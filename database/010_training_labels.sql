-- 010_training_labels.sql
-- Tabla de etiquetas de especialista para reentrenamiento del modelo ML.
-- Registra la opinión clínica sobre cada diagnóstico automático.
-- Solo contiene feature_vector_28 (28 números, sin PII) + etiquetas confirmadas.
-- Exportar para training: SELECT feature_vector_28, confirmed_subtype, confirmed_severity, confirmed_risk_level FROM diagnosis.training_labels;

CREATE TABLE IF NOT EXISTS diagnosis.training_labels (
    id                   UUID         NOT NULL DEFAULT gen_random_uuid() PRIMARY KEY,
    diagnosis_id         UUID         NOT NULL REFERENCES diagnosis.diagnoses(id) ON DELETE CASCADE,
    feature_vector_28    NUMERIC[]    NOT NULL,
    confirmed_subtype    diagnosis.dyslexia_subtype NOT NULL,
    confirmed_severity   diagnosis.severity_level   NOT NULL,
    confirmed_risk_level TEXT         NOT NULL CHECK (confirmed_risk_level IN ('LOW', 'MEDIUM', 'HIGH')),
    specialist_id        UUID         NOT NULL REFERENCES auth.users(id),
    notes                TEXT,
    labeled_at           TIMESTAMPTZ  NOT NULL DEFAULT now(),

    -- Un solo label por diagnóstico; el especialista puede corregir el suyo (ON CONFLICT DO UPDATE)
    CONSTRAINT training_labels_diagnosis_unique UNIQUE (diagnosis_id)
);

CREATE INDEX IF NOT EXISTS idx_training_labels_labeled_at  ON diagnosis.training_labels (labeled_at DESC);
CREATE INDEX IF NOT EXISTS idx_training_labels_subtype     ON diagnosis.training_labels (confirmed_subtype);
CREATE INDEX IF NOT EXISTS idx_training_labels_specialist  ON diagnosis.training_labels (specialist_id);

COMMENT ON TABLE diagnosis.training_labels IS
    'Etiquetas clínicas de especialista para reentrenamiento ML. '
    'Referencia anónima: feature_vector_28 es vector numérico sin nombre ni ID del alumno. '
    'UNIQUE (diagnosis_id): un especialista puede sobreescribir su propio label. '
    'Target mínimo para reentrenamiento real: >= 50 labels por clase (HU-BD-10).';
