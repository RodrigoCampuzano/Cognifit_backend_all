-- =============================================================
-- 005 — Corrige diagnosis.v_latest_student_risk
--
-- PROBLEMA: la vista se creó en 001 exponiendo solo las columnas que
-- existían entonces. La migración 002 agregó a diagnosis.diagnoses las
-- columnas del PLN (pln_subtype, pln_severity, pln_source, model_version)
-- pero NUNCA actualizó la vista. Como PgResultRepository.get_latest_risk
-- hace `SELECT r.* FROM diagnosis.v_latest_student_risk`, esos campos
-- nunca llegaban al cliente: la app Flutter caía a sus defaults y mostraba
-- SIEMPRE "Subtipo: sin_riesgo / Severidad: ninguna" aunque el diagnóstico
-- almacenado fuera fonológico severo con riesgo HIGH.
--
-- Además la vista exponía `diagnosis_id` mientras el modelo del cliente lee
-- `id`, y no exponía `assignment_id` ni la ruta de intervención recomendada.
--
-- Esta migración reconstruye la vista con el contrato completo que consume
-- la app. Idempotente (CREATE OR REPLACE).
-- Requiere: 001, 002 aplicadas.
-- =============================================================

-- DROP explícito: CREATE OR REPLACE VIEW no permite cambiar el nombre ni el
-- orden de las columnas existentes (aquí renombramos diagnosis_id -> id y
-- agregamos columnas nuevas), así que hay que recrearla desde cero.
DROP VIEW IF EXISTS diagnosis.v_latest_student_risk;

CREATE VIEW diagnosis.v_latest_student_risk AS
SELECT DISTINCT ON (d.student_id)
    d.student_id,
    d.id                        AS id,            -- el cliente lee 'id', no 'diagnosis_id'
    d.id                        AS diagnosis_id,  -- se conserva por compatibilidad
    d.assignment_id,
    -- Enum clínico (PHONOLOGICAL/VISUAL_SURFACE/MIXED/NO_DYSLEXIA)
    d.subtype,
    d.severity,
    -- Valores RAW del PLN — son los que muestra la UI y los que consume
    -- el Recommendation Service sin pérdida de información.
    d.pln_subtype,
    d.pln_severity,
    d.pln_source,
    d.model_version,
    d.risk_probability,
    COALESCE(
        d.risk_level,
        CASE
            WHEN d.risk_probability >= 0.66 THEN 'HIGH'
            WHEN d.risk_probability >= 0.31 THEN 'MEDIUM'
            ELSE 'LOW'
        END
    ) AS risk_level,
    d.main_error_codes,
    d.recommendation_reason,
    -- Ruta de intervención activa del alumno (la genera el Recommendation
    -- Service en el mismo request del diagnóstico). LEFT JOIN: si el
    -- servicio de recomendación falló, el diagnóstico sigue siendo válido
    -- y la ruta simplemente viene vacía.
    COALESCE(sp.exercise_route, '[]'::JSONB) AS recommended_route,
    d.diagnosed_at
FROM diagnosis.diagnoses d
LEFT JOIN LATERAL (
    SELECT p.exercise_route
    FROM intervention.student_paths p
    WHERE p.student_id = d.student_id AND p.is_active
    ORDER BY p.assigned_at DESC
    LIMIT 1
) sp ON TRUE
ORDER BY d.student_id, d.diagnosed_at DESC;

COMMENT ON VIEW diagnosis.v_latest_student_risk IS
    'Último diagnóstico por alumno con el contrato completo que consume la app '
    '(incluye pln_subtype/pln_severity/pln_source y la ruta de intervención activa). '
    'Corregida en 005: antes omitía las columnas agregadas en 002.';
