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
