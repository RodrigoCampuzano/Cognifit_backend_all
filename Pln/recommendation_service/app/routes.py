"""
Motor de recomendación adaptativa de CogniFit Escolar.
Mapea (subtipo, severidad) → ruta de aprendizaje ordenada.
Todos los exercise_ids existen en banco_ejercicios_intervencion.json.
"""

# ─── Rutas de aprendizaje por perfil ─────────────────────────────────────────
# Cada clave es (subtipo, severidad) → lista ordenada de exercise_ids.
# El orden importa: de menor a mayor dificultad dentro del perfil.

LEARNING_ROUTES: dict[tuple, list[str]] = {

    # ── FONOLÓGICO ────────────────────────────────────────────────────────────
    ("fonologico", "leve"): [
        "CF_silabas_N1",
        "CF_fonema_inicial_N1",
        "CF_rima_N1",
        "PS_cv_N1",
        "DIC_palabras_simples_N1",
    ],
    ("fonologico", "moderado"): [
        "CF_silabas_N1",
        "CF_fonema_inicial_N1",
        "CF_supresion_N1",
        "PS_cv_N1",
        "PS_cvc_N2",
        "DIC_frases_cortas_N1",
    ],
    ("fonologico", "severo"): [
        "CF_silabas_N1",
        "CF_fonema_inicial_N1",
        "CF_supresion_N1",
        "CF_sustitucion_N1",
        "PS_cv_N1",
        "PS_cv_N1_refuerzo",
        "DIC_palabras_simples_N1",
        "TTS_lectura_guiada_N1",
    ],

    # ── VISUAL ────────────────────────────────────────────────────────────────
    ("visual", "leve"): [
        "VIS_discriminacion_bd_N1",
        "VIS_discriminacion_pq_N1",
        "VIS_memoria_palabras_N1",
        "DEN_rapid_letras_N1",
        "LEC_guiada_N1",
    ],
    ("visual", "moderado"): [
        "VIS_discriminacion_bd_N1",
        "VIS_discriminacion_pq_N1",
        "VIS_memoria_palabras_N1",
        "VIS_parejas_palabras_N1",
        "DEN_rapid_letras_N1",
        "DEN_rapid_objetos_N1",
        "PS_cv_N1",
    ],
    ("visual", "severo"): [
        "VIS_discriminacion_bd_N1",
        "VIS_discriminacion_pq_N1",
        "VIS_memoria_palabras_N1",
        "VIS_parejas_palabras_N1",
        "VIS_trazado_letras_N1",
        "DEN_rapid_letras_N1",
        "DEN_rapid_objetos_N1",
        "PS_cv_N1",
        "TTS_lectura_guiada_N1",
    ],

    # ── MIXTO ─────────────────────────────────────────────────────────────────
    ("mixto", "leve"): [
        "CF_silabas_N1",
        "VIS_discriminacion_bd_N1",
        "PS_cv_N1",
        "DIC_palabras_simples_N1",
    ],
    ("mixto", "moderado"): [
        "MULTI_silabas_cromaticas_N1",
        "MULTI_lectura_auditiva_N1",
        "CF_silabas_N1",
        "VIS_discriminacion_bd_N1",
        "PS_cv_N1",
        "DIC_palabras_simples_N1",
    ],
    ("mixto", "severo"): [
        "MULTI_silabas_cromaticas_N1",
        "MULTI_lectura_auditiva_N1",
        "MULTI_lectura_auditiva_N1_refuerzo",
        "CF_silabas_N1",
        "CF_fonema_inicial_N1",
        "VIS_discriminacion_bd_N1",
        "VIS_discriminacion_pq_N1",
        "PS_cv_N1",
        "DIC_palabras_simples_N1",
        "COMP_textos_cortos_N1",
    ],

    # ── FLUIDEZ ───────────────────────────────────────────────────────────────
    ("fluidez", "leve"): [
        "DEN_rapid_colores_N1",
        "DEN_rapid_letras_N1",
        "LEC_repetida_N1",
        "LEC_temporizador_N1",
    ],
    ("fluidez", "moderado"): [
        "DEN_rapid_colores_N1",
        "DEN_rapid_letras_N1",
        "DEN_rapid_objetos_N1",
        "LEC_repetida_N1",
        "LEC_repetida_N2",
        "LEC_temporizador_N1",
        "LEC_temporizador_N2",
    ],
    ("fluidez", "severo"): [
        "DEN_rapid_colores_N1",
        "DEN_rapid_letras_N1",
        "DEN_rapid_objetos_N1",
        "LEC_repetida_N1",
        "LEC_repetida_N1_refuerzo",
        "LEC_repetida_N2",
        "LEC_temporizador_N1",
        "LEC_temporizador_N2",
        "TTS_lectura_guiada_N1",
        "MULTI_lectura_auditiva_N1",
    ],

    # ── SIN RIESGO ────────────────────────────────────────────────────────────
    ("sin_riesgo", "ninguna"): [],
    ("sin_riesgo", "leve"):    [],   # fallback por si ML devuelve severidad
}

# Validación en carga: todos los perfiles tienen ruta
_SUBTYPES   = ["fonologico", "visual", "mixto", "fluidez"]
_SEVERITIES = ["leve", "moderado", "severo"]
for _s in _SUBTYPES:
    for _sev in _SEVERITIES:
        assert (_s, _sev) in LEARNING_ROUTES, f"Ruta faltante: ({_s!r}, {_sev!r})"


def get_route(subtype: str, severity: str) -> list[str]:
    """
    Devuelve la ruta de ejercicios para un perfil.
    Nunca falla silenciosamente: si el par no existe usa fallback leve.
    """
    key = (subtype, severity)
    if key in LEARNING_ROUTES:
        return list(LEARNING_ROUTES[key])

    # Fallback explícito
    fallback = (subtype, "leve")
    if fallback in LEARNING_ROUTES:
        return list(LEARNING_ROUTES[fallback])

    return []  # sin_riesgo u otro caso sin intervención


# Cuántos ejercicios lleva una ruta según la severidad. Sale de los largos que
# ya tenían las rutas curadas (leve 4-5, moderado 6-7, severo 8-10): la
# severidad marca cuánto trabajo recibe el alumno, y eso no cambia por su grado.
ROUTE_BUDGET = {"leve": 5, "moderado": 7, "severo": 10}


def build_route(subtype: str, severity: str, grade, exercise_bank: dict) -> tuple[list[str], bool]:
    """Arma la ruta del alumno considerando su grado.

    Devuelve (ruta, el_banco_cubre_ese_grado).

    `LEARNING_ROUTES` es una lista curada por (subtipo, severidad) y el orden
    clínico de esa curaduría se respeta. Lo que agrega esta función es el eje
    que faltaba: **el grado**.

    Tres pasos:

    1. De la ruta curada se adelantan los ejercicios etiquetados para el grado.
    2. Se completan con ejercicios del banco que sirven al mismo perfil y al
       mismo grado pero que ninguna ruta menciona. Esto es lo que permite que
       un ejercicio nuevo llegue a un alumno sin editar a mano las doce listas
       —el modo de falla que dejó a `M10_VD` inalcanzable durante meses— y es
       la condición para poder fusionar el material de 4º-6º.
    3. Si aun así no se llega al presupuesto de la severidad, se rellena con el
       resto de la ruta curada, aunque sea de otro grado.

    **Nunca devuelve vacío por filtrar.** Con el banco actual, un alumno de 6º
    no tiene un solo ejercicio de su grado en ningún perfil; dejarlo sin
    intervención sería peor que darle material de un grado menor. En ese caso
    se entrega la ruta curada completa y el flag queda en False para que la UI
    lo diga en vez de fingir que el material corresponde.
    """
    curada = get_route(subtype, severity)
    if not curada or grade is None:
        return curada, True

    g = str(grade)

    def grados_de(eid: str) -> list:
        return exercise_bank.get(eid, {}).get("grados") or []

    del_grado = [eid for eid in curada if g in grados_de(eid)]

    # Si la curaduría ya cubre el grado, se respeta tal cual y solo se adelantan
    # los ejercicios que le corresponden. Esa lista codifica un orden clínico:
    # reemplazarla porque en el banco hay otros ejercicios etiquetados para el
    # mismo grado sería tirar ese criterio. Con el banco actual esta rama deja
    # 1º-3º exactamente como estaba.
    if del_grado:
        return del_grado + [eid for eid in curada if eid not in del_grado], True

    # Acá está el caso roto: ningún ejercicio de la ruta curada corresponde al
    # grado del alumno. Es lo que hoy le pasa a todo 4º-6º. Recién entonces se
    # arma desde el banco.
    #
    # Ejercicios del banco que sirven a este perfil y grado y que la curaduría
    # no menciona. Se ordenan por nivel para conservar la progresión de
    # dificultad, y por id para que la ruta sea estable entre llamadas. Es
    # también lo que permite que material nuevo llegue a alguien sin editar a
    # mano las doce listas — el modo de falla que dejó a `M10_VD` inalcanzable.
    #
    # El banco que llega acá tiene los dos catálogos fusionados (se unen para
    # que /exercises/{id} resuelva cualquier id), así que se excluye
    # explícitamente la vía universal: la comprensión se entrega por grado y no
    # la predice ningún subtipo. Hoy además no calzaría —su perfil_objetivo es
    # "universal"— pero apoyarse en eso sería una garantía por accidente.
    extra = sorted(
        (
            eid
            for eid, ex in exercise_bank.items()
            if eid not in curada
            and ex.get("via") != "universal_grado"
            and subtype in (ex.get("perfil_objetivo") or [])
            and g in (ex.get("grados") or [])
        ),
        key=lambda eid: (exercise_bank[eid].get("nivel", 1), eid),
    )

    # Ni la ruta curada ni el banco tienen algo de ese grado. Filtrar dejaría al
    # alumno sin intervención, que es peor que darle material de un grado menor:
    # se entrega la ruta completa y el flag avisa, en vez de fingir que el
    # material corresponde.
    if not extra:
        return curada, False

    presupuesto = ROUTE_BUDGET.get(severity, 7)
    ruta = extra[:presupuesto]

    if len(ruta) < presupuesto:
        ruta += [eid for eid in curada if eid not in ruta][: presupuesto - len(ruta)]

    return ruta, True


def get_next_exercise(
    current_route: list[str],
    session_history: list[dict],
) -> dict:
    """
    Decide el próximo ejercicio según el desempeño reciente.

    Reglas (umbrales de Rasinski 2004 adaptados):
    - accuracy > 90% en las últimas 3 sesiones del ejercicio → sube nivel
    - accuracy < 40% en las últimas 3 sesiones → añade soporte TTS
    - entre 40-90% → continúa en el mismo ejercicio

    session_history: lista de dicts con {exercise_id, accuracy}
    """
    if not current_route:
        return {"exercise_id": None, "action": "route_empty"}

    if not session_history:
        return {"exercise_id": current_route[0], "action": "start"}

    current_exercise = session_history[-1]["exercise_id"]

    # Buscar el ejercicio actual en la ruta
    if current_exercise not in current_route:
        return {"exercise_id": current_route[0], "action": "restart"}

    # Últimas 3 sesiones del ejercicio actual
    recent = [
        s for s in session_history[-10:]
        if s["exercise_id"] == current_exercise
    ][-3:]

    if len(recent) < 2:
        return {"exercise_id": current_exercise, "action": "continue"}

    recent_accuracy = sum(s["accuracy"] for s in recent) / len(recent)
    current_idx = current_route.index(current_exercise)

    if recent_accuracy > 0.90:
        # Subir al siguiente ejercicio de la ruta
        if current_idx < len(current_route) - 1:
            return {
                "exercise_id": current_route[current_idx + 1],
                "action": "level_up",
                "trigger": f"accuracy {recent_accuracy:.0%} en {len(recent)} sesiones",
            }
        return {"exercise_id": current_exercise, "action": "route_completed"}

    if recent_accuracy < 0.40:
        return {
            "exercise_id": current_exercise,
            "action": "add_support",
            "support": "tts_enabled",
            "trigger": f"accuracy {recent_accuracy:.0%} — activando TTS de apoyo",
        }

    return {"exercise_id": current_exercise, "action": "continue"}
