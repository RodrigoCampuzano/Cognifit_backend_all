"""
Detección y clasificación de errores de dislexia (PLN).
Compara target vs response y tipifica cada divergencia con un código de error.
"""
from Levenshtein import editops

# Pares de rotación visual (letras espejo)
ROTATION_PAIRS = {
    frozenset({"b", "d"}),
    frozenset({"p", "q"}),
    frozenset({"m", "w"}),
    frozenset({"n", "u"}),
}

# Homófonos del español mexicano -> no son errores diagnósticos de dislexia
SPANISH_PHONETIC_RULES = {
    frozenset({"b", "v"}): "SUS_HOMOFONICO",   # baca/vaca -> ortografía
    frozenset({"ll", "y"}): "SUS_HOMOFONICO",  # llama/yama -> yeísmo MX
    frozenset({"c", "s"}): "SUS_HOMOFONICO",   # cena/sena -> seseo MX
    frozenset({"c", "z"}): "SUS_HOMOFONICO",
    frozenset({"g", "j"}): "FON",              # gitarra -> error fonológico real
    frozenset({"h", ""}): "OMI_HOMOFONICO",    # omitir h muda -> normal MX
}


def classify_char_error(expected: str, produced: str) -> str:
    """Clasifica un error de carácter: ROT (rotación visual) o SUS (sustitución)."""
    return "ROT" if frozenset({expected, produced}) in ROTATION_PAIRS else "SUS"


def is_silent_h_omission(target: str, position: int) -> bool:
    """¿La omisión en `position` es una 'h' muda (ortografía, no dislexia)?

    La 'h' española no se pronuncia, así que omitirla ("hola" -> "ola") es un
    error ortográfico normal en escolares mexicanos, NO un marcador fonológico
    de dislexia. La única excepción es la 'h' del dígrafo 'ch': ahí sí cambia
    la pronunciación ("chico" -> "cico"), y por eso se mantiene diagnóstica.
    """
    if target[position].lower() != "h":
        return False
    return not (position > 0 and target[position - 1].lower() == "c")


def refine_error_with_phonetics(error: dict) -> dict:
    """
    Refina un error SUS/FON usando reglas fonéticas del español MX.
    Si el par es un homófono, lo marca como no diagnóstico para no inflar el score.
    """
    if error["type"] not in ("SUS", "FON"):
        return {**error, "is_diagnostic": True}

    pair = frozenset({error.get("expected_char", ""), error.get("produced_char", "")})
    refined = SPANISH_PHONETIC_RULES.get(pair)
    if refined:
        return {**error, "type": refined, "is_diagnostic": False}
    return {**error, "is_diagnostic": True}


def detect_errors(target: str, response: str) -> list:
    """
    Compara target vs response a nivel de carácter usando editops de Levenshtein.
    Devuelve una lista de errores clasificados con código y contexto.
    """
    if not response:
        return [{
            "type": "OMI", "expected_char": target, "position": 0,
            "context": target, "detail": "respuesta_vacía", "is_diagnostic": True,
        }]

    errors = []
    for op, i, j in editops(target, response):
        if op == "delete":
            # La regla OMI_HOMOFONICO de SPANISH_PHONETIC_RULES nunca se
            # aplicaba: refine_error_with_phonetics solo corre en el branch
            # "replace", y omitir una letra es un "delete". Resultado: la 'h'
            # muda inflaba OMI_rate (una feature que el modelo sí usa) y subía
            # el riesgo de niños con ortografía perfectamente normal.
            silent_h = is_silent_h_omission(target, i)
            errors.append({
                "type": "OMI_HOMOFONICO" if silent_h else "OMI",
                "expected_char": target[i],
                "position": i, "context": target[max(0, i - 2):i + 3],
                "is_diagnostic": not silent_h,
            })
        elif op == "insert":
            errors.append({
                "type": "ADD", "produced_char": response[j],
                "position": j, "context": response[max(0, j - 2):j + 3],
                "is_diagnostic": True,
            })
        elif op == "replace":
            err = {
                "type": classify_char_error(target[i], response[j]),
                "expected_char": target[i], "produced_char": response[j],
                "position": i, "context": target[max(0, i - 2):i + 3],
            }
            errors.append(refine_error_with_phonetics(err))
    return errors


def detect_word_level_errors(target_words: list, response_words: list) -> list:
    """Detecta inversiones de sílabas, segmentación y unión a nivel de palabra."""
    errors = []
    target_joined = "".join(target_words)
    response_joined = "".join(response_words)

    if len(target_words) != len(response_words) and target_joined == response_joined:
        if len(response_words) < len(target_words):
            errors.append({"type": "UNI", "detail": "palabras unidas", "is_diagnostic": True})
        else:
            errors.append({"type": "SEG", "detail": "palabra segmentada", "is_diagnostic": True})

    for tw, rw in zip(target_words, response_words):
        if tw != rw and sorted(tw) == sorted(rw) and len(tw) == len(rw):
            errors.append({
                "type": "INV", "expected": tw, "produced": rw,
                "detail": "inversión de letras o sílabas", "is_diagnostic": True,
            })
    return errors


def is_lexicalization(target_pseudo: str, response: str, lexicon: set) -> bool:
    """Detecta si una pseudopalabra fue convertida en palabra real (perfil visual)."""
    return response in lexicon and target_pseudo not in lexicon
