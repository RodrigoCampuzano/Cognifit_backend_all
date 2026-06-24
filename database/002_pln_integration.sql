-- =============================================================
-- 002 — Integración con microservicios PLN (Diagnosis 8001 / Recommendation 8002)
-- Idempotente. Mantiene el enum clínico intacto (PHONOLOGICAL/VISUAL_SURFACE/MIXED/
-- NO_DYSLEXIA) y guarda además el valor RAW del PLN
-- (fonologico/visual/mixto/fluidez/sin_riesgo, leve/moderado/severo/ninguna)
-- para reenviarlo al Recommendation Service sin pérdida de información.
-- Requiere 001_cognifit_schema_v2_full.sql aplicado.
-- =============================================================

-- Diagnóstico: valor RAW del PLN + versión real del modelo + breakdown de errores.
ALTER TABLE diagnosis.diagnoses
    ADD COLUMN IF NOT EXISTS pln_subtype     TEXT,           -- 'fonologico'|'visual'|'mixto'|'fluidez'|'sin_riesgo'
    ADD COLUMN IF NOT EXISTS pln_severity    TEXT,           -- 'leve'|'moderado'|'severo'|'ninguna'
    ADD COLUMN IF NOT EXISTS model_version   TEXT,           -- versión real del .pkl (p.ej. '20260618_0309')
    ADD COLUMN IF NOT EXISTS error_breakdown JSONB NOT NULL DEFAULT '{}'::JSONB,
    ADD COLUMN IF NOT EXISTS pln_source      TEXT NOT NULL DEFAULT 'service';  -- 'service' | 'local_fallback'

-- student_paths: ya trae route_template_id/route_reason (001). Añadimos lo que
-- necesita persistir la ruta devuelta por el Recommendation Service.
ALTER TABLE intervention.student_paths
    ADD COLUMN IF NOT EXISTS exercise_route  JSONB NOT NULL DEFAULT '[]'::JSONB,  -- exercise_ids ordenados (8002)
    ADD COLUMN IF NOT EXISTS total_exercises SMALLINT NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS pln_profile     TEXT;                                -- subtype RAW que generó la ruta

CREATE INDEX IF NOT EXISTS idx_student_paths_student_active
    ON intervention.student_paths(student_id) WHERE is_active;

CREATE INDEX IF NOT EXISTS idx_ml_model_versions_production
    ON diagnosis.ml_model_versions(is_production) WHERE is_production;

COMMENT ON COLUMN diagnosis.diagnoses.pln_subtype IS
    'Subtipo RAW del Diagnosis Service. Se reenvía a /recommend sin mapear al enum clínico.';
COMMENT ON COLUMN diagnosis.diagnoses.pln_source IS
    'service = modelos entrenados (8001); local_fallback = pipeline rule-based del API.';
