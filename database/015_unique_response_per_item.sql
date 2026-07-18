-- =============================================================
-- 015 — Una sola respuesta por (sesión, ítem)
--
-- PROBLEMA: assessment.student_responses no tenía ninguna restricción de
-- unicidad y save_response siempre hacía INSERT. El cliente móvil reencola
-- las respuestas cuando no hay conexión y las reintenta hasta observar un
-- éxito explícito (semántica at-least-once), así que una respuesta que se
-- confirmó en el servidor pero cuya confirmación no llegó al dispositivo se
-- reenviaba y quedaba duplicada.
--
-- Eso no es solo ruido: el diagnóstico cuenta errores por tipo sobre estas
-- filas (OMI_rate, SUS_rate, accuracy...), así que cada duplicado infla
-- artificialmente el conteo de errores del alumno y puede empujar su riesgo
-- hacia arriba.
--
-- Idempotente. Deduplica lo existente antes de crear el índice para que la
-- migración no falle en bases que ya acumularon duplicados.
-- =============================================================

-- 1. Deduplicar: conservar la fila más reciente de cada (session_id, item_id).
--    Se usa ctid como desempate porque la tabla no tiene un timestamp propio
--    fiable para esto en todas las versiones del esquema.
DELETE FROM assessment.student_responses a
USING assessment.student_responses b
WHERE a.session_id IS NOT NULL
  AND a.session_id = b.session_id
  AND a.item_id    = b.item_id
  AND a.ctid       < b.ctid;

-- 2. Índice único parcial: session_id es NULLable (se agregó por ALTER en 001),
--    y las filas históricas sin sesión no deben bloquear la restricción.
CREATE UNIQUE INDEX IF NOT EXISTS uq_student_responses_session_item
    ON assessment.student_responses (session_id, item_id)
    WHERE session_id IS NOT NULL;

COMMENT ON INDEX assessment.uq_student_responses_session_item IS
    'Garantiza una respuesta por ítem y sesión. Habilita el ON CONFLICT DO UPDATE '
    'de save_response: un reenvío del cliente offline actualiza la fila en vez de '
    'duplicarla y sesgar el conteo de errores del diagnóstico.';
