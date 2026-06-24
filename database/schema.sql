-- =============================================================
-- CogniFit Escolar — Schema PostgreSQL
-- Versión: 1.0
-- Separado por dominios con schemas individuales
-- =============================================================

-- ─────────────────────────────────────────────────────────────
-- EXTENSIONES
-- ─────────────────────────────────────────────────────────────
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";       -- UUIDs
CREATE EXTENSION IF NOT EXISTS "pgcrypto";        -- cifrado de campos sensibles
CREATE EXTENSION IF NOT EXISTS "pg_trgm";         -- búsqueda difusa en nombres

-- ─────────────────────────────────────────────────────────────
-- SCHEMAS
-- ─────────────────────────────────────────────────────────────
CREATE SCHEMA IF NOT EXISTS auth;
CREATE SCHEMA IF NOT EXISTS academic;
CREATE SCHEMA IF NOT EXISTS assessment;
CREATE SCHEMA IF NOT EXISTS diagnosis;
CREATE SCHEMA IF NOT EXISTS intervention;
CREATE SCHEMA IF NOT EXISTS tracking;
CREATE SCHEMA IF NOT EXISTS reporting;
CREATE SCHEMA IF NOT EXISTS audit;


-- =============================================================
-- SCHEMA: auth
-- Usuarios del sistema, roles, sesiones JWT
-- =============================================================

CREATE TYPE auth.user_role AS ENUM (
    'ADMIN',
    'TEACHER',
    'STUDENT'
);

CREATE TABLE auth.users (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email           TEXT UNIQUE NOT NULL,
    -- Argon2 hash almacenado como texto (el hash ya incluye sal)
    password_hash   TEXT NOT NULL,
    role            auth.user_role NOT NULL,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
COMMENT ON TABLE auth.users IS 'Tabla base de todos los usuarios del sistema. El rol determina qué datos son accesibles via RLS.';

-- Tokens de refresco (JWT refresh tokens)
CREATE TABLE auth.refresh_tokens (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    token_hash      TEXT NOT NULL UNIQUE,          -- hash del refresh token, nunca en claro
    device_info     TEXT,                          -- "Android 14 / Pixel 8"
    ip_address      INET,
    expires_at      TIMESTAMPTZ NOT NULL,
    revoked_at      TIMESTAMPTZ,                   -- NULL = vigente
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
COMMENT ON TABLE auth.refresh_tokens IS 'Refresh tokens para renovar JWT. Se invalidan en logout o remote wipe.';

-- Registro de consentimiento del tutor (LGPDPPSO / buenas prácticas)
CREATE TABLE auth.guardian_consents (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    student_id      UUID NOT NULL,                 -- FK a academic.students, se agrega después
    guardian_name   TEXT NOT NULL,
    guardian_email  TEXT,
    accepted_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    ip_address      INET,
    consent_version TEXT NOT NULL DEFAULT '1.0'    -- versión del documento de privacidad
);
COMMENT ON TABLE auth.guardian_consents IS 'Registro de consentimiento del tutor al crear cuenta de alumno.';


-- =============================================================
-- SCHEMA: academic
-- Escuelas, grupos, alumnos
-- =============================================================

CREATE TABLE academic.schools (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name            TEXT NOT NULL,
    cct             TEXT UNIQUE,                   -- Clave Centro de Trabajo SEP
    state           TEXT NOT NULL DEFAULT 'Chiapas',
    municipality    TEXT,
    license_tier    TEXT NOT NULL DEFAULT 'freemium', -- 'freemium' | 'premium' | 'institutional'
    license_expires_at TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
COMMENT ON TABLE academic.schools IS 'Escuelas registradas. La licencia controla el tier de acceso.';

CREATE TABLE academic.groups (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    school_id       UUID NOT NULL REFERENCES academic.schools(id) ON DELETE CASCADE,
    teacher_id      UUID NOT NULL REFERENCES auth.users(id),
    grade           SMALLINT NOT NULL CHECK (grade BETWEEN 1 AND 6),  -- 1° a 6° primaria
    group_label     TEXT NOT NULL,                 -- "A", "B", "9-D"
    school_year     TEXT NOT NULL,                 -- "2025-2026"
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (school_id, grade, group_label, school_year)
);

CREATE TABLE academic.students (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         UUID REFERENCES auth.users(id) ON DELETE SET NULL,  -- NULL si no tiene login propio
    group_id        UUID NOT NULL REFERENCES academic.groups(id),
    -- Datos PII cifrados con pgcrypto (AES-256)
    full_name       BYTEA NOT NULL,                -- pgp_sym_encrypt(nombre, key)
    birth_year      SMALLINT,
    gender          TEXT,                          -- 'M' | 'F' | 'NB' | NULL
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    enrolled_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
COMMENT ON TABLE academic.students IS 'PII (nombre) cifrado en reposo con pgcrypto. Solo descifrable con la clave de aplicación.';

-- FK diferida para evitar dependencia circular auth ↔ academic
ALTER TABLE auth.guardian_consents
    ADD CONSTRAINT fk_guardian_student
    FOREIGN KEY (student_id) REFERENCES academic.students(id) ON DELETE CASCADE;


-- =============================================================
-- SCHEMA: assessment
-- Tests diagnósticos, ítems, respuestas capturadas
-- =============================================================

CREATE TYPE assessment.test_type AS ENUM (
    'LEXICO_VISUAL',     -- reconocimiento de palabras escritas
    'PSEUDOWORDS',       -- lectura de pseudopalabras
    'DICTATION_STT'      -- dictado con Speech-to-Text
);

CREATE TABLE assessment.tests (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name            TEXT NOT NULL,
    test_type       assessment.test_type NOT NULL,
    target_grades   SMALLINT[] NOT NULL,           -- ej: {1,2,3}
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE assessment.test_items (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    test_id         UUID NOT NULL REFERENCES assessment.tests(id) ON DELETE CASCADE,
    item_order      SMALLINT NOT NULL,
    stimulus_text   TEXT NOT NULL,                 -- palabra / pseudopalabra / oración
    stimulus_audio_url TEXT,                       -- URL en storage para ítems de dictado
    expected_response TEXT NOT NULL,
    difficulty      SMALLINT NOT NULL DEFAULT 1 CHECK (difficulty BETWEEN 1 AND 5),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Asignación de un test a un alumno específico
CREATE TABLE assessment.test_assignments (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    student_id      UUID NOT NULL REFERENCES academic.students(id),
    test_id         UUID NOT NULL REFERENCES assessment.tests(id),
    assigned_by     UUID NOT NULL REFERENCES auth.users(id),   -- docente
    assigned_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    due_at          TIMESTAMPTZ,
    status          TEXT NOT NULL DEFAULT 'PENDING'            -- 'PENDING'|'IN_PROGRESS'|'COMPLETED'
);

-- Respuesta del alumno a cada ítem del test
CREATE TABLE assessment.student_responses (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    assignment_id       UUID NOT NULL REFERENCES assessment.test_assignments(id) ON DELETE CASCADE,
    item_id             UUID NOT NULL REFERENCES assessment.test_items(id),
    raw_response        TEXT NOT NULL,             -- texto capturado (STT transcripción o escritura)
    response_time_ms    INT,                       -- latencia de respuesta
    is_correct          BOOLEAN,                   -- NULL = pendiente de análisis PLN
    -- Resultado del pipeline PLN propio (Development):
    error_tags          TEXT[],                    -- ['INVERSION','OMISSION','SUBSTITUTION']
    phonetic_distance   FLOAT,                     -- distancia Levenshtein fonética
    responded_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
COMMENT ON TABLE assessment.student_responses IS 'Captura bruta de cada respuesta. El pipeline PLN/ML propio llena error_tags y phonetic_distance.';


-- =============================================================
-- SCHEMA: diagnosis
-- Diagnósticos emitidos por el modelo ML, versiones del modelo
-- =============================================================

CREATE TYPE diagnosis.dyslexia_subtype AS ENUM (
    'PHONOLOGICAL',      -- fonológica
    'VISUAL_SURFACE',    -- superficial/visual
    'MIXED',
    'NO_DYSLEXIA'
);

CREATE TYPE diagnosis.severity_level AS ENUM (
    'MILD',
    'MODERATE',
    'SEVERE'
);

CREATE TABLE diagnosis.ml_model_versions (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    version_tag     TEXT NOT NULL UNIQUE,          -- "v1.2.3"
    algorithm       TEXT NOT NULL,                 -- "RandomForest" | "SVM"
    accuracy        FLOAT,
    f1_score        FLOAT,
    precision_score FLOAT,
    recall_score    FLOAT,
    train_date      DATE NOT NULL,
    is_production   BOOLEAN NOT NULL DEFAULT FALSE,
    notes           TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
COMMENT ON TABLE diagnosis.ml_model_versions IS 'Solo se puede marcar is_production=TRUE si las métricas superan el umbral validado. Regla de negocio en la app.';

CREATE TABLE diagnosis.diagnoses (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    student_id          UUID NOT NULL REFERENCES academic.students(id),
    assignment_id       UUID NOT NULL REFERENCES assessment.test_assignments(id),
    model_version_id    UUID NOT NULL REFERENCES diagnosis.ml_model_versions(id),
    subtype             diagnosis.dyslexia_subtype NOT NULL,
    severity            diagnosis.severity_level,              -- NULL si NO_DYSLEXIA
    risk_probability    FLOAT NOT NULL CHECK (risk_probability BETWEEN 0 AND 1),
    -- Detalle del pipeline PLN propio almacenado como JSONB
    feature_vector      JSONB,                     -- {"tfidf_top10": [...], "ngrams": [...]}
    class_probabilities JSONB,                     -- {"PHONOLOGICAL": 0.72, "MIXED": 0.20, ...}
    diagnosed_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    reviewed_by         UUID REFERENCES auth.users(id)         -- si un especialista lo validó
);
COMMENT ON TABLE diagnosis.diagnoses IS 'feature_vector y class_probabilities como JSONB: flexibilidad para cambiar el modelo sin alterar el schema.';


-- =============================================================
-- SCHEMA: intervention
-- Rutas de aprendizaje, ejercicios, sesiones de ejercicio
-- =============================================================

CREATE TABLE intervention.learning_paths (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name            TEXT NOT NULL,
    target_subtype  diagnosis.dyslexia_subtype NOT NULL,
    target_severity diagnosis.severity_level NOT NULL,
    description     TEXT,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
COMMENT ON TABLE intervention.learning_paths IS 'Motor de recomendación: diagnóstico → ruta de aprendizaje.';

CREATE TABLE intervention.exercises (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    learning_path_id UUID NOT NULL REFERENCES intervention.learning_paths(id),
    title           TEXT NOT NULL,
    exercise_type   TEXT NOT NULL,                 -- 'PHONOLOGICAL_AWARENESS'|'SYLLABIC_SEGMENTATION'|'VISUAL_TRACKING'|...
    difficulty      SMALLINT NOT NULL DEFAULT 1 CHECK (difficulty BETWEEN 1 AND 5),
    content         JSONB NOT NULL,                -- estructura variable según tipo de ejercicio
    has_tts         BOOLEAN NOT NULL DEFAULT FALSE,
    has_stt         BOOLEAN NOT NULL DEFAULT FALSE,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Asignación de ruta a un alumno tras diagnóstico
CREATE TABLE intervention.student_paths (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    student_id          UUID NOT NULL REFERENCES academic.students(id),
    learning_path_id    UUID NOT NULL REFERENCES intervention.learning_paths(id),
    diagnosis_id        UUID NOT NULL REFERENCES diagnosis.diagnoses(id),
    current_difficulty  SMALLINT NOT NULL DEFAULT 1,
    assigned_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    is_active           BOOLEAN NOT NULL DEFAULT TRUE
);

-- Sesión de un alumno realizando un ejercicio
CREATE TABLE intervention.exercise_sessions (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    student_path_id     UUID NOT NULL REFERENCES intervention.student_paths(id),
    exercise_id         UUID NOT NULL REFERENCES intervention.exercises(id),
    started_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at        TIMESTAMPTZ,
    score               FLOAT,                     -- 0.0 – 1.0
    accuracy_pct        FLOAT,
    avg_response_ms     INT,
    -- Estado local para offline-first (Flutter lo sincroniza al reconnectarse)
    local_state         JSONB,                     -- progreso parcial si se cortó la conexión
    is_synced           BOOLEAN NOT NULL DEFAULT TRUE
);
COMMENT ON TABLE intervention.exercise_sessions IS 'local_state permite reanudar si se pierde conexión (offline-first Flutter).';


-- =============================================================
-- SCHEMA: tracking
-- Series temporales, recalibración automática, alertas
-- =============================================================

-- Snapshot periódico del progreso (generado tras cada sesión completada)
CREATE TABLE tracking.progress_snapshots (
    id                  UUID NOT NULL DEFAULT uuid_generate_v4(),
    student_id          UUID NOT NULL REFERENCES academic.students(id),
    student_path_id     UUID NOT NULL REFERENCES intervention.student_paths(id),
    snapshot_date       DATE NOT NULL DEFAULT CURRENT_DATE,
    -- Métricas de la ventana de N sesiones anteriores
    sessions_count      SMALLINT NOT NULL,
    avg_accuracy_pct    FLOAT NOT NULL,
    avg_response_ms     INT,
    errors_per_minute   FLOAT,
    current_difficulty  SMALLINT NOT NULL,
    -- Resultado de recalibración automática
    recalibration_event TEXT,                      -- NULL | 'LEVEL_UP' | 'STAGNATION_DETECTED'
    -- En tablas particionadas la PK y los UNIQUE deben incluir la columna de partición
    PRIMARY KEY (id, snapshot_date),
    UNIQUE (student_id, student_path_id, snapshot_date)
)
PARTITION BY RANGE (snapshot_date);               -- particionar por año para tablas grandes

-- Partición inicial (se crea una por año en producción)
CREATE TABLE tracking.progress_snapshots_2025
    PARTITION OF tracking.progress_snapshots
    FOR VALUES FROM ('2025-01-01') TO ('2026-01-01');

CREATE TABLE tracking.progress_snapshots_2026
    PARTITION OF tracking.progress_snapshots
    FOR VALUES FROM ('2026-01-01') TO ('2027-01-01');

-- Alertas de estancamiento enviadas al docente
CREATE TABLE tracking.alerts (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    student_id          UUID NOT NULL REFERENCES academic.students(id),
    teacher_id          UUID NOT NULL REFERENCES auth.users(id),
    alert_type          TEXT NOT NULL,             -- 'STAGNATION' | 'LEVEL_UP' | 'INACTIVITY'
    message             TEXT NOT NULL,
    is_read             BOOLEAN NOT NULL DEFAULT FALSE,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    read_at             TIMESTAMPTZ
);


-- =============================================================
-- SCHEMA: reporting
-- Solicitudes y archivos PDF generados por ReportLab
-- =============================================================

CREATE TABLE reporting.report_requests (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    requested_by    UUID NOT NULL REFERENCES auth.users(id),
    student_id      UUID NOT NULL REFERENCES academic.students(id),
    report_type     TEXT NOT NULL,                 -- 'PARENT_SUMMARY' | 'SPECIALIST_FULL' | 'GROUP_OVERVIEW'
    status          TEXT NOT NULL DEFAULT 'PENDING', -- 'PENDING'|'GENERATING'|'READY'|'FAILED'
    file_url        TEXT,                          -- URL firmada en object storage (S3/MinIO)
    expires_at      TIMESTAMPTZ,                   -- URL con expiración para proteger datos clínicos
    requested_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at    TIMESTAMPTZ
);


-- =============================================================
-- SCHEMA: audit
-- Log inmutable de acciones críticas (INSERT ONLY)
-- =============================================================

CREATE TABLE audit.audit_log (
    id              BIGSERIAL PRIMARY KEY,         -- BIGSERIAL para append rápido
    event_time      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    actor_id        UUID,                          -- auth.users.id (NULL si es proceso interno)
    actor_role      auth.user_role,
    action          TEXT NOT NULL,                 -- 'LOGIN'|'DIAGNOSIS_VIEWED'|'REPORT_GENERATED'|...
    target_table    TEXT,                          -- tabla afectada
    target_id       UUID,                          -- PK del registro afectado
    ip_address      INET,
    user_agent      TEXT,
    metadata        JSONB                          -- detalles adicionales sin schema fijo
);

-- Trigger para bloquear UPDATE y DELETE en audit_log
CREATE OR REPLACE FUNCTION audit.prevent_modification()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'audit_log es de solo inserción. No se permiten UPDATE ni DELETE.';
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER audit_log_immutable
    BEFORE UPDATE OR DELETE ON audit.audit_log
    FOR EACH ROW EXECUTE FUNCTION audit.prevent_modification();


-- =============================================================
-- ÍNDICES CLAVE
-- =============================================================

-- Auth
CREATE INDEX idx_refresh_tokens_user     ON auth.refresh_tokens(user_id) WHERE revoked_at IS NULL;

-- Academic
CREATE INDEX idx_students_group          ON academic.students(group_id);
CREATE INDEX idx_groups_teacher          ON academic.groups(teacher_id);

-- Assessment
CREATE INDEX idx_responses_assignment    ON assessment.student_responses(assignment_id);
CREATE INDEX idx_assignments_student     ON assessment.test_assignments(student_id);

-- Diagnosis
CREATE INDEX idx_diagnoses_student       ON diagnosis.diagnoses(student_id);
CREATE INDEX idx_diagnoses_subtype       ON diagnosis.diagnoses(subtype);

-- Intervention
CREATE INDEX idx_exercise_sessions_path  ON intervention.exercise_sessions(student_path_id);
CREATE INDEX idx_exercise_sessions_date  ON intervention.exercise_sessions(started_at);

-- Tracking
CREATE INDEX idx_progress_student        ON tracking.progress_snapshots(student_id, snapshot_date DESC);
CREATE INDEX idx_alerts_teacher_unread   ON tracking.alerts(teacher_id) WHERE is_read = FALSE;

-- Audit (por fecha para queries de compliance)
CREATE INDEX idx_audit_time              ON audit.audit_log(event_time DESC);
CREATE INDEX idx_audit_actor             ON audit.audit_log(actor_id);


-- =============================================================
-- ROW-LEVEL SECURITY (RLS)
-- RBAC implementado directamente en PostgreSQL
-- =============================================================

-- Habilitar RLS en tablas con datos clínicos
ALTER TABLE academic.students         ENABLE ROW LEVEL SECURITY;
ALTER TABLE diagnosis.diagnoses       ENABLE ROW LEVEL SECURITY;
ALTER TABLE intervention.exercise_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE tracking.alerts           ENABLE ROW LEVEL SECURITY;

-- Política: el docente solo ve alumnos de sus propios grupos
-- (La app pasa current_user_id como parámetro de sesión)
CREATE POLICY teacher_sees_own_students ON academic.students
    FOR SELECT
    USING (
        group_id IN (
            SELECT id FROM academic.groups
            WHERE teacher_id = current_setting('app.current_user_id')::UUID
        )
    );

-- Política: el alumno solo ve sus propios datos de sesiones
CREATE POLICY student_sees_own_sessions ON intervention.exercise_sessions
    FOR SELECT
    USING (
        student_path_id IN (
            SELECT sp.id FROM intervention.student_paths sp
            JOIN academic.students s ON s.id = sp.student_id
            JOIN auth.users u ON u.id = s.user_id
            WHERE u.id = current_setting('app.current_user_id')::UUID
        )
    );

-- Política: el docente solo ve alertas dirigidas a él
CREATE POLICY teacher_sees_own_alerts ON tracking.alerts
    FOR SELECT
    USING (teacher_id = current_setting('app.current_user_id')::UUID);


-- =============================================================
-- FUNCIÓN DE UTILIDAD: descifrar nombre de alumno
-- (Solo la app llama esto con la clave de cifrado)
-- =============================================================
CREATE OR REPLACE FUNCTION academic.decrypt_student_name(
    p_student_id UUID,
    p_key TEXT
) RETURNS TEXT AS $$
DECLARE
    v_encrypted BYTEA;
BEGIN
    SELECT full_name INTO v_encrypted
    FROM academic.students WHERE id = p_student_id;

    RETURN pgp_sym_decrypt(v_encrypted, p_key);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;


-- =============================================================
-- DATOS SEMILLA (seed mínimo para desarrollo)
-- =============================================================

-- Modelo ML inicial (sin producción aún)
INSERT INTO diagnosis.ml_model_versions (version_tag, algorithm, train_date, is_production, notes)
VALUES ('v0.1.0-dev', 'RandomForest', CURRENT_DATE, FALSE, 'Modelo inicial en desarrollo');

-- Tests base
INSERT INTO assessment.tests (name, test_type, target_grades) VALUES
    ('Test Léxico-Visual Básico',      'LEXICO_VISUAL',  '{1,2,3}'),
    ('Test Pseudopalabras Nivel 1',    'PSEUDOWORDS',    '{2,3,4}'),
    ('Test Dictado con STT Nivel 1',   'DICTATION_STT',  '{3,4,5,6}');

-- =============================================================
-- FIN DEL SCHEMA
-- =============================================================

-- =============================================================
-- CogniFit Escolar - Integración completa tests + PLN/ML
-- Migración v2 sobre cognifit_schema.sql v1.0
-- Ejecutar en autocommit o fuera de una transacción única porque ALTER TYPE ADD VALUE
-- puede requerir commit antes de usar los nuevos valores en algunas versiones de PostgreSQL.
-- =============================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Nuevos tipos de test para cubrir la batería completa de 9 módulos.
ALTER TYPE assessment.test_type ADD VALUE IF NOT EXISTS 'TEACHER_SCREENING';
ALTER TYPE assessment.test_type ADD VALUE IF NOT EXISTS 'PHONOLOGICAL_AWARENESS';
ALTER TYPE assessment.test_type ADD VALUE IF NOT EXISTS 'LETTERS_SYLLABLES';
ALTER TYPE assessment.test_type ADD VALUE IF NOT EXISTS 'REAL_WORDS';
ALTER TYPE assessment.test_type ADD VALUE IF NOT EXISTS 'SMART_DICTATION';
ALTER TYPE assessment.test_type ADD VALUE IF NOT EXISTS 'CONTROLLED_COPY';
ALTER TYPE assessment.test_type ADD VALUE IF NOT EXISTS 'RAPID_NAMING';
ALTER TYPE assessment.test_type ADD VALUE IF NOT EXISTS 'READING_COMPREHENSION';
ALTER TYPE assessment.test_type ADD VALUE IF NOT EXISTS 'FULL_BATTERY';

-- Perfiles adicionales que el clasificador puede emitir además de dislexia fonológica/visual/mixta.
ALTER TYPE diagnosis.dyslexia_subtype ADD VALUE IF NOT EXISTS 'FLUENCY';
ALTER TYPE diagnosis.dyslexia_subtype ADD VALUE IF NOT EXISTS 'COMPREHENSION';
ALTER TYPE diagnosis.dyslexia_subtype ADD VALUE IF NOT EXISTS 'RISK_ONLY';
ALTER TYPE diagnosis.severity_level ADD VALUE IF NOT EXISTS 'NONE';
ALTER TYPE diagnosis.severity_level ADD VALUE IF NOT EXISTS 'VERY_SEVERE';

-- Catálogo de instrumentos fuente.
CREATE TABLE IF NOT EXISTS assessment.source_instruments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    code TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    source_kind TEXT NOT NULL,
    license_note TEXT,
    implementation_use TEXT NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}'::JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Módulos funcionales de la batería. Un módulo puede generar tests y ejercicios.
CREATE TABLE IF NOT EXISTS assessment.battery_modules (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    module_number SMALLINT NOT NULL UNIQUE CHECK (module_number BETWEEN 1 AND 9),
    module_code TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL,
    phase SMALLINT NOT NULL CHECK (phase BETWEEN 1 AND 6),
    test_type assessment.test_type NOT NULL,
    duration_min SMALLINT,
    duration_max SMALLINT,
    input_modes TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
    captures TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
    source_refs JSONB NOT NULL DEFAULT '[]'::JSONB,
    risk_weight NUMERIC(5,4),
    is_core BOOLEAN NOT NULL DEFAULT TRUE,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS assessment.module_activation_rules (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    rule_code TEXT NOT NULL UNIQUE,
    description TEXT NOT NULL,
    condition JSONB NOT NULL,
    enabled_module_codes TEXT[] NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Extensión no destructiva de tablas existentes de assessment.
ALTER TABLE assessment.tests ADD COLUMN IF NOT EXISTS module_id UUID REFERENCES assessment.battery_modules(id);
ALTER TABLE assessment.tests ADD COLUMN IF NOT EXISTS source_instruments JSONB NOT NULL DEFAULT '[]'::JSONB;
ALTER TABLE assessment.tests ADD COLUMN IF NOT EXISTS scoring_config JSONB NOT NULL DEFAULT '{}'::JSONB;
ALTER TABLE assessment.tests ADD COLUMN IF NOT EXISTS estimated_duration_min SMALLINT;
ALTER TABLE assessment.tests ADD COLUMN IF NOT EXISTS estimated_duration_max SMALLINT;
ALTER TABLE assessment.tests ADD COLUMN IF NOT EXISTS administration_mode TEXT NOT NULL DEFAULT 'APP';

ALTER TABLE assessment.test_items ADD COLUMN IF NOT EXISTS module_id UUID REFERENCES assessment.battery_modules(id);
ALTER TABLE assessment.test_items ADD COLUMN IF NOT EXISTS item_code TEXT;
ALTER TABLE assessment.test_items ADD COLUMN IF NOT EXISTS source_instrument_code TEXT;
ALTER TABLE assessment.test_items ADD COLUMN IF NOT EXISTS construct_area TEXT;
ALTER TABLE assessment.test_items ADD COLUMN IF NOT EXISTS item_kind TEXT;
ALTER TABLE assessment.test_items ADD COLUMN IF NOT EXISTS expected_response_json JSONB NOT NULL DEFAULT '{}'::JSONB;
ALTER TABLE assessment.test_items ADD COLUMN IF NOT EXISTS scoring_config JSONB NOT NULL DEFAULT '{}'::JSONB;
ALTER TABLE assessment.test_items ADD COLUMN IF NOT EXISTS tags TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[];
ALTER TABLE assessment.test_items ADD COLUMN IF NOT EXISTS is_practice BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE assessment.test_items ALTER COLUMN stimulus_text DROP NOT NULL;
ALTER TABLE assessment.test_items ALTER COLUMN expected_response DROP NOT NULL;

ALTER TABLE assessment.test_assignments ADD COLUMN IF NOT EXISTS battery_mode TEXT NOT NULL DEFAULT 'FULL' CHECK (battery_mode IN ('QUICK','FULL','FOLLOW_UP'));
ALTER TABLE assessment.test_assignments ADD COLUMN IF NOT EXISTS teacher_screening_score NUMERIC(5,2);
ALTER TABLE assessment.test_assignments ADD COLUMN IF NOT EXISTS teacher_screening_flags JSONB NOT NULL DEFAULT '[]'::JSONB;

CREATE TABLE IF NOT EXISTS assessment.test_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    assignment_id UUID NOT NULL REFERENCES assessment.test_assignments(id) ON DELETE CASCADE,
    module_id UUID NOT NULL REFERENCES assessment.battery_modules(id),
    session_status TEXT NOT NULL DEFAULT 'IN_PROGRESS' CHECK (session_status IN ('IN_PROGRESS','COMPLETED','ABANDONED','SYNC_PENDING')),
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    device_id TEXT,
    app_version TEXT,
    raw_client_payload JSONB NOT NULL DEFAULT '{}'::JSONB,
    UNIQUE (assignment_id, module_id)
);

ALTER TABLE assessment.student_responses ADD COLUMN IF NOT EXISTS session_id UUID REFERENCES assessment.test_sessions(id) ON DELETE CASCADE;
ALTER TABLE assessment.student_responses ADD COLUMN IF NOT EXISTS module_id UUID REFERENCES assessment.battery_modules(id);
ALTER TABLE assessment.student_responses ADD COLUMN IF NOT EXISTS normalized_response TEXT;
ALTER TABLE assessment.student_responses ADD COLUMN IF NOT EXISTS expected_text TEXT;
ALTER TABLE assessment.student_responses ADD COLUMN IF NOT EXISTS capture_modality TEXT;
ALTER TABLE assessment.student_responses ADD COLUMN IF NOT EXISTS response_audio_url TEXT;
ALTER TABLE assessment.student_responses ADD COLUMN IF NOT EXISTS stt_confidence NUMERIC(5,4);
ALTER TABLE assessment.student_responses ADD COLUMN IF NOT EXISTS edit_distance INT;
ALTER TABLE assessment.student_responses ADD COLUMN IF NOT EXISTS phonetic_similarity NUMERIC(5,4);
ALTER TABLE assessment.student_responses ADD COLUMN IF NOT EXISTS ngram_overlap NUMERIC(5,4);
ALTER TABLE assessment.student_responses ADD COLUMN IF NOT EXISTS lexicalization_flag BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE assessment.student_responses ADD COLUMN IF NOT EXISTS error_breakdown JSONB NOT NULL DEFAULT '{}'::JSONB;
ALTER TABLE assessment.student_responses ALTER COLUMN raw_response DROP NOT NULL;

-- PRODISLEX: versión compacta de 8 preguntas y banco completo por ciclo.
CREATE TABLE IF NOT EXISTS assessment.teacher_screening_items (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    item_code TEXT NOT NULL UNIQUE,
    prompt TEXT NOT NULL,
    weight NUMERIC(5,2) NOT NULL CHECK (weight >= 0),
    tags TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
    source_note TEXT NOT NULL,
    scale JSONB NOT NULL DEFAULT '[{"label":"Nunca","value":0},{"label":"A veces","value":0.5},{"label":"Frecuente","value":1}]'::JSONB,
    is_active BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS assessment.teacher_screening_results (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    student_id UUID NOT NULL REFERENCES academic.students(id) ON DELETE CASCADE,
    teacher_id UUID NOT NULL REFERENCES auth.users(id),
    assignment_id UUID REFERENCES assessment.test_assignments(id) ON DELETE SET NULL,
    score NUMERIC(5,2) NOT NULL CHECK (score BETWEEN 0 AND 100),
    battery_mode TEXT NOT NULL CHECK (battery_mode IN ('QUICK','FULL')),
    answers JSONB NOT NULL,
    risk_flags JSONB NOT NULL DEFAULT '[]'::JSONB,
    completed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS assessment.prodislex_observation_items (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    cycle TEXT NOT NULL CHECK (cycle IN ('1ciclo','2ciclo','3ciclo')),
    item_code TEXT NOT NULL,
    area TEXT NOT NULL,
    item_text TEXT NOT NULL,
    source_page SMALLINT,
    original_scale TEXT[] NOT NULL DEFAULT ARRAY['SI','NO','SE']::TEXT[],
    tags TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (cycle, item_code)
);

-- Bancos de ítems y contenidos normalizados.
CREATE TABLE IF NOT EXISTS assessment.item_banks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    bank_code TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL,
    source_instrument_code TEXT NOT NULL,
    description TEXT,
    content JSONB NOT NULL,
    license_note TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS assessment.tede_items (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    item_code TEXT NOT NULL UNIQUE,
    bank_code TEXT NOT NULL DEFAULT 'TEDE_ITEM_BANK',
    section TEXT NOT NULL,
    category TEXT NOT NULL,
    item_order SMALLINT NOT NULL,
    stimulus_text TEXT NOT NULL,
    expected_response TEXT,
    tags TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
    source_note TEXT NOT NULL DEFAULT 'TEDE/edtv_6 extraído de PDF'
);

-- Diagnóstico: códigos de error, eventos por respuesta y vector de features estable.
CREATE TABLE IF NOT EXISTS diagnosis.error_codes (
    code TEXT PRIMARY KEY,
    error_type TEXT NOT NULL,
    example TEXT,
    profile_hint TEXT,
    counts_for_risk BOOLEAN NOT NULL DEFAULT TRUE,
    description TEXT
);

CREATE TABLE IF NOT EXISTS diagnosis.response_error_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    response_id UUID NOT NULL REFERENCES assessment.student_responses(id) ON DELETE CASCADE,
    error_code TEXT NOT NULL REFERENCES diagnosis.error_codes(code),
    expected_fragment TEXT,
    produced_fragment TEXT,
    start_index SMALLINT,
    end_index SMALLINT,
    edit_op TEXT,
    confidence NUMERIC(5,4),
    metadata JSONB NOT NULL DEFAULT '{}'::JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS diagnosis.feature_definitions (
    feature_index SMALLINT PRIMARY KEY CHECK (feature_index BETWEEN 0 AND 27),
    feature_name TEXT NOT NULL UNIQUE,
    feature_group TEXT NOT NULL,
    description TEXT NOT NULL,
    source_modules TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[]
);

ALTER TABLE diagnosis.ml_model_versions ADD COLUMN IF NOT EXISTS f1_macro_subtype NUMERIC(5,4);
ALTER TABLE diagnosis.ml_model_versions ADD COLUMN IF NOT EXISTS f1_macro_severity NUMERIC(5,4);
ALTER TABLE diagnosis.ml_model_versions ADD COLUMN IF NOT EXISTS balanced_accuracy NUMERIC(5,4);
ALTER TABLE diagnosis.ml_model_versions ADD COLUMN IF NOT EXISTS sensitivity_high_risk NUMERIC(5,4);
ALTER TABLE diagnosis.ml_model_versions ADD COLUMN IF NOT EXISTS samples_per_class JSONB NOT NULL DEFAULT '{}'::JSONB;
ALTER TABLE diagnosis.ml_model_versions ADD COLUMN IF NOT EXISTS validation_report JSONB NOT NULL DEFAULT '{}'::JSONB;
DO $$ BEGIN
    ALTER TABLE diagnosis.ml_model_versions ADD CONSTRAINT ck_model_production_thresholds
    CHECK (
        is_production = FALSE OR (
            COALESCE(f1_macro_subtype, 0) >= 0.80 AND
            COALESCE(f1_macro_severity, 0) >= 0.75 AND
            COALESCE(balanced_accuracy, 0) >= 0.75 AND
            COALESCE(sensitivity_high_risk, 0) >= 0.85
        )
    );
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

ALTER TABLE diagnosis.diagnoses ADD COLUMN IF NOT EXISTS risk_level TEXT CHECK (risk_level IS NULL OR risk_level IN ('LOW','MEDIUM','HIGH'));
ALTER TABLE diagnosis.diagnoses ADD COLUMN IF NOT EXISTS main_error_codes TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[];
ALTER TABLE diagnosis.diagnoses ADD COLUMN IF NOT EXISTS feature_vector_28 NUMERIC[];
ALTER TABLE diagnosis.diagnoses ADD COLUMN IF NOT EXISTS recommendation_reason TEXT;
DO $$ BEGIN
    ALTER TABLE diagnosis.diagnoses ADD CONSTRAINT ck_feature_vector_28_len
    CHECK (feature_vector_28 IS NULL OR array_length(feature_vector_28, 1) = 28);
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

CREATE TABLE IF NOT EXISTS diagnosis.pipeline_runs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    assignment_id UUID REFERENCES assessment.test_assignments(id) ON DELETE SET NULL,
    test_session_id UUID REFERENCES assessment.test_sessions(id) ON DELETE SET NULL,
    model_version_id UUID NOT NULL REFERENCES diagnosis.ml_model_versions(id),
    pipeline_version TEXT NOT NULL DEFAULT 'pln-v1',
    feature_vector_28 NUMERIC[] NOT NULL CHECK (array_length(feature_vector_28, 1) = 28),
    error_breakdown JSONB NOT NULL,
    module_metrics JSONB NOT NULL DEFAULT '{}'::JSONB,
    subtype diagnosis.dyslexia_subtype NOT NULL,
    severity diagnosis.severity_level,
    risk_probability NUMERIC(5,4) NOT NULL CHECK (risk_probability BETWEEN 0 AND 1),
    risk_level TEXT NOT NULL CHECK (risk_level IN ('LOW','MEDIUM','HIGH')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Intervención: rutas y ejercicios desacoplados del enum clínico para soportar fluidez/comprensión.
CREATE TABLE IF NOT EXISTS intervention.route_templates (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    route_code TEXT NOT NULL UNIQUE,
    profile_code TEXT NOT NULL,
    pattern TEXT NOT NULL,
    ordered_exercise_codes TEXT[] NOT NULL,
    source_rules JSONB NOT NULL DEFAULT '{}'::JSONB,
    is_active BOOLEAN NOT NULL DEFAULT TRUE
);

ALTER TABLE intervention.exercises ADD COLUMN IF NOT EXISTS exercise_code TEXT;
ALTER TABLE intervention.exercises ADD COLUMN IF NOT EXISTS module_id UUID REFERENCES assessment.battery_modules(id);
ALTER TABLE intervention.exercises ADD COLUMN IF NOT EXISTS skill_target TEXT;
ALTER TABLE intervention.exercises ADD COLUMN IF NOT EXISTS objective TEXT;
ALTER TABLE intervention.exercises ADD COLUMN IF NOT EXISTS source_tags TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[];
ALTER TABLE intervention.exercises ADD COLUMN IF NOT EXISTS ui_config JSONB NOT NULL DEFAULT '{}'::JSONB;
CREATE UNIQUE INDEX IF NOT EXISTS ux_exercises_exercise_code ON intervention.exercises(exercise_code) WHERE exercise_code IS NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS ux_learning_paths_name ON intervention.learning_paths(name);
CREATE UNIQUE INDEX IF NOT EXISTS ux_tests_name ON assessment.tests(name);

ALTER TABLE intervention.student_paths ADD COLUMN IF NOT EXISTS route_template_id UUID REFERENCES intervention.route_templates(id);
ALTER TABLE intervention.student_paths ADD COLUMN IF NOT EXISTS route_reason TEXT;

-- Seguimiento: sesiones de diagnóstico acumulables como serie temporal, además de ejercicios.
CREATE TABLE IF NOT EXISTS tracking.diagnosis_ml_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    student_id UUID NOT NULL REFERENCES academic.students(id) ON DELETE CASCADE,
    assignment_id UUID REFERENCES assessment.test_assignments(id) ON DELETE SET NULL,
    diagnosis_id UUID REFERENCES diagnosis.diagnoses(id) ON DELETE SET NULL,
    session_date TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    session_number INT NOT NULL,
    grade SMALLINT NOT NULL CHECK (grade BETWEEN 1 AND 6),
    accuracy NUMERIC(5,4),
    error_rate NUMERIC(5,4),
    avg_response_ms INT,
    feature_vector JSONB NOT NULL DEFAULT '{}'::JSONB,
    feature_vector_28 NUMERIC[],
    error_breakdown JSONB NOT NULL DEFAULT '{}'::JSONB,
    subtype TEXT,
    severity TEXT,
    risk_probability NUMERIC(5,4),
    risk_level TEXT CHECK (risk_level IS NULL OR risk_level IN ('LOW','MEDIUM','HIGH')),
    model_version TEXT,
    exercise_route JSONB NOT NULL DEFAULT '[]'::JSONB,
    exercise_level INT NOT NULL DEFAULT 1,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE tracking.alerts ADD COLUMN IF NOT EXISTS suggested_action TEXT;
ALTER TABLE tracking.alerts ADD COLUMN IF NOT EXISTS urgency TEXT CHECK (urgency IS NULL OR urgency IN ('LOW','MEDIUM','HIGH'));
ALTER TABLE tracking.alerts ADD COLUMN IF NOT EXISTS source_session_id UUID REFERENCES tracking.diagnosis_ml_sessions(id) ON DELETE SET NULL;

-- Índices adicionales.
CREATE INDEX IF NOT EXISTS idx_tests_module ON assessment.tests(module_id);
CREATE INDEX IF NOT EXISTS idx_test_items_module ON assessment.test_items(module_id);
CREATE INDEX IF NOT EXISTS idx_test_sessions_assignment ON assessment.test_sessions(assignment_id);
CREATE INDEX IF NOT EXISTS idx_responses_session ON assessment.student_responses(session_id);
CREATE INDEX IF NOT EXISTS idx_response_error_events_response ON diagnosis.response_error_events(response_id);
CREATE INDEX IF NOT EXISTS idx_pipeline_runs_assignment ON diagnosis.pipeline_runs(assignment_id);
CREATE INDEX IF NOT EXISTS idx_diagnosis_ml_sessions_student_date ON tracking.diagnosis_ml_sessions(student_id, session_date DESC);

-- RLS para tablas nuevas con datos de menores.
ALTER TABLE assessment.teacher_screening_results ENABLE ROW LEVEL SECURITY;
ALTER TABLE assessment.test_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE assessment.student_responses ENABLE ROW LEVEL SECURITY;
ALTER TABLE tracking.diagnosis_ml_sessions ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS teacher_sees_own_screening_results ON assessment.teacher_screening_results;
CREATE POLICY teacher_sees_own_screening_results ON assessment.teacher_screening_results
    FOR SELECT USING (teacher_id = current_setting('app.current_user_id')::UUID);

DROP POLICY IF EXISTS teacher_sees_own_test_sessions ON assessment.test_sessions;
CREATE POLICY teacher_sees_own_test_sessions ON assessment.test_sessions
    FOR SELECT USING (
        assignment_id IN (
            SELECT ta.id FROM assessment.test_assignments ta
            JOIN academic.students s ON s.id = ta.student_id
            JOIN academic.groups g ON g.id = s.group_id
            WHERE g.teacher_id = current_setting('app.current_user_id')::UUID
        )
    );

DROP POLICY IF EXISTS student_sees_own_test_sessions ON assessment.test_sessions;
CREATE POLICY student_sees_own_test_sessions ON assessment.test_sessions
    FOR SELECT USING (
        assignment_id IN (
            SELECT ta.id FROM assessment.test_assignments ta
            JOIN academic.students s ON s.id = ta.student_id
            WHERE s.user_id = current_setting('app.current_user_id')::UUID
        )
    );

DROP POLICY IF EXISTS teacher_sees_own_student_responses ON assessment.student_responses;
CREATE POLICY teacher_sees_own_student_responses ON assessment.student_responses
    FOR SELECT USING (
        assignment_id IN (
            SELECT ta.id FROM assessment.test_assignments ta
            JOIN academic.students s ON s.id = ta.student_id
            JOIN academic.groups g ON g.id = s.group_id
            WHERE g.teacher_id = current_setting('app.current_user_id')::UUID
        )
    );

DROP POLICY IF EXISTS student_sees_own_student_responses ON assessment.student_responses;
CREATE POLICY student_sees_own_student_responses ON assessment.student_responses
    FOR SELECT USING (
        assignment_id IN (
            SELECT ta.id FROM assessment.test_assignments ta
            JOIN academic.students s ON s.id = ta.student_id
            WHERE s.user_id = current_setting('app.current_user_id')::UUID
        )
    );

DROP POLICY IF EXISTS teacher_sees_own_diagnosis_ml_sessions ON tracking.diagnosis_ml_sessions;
CREATE POLICY teacher_sees_own_diagnosis_ml_sessions ON tracking.diagnosis_ml_sessions
    FOR SELECT USING (
        student_id IN (
            SELECT s.id FROM academic.students s
            JOIN academic.groups g ON g.id = s.group_id
            WHERE g.teacher_id = current_setting('app.current_user_id')::UUID
        )
    );

-- =============================================================
-- Seeds
-- =============================================================

INSERT INTO assessment.source_instruments (code, name, source_kind, license_note, implementation_use, metadata)
VALUES
    ('PRODISLEX', 'PRODISLEX Protocolos de Detección y Actuación en Dislexia', 'free_pdf', 'Documento gratuito DISFAM; usar como observación docente, no como diagnóstico clínico.', 'Digitalizar indicadores observacionales y pautas de actuación.', '{}'::JSONB),
    ('TEDE', 'Test Exploratorio de Dislexia Específica', 'free_pdf', 'Usar ítems disponibles en PDFs aportados; validar permisos antes de producción comercial.', 'Banco de letras, sílabas, palabras, pseudopalabras y errores específicos.', '{}'::JSONB),
    ('PROLEXIA_COP', 'PROLEXIA evaluación COP', 'review_pdf', 'Documento de evaluación COP; PROLEXIA comercial requiere licencia.', 'Referencia metodológica para procesos fonológicos, RAN, pseudopalabras y puntuación de riesgo.', '{}'::JSONB),
    ('PROLEC3_REF', 'PROLEC-3', 'commercial_reference', 'Referencia metodológica, no banco de ítems.', 'Diseño de palabras, pseudopalabras y comprensión.', '{}'::JSONB),
    ('DSTJ_REF', 'DST-J', 'commercial_reference', 'Referencia metodológica, no banco de ítems.', 'Denominación rápida y screening 6-11 años.', '{}'::JSONB),
    ('LEE_REF', 'LEE', 'commercial_reference', 'Referencia metodológica, no banco de ítems.', 'Dictado cronometrado, lectura/escritura y fluidez.', '{}'::JSONB),
    ('TALE_REF', 'TALE', 'commercial_reference', 'Referencia metodológica, no banco de ítems.', 'Copia controlada y comparación visual/fonológica.', '{}'::JSONB)
ON CONFLICT (code) DO UPDATE SET
    name = EXCLUDED.name,
    source_kind = EXCLUDED.source_kind,
    license_note = EXCLUDED.license_note,
    implementation_use = EXCLUDED.implementation_use;

INSERT INTO assessment.battery_modules
    (module_number, module_code, title, phase, test_type, duration_min, duration_max, input_modes, captures, source_refs, risk_weight)
VALUES
    (1, 'M01_TEACHER_PRODISLEX_SCREENING', 'Cuestionario docente PRODISLEX digitalizado', 1, 'TEACHER_SCREENING', 2, 3, ARRAY['docente selecciona Nunca/A veces/Frecuente']::TEXT[], ARRAY['teacher_score_0_100', 'risk_flags', 'grade', 'cycle']::TEXT[], '["Protocolo-Dislexia-Primaria-1ciclo.pdf","Protocolo-Dislexia-Primaria-2ciclo.pdf","Protocolo-Dislexia-Primaria-3ciclo.pdf"]'::JSONB, NULL),
    (2, 'M02_PHONOLOGICAL_AWARENESS', 'Conciencia fonológica', 2, 'PHONOLOGICAL_AWARENESS', 4, 5, ARRAY['voz/STT o selección táctil']::TEXT[], ARRAY['accuracy', 'error_code', 'response_time_ms', 'audio_uri']::TEXT[], '["PROLEXIA_evaluacion_COP.pdf","referencia DST-J del contexto"]'::JSONB, NULL),
    (3, 'M03_LETTERS_SYLLABLES', 'Letras y sílabas', 2, 'LETTERS_SYLLABLES', 3, 4, ARRAY['lectura en voz alta con STT o registro docente']::TEXT[], ARRAY['expected', 'produced', 'accuracy', 'response_time_ms', 'OMI/SUS/INV/ROT']::TEXT[], '["TEDE Parte 1","edtv_6.pdf fichas"]'::JSONB, NULL),
    (4, 'M04_REAL_WORDS', 'Palabras reales', 2, 'REAL_WORDS', 3, 4, ARRAY['lectura en voz alta']::TEXT[], ARRAY['precision', 'words_per_minute', 'autocorrections', 'word_error_rate']::TEXT[], '["TEDE","PROLEC-3 como referencia metodológica"]'::JSONB, NULL),
    (5, 'M05_PSEUDOWORDS', 'Pseudopalabras', 2, 'PSEUDOWORDS', 3, 4, ARRAY['lectura en voz alta y/o escritura']::TEXT[], ARRAY['pseudo_error_rate', 'lexicalization_flag', 'phonetic_similarity', 'ngram_overlap']::TEXT[], '["TEDE Parte 2","PROLEXIA lectura/deletreo/dictado de pseudopalabras","PROLEC-3 como referencia metodológica"]'::JSONB, 0.25),
    (6, 'M06_SMART_DICTATION', 'Dictado inteligente', 2, 'SMART_DICTATION', 4, 5, ARRAY['TTS reproduce, alumno escribe; opcional STT para lectura posterior']::TEXT[], ARRAY['expected_text', 'produced_text', 'edit_distance', 'metaphone_similarity', 'phonological_vs_orthographic_error']::TEXT[], '["TEDE","LEE como referencia metodológica"]'::JSONB, NULL),
    (7, 'M07_CONTROLLED_COPY', 'Copia controlada', 2, 'CONTROLLED_COPY', 2, 3, ARRAY['texto visible, alumno copia']::TEXT[], ARRAY['copy_error_rate', 'dictation_copy_gap', 'visual_error_flags', 'graphomotor_notes']::TEXT[], '["TALE/LEE como referencia metodológica","PRODISLEX copiados"]'::JSONB, NULL),
    (8, 'M08_RAPID_NAMING', 'Denominación rápida', 2, 'RAPID_NAMING', 2, 3, ARRAY['grilla de 36 estímulos con voz/STT o registro táctil']::TEXT[], ARRAY['total_time_sec', 'ran_errors', 'LEN_rate', 'automation_score']::TEXT[], '["PROLEXIA RAN colores/objetos","DST-J"]'::JSONB, NULL),
    (9, 'M09_READING_COMPREHENSION', 'Comprensión lectora', 2, 'READING_COMPREHENSION', 4, 5, ARRAY['lee texto corto y responde preguntas']::TEXT[], ARRAY['literal_accuracy', 'inferential_accuracy', 'COM_errors', 'read_time_ms']::TEXT[], '["PROLEC-3/DST-J como referencia metodológica","PRODISLEX comprensión lectora"]'::JSONB, NULL)
ON CONFLICT (module_code) DO UPDATE SET
    title = EXCLUDED.title,
    phase = EXCLUDED.phase,
    test_type = EXCLUDED.test_type,
    duration_min = EXCLUDED.duration_min,
    duration_max = EXCLUDED.duration_max,
    input_modes = EXCLUDED.input_modes,
    captures = EXCLUDED.captures,
    source_refs = EXCLUDED.source_refs,
    risk_weight = EXCLUDED.risk_weight;

INSERT INTO assessment.module_activation_rules (rule_code, description, condition, enabled_module_codes)
VALUES
    ('PRODISLEX_SCORE_LT_50', 'Score docente menor a 50: screening rápido con módulos 2, 4 y 8.', '{"teacher_score":{"lt":50}}'::JSONB, ARRAY['M02_PHONOLOGICAL_AWARENESS', 'M04_REAL_WORDS', 'M08_RAPID_NAMING']::TEXT[]),
    ('PRODISLEX_SCORE_GTE_50', 'Score docente mayor o igual a 50: batería completa de 9 módulos.', '{"teacher_score":{"gte":50}}'::JSONB, ARRAY['M01_TEACHER_PRODISLEX_SCREENING', 'M02_PHONOLOGICAL_AWARENESS', 'M03_LETTERS_SYLLABLES', 'M04_REAL_WORDS', 'M05_PSEUDOWORDS', 'M06_SMART_DICTATION', 'M07_CONTROLLED_COPY', 'M08_RAPID_NAMING', 'M09_READING_COMPREHENSION']::TEXT[])
ON CONFLICT (rule_code) DO UPDATE SET
    description = EXCLUDED.description,
    condition = EXCLUDED.condition,
    enabled_module_codes = EXCLUDED.enabled_module_codes;

INSERT INTO assessment.teacher_screening_items (item_code, prompt, weight, tags, source_note, scale)
VALUES
    ('q01_confunde_letras_espejo', 'Confunde letras simétricas o en espejo, como b/d, p/q, u/n o m/w.', 14, ARRAY['ROT', 'visual_superficial']::TEXT[], 'PRODISLEX Lectura/Escritura; TEDE errores específicos visuales.', '[{"label":"Nunca","value":0},{"label":"A veces","value":0.5},{"label":"Frecuente","value":1}]'::JSONB),
    ('q02_invierte_orden', 'Cambia el orden de letras o sílabas dentro de las palabras.', 13, ARRAY['INV', 'fonologico_mixto']::TEXT[], 'PRODISLEX Lectura/Escritura; TEDE inversiones.', '[{"label":"Nunca","value":0},{"label":"A veces","value":0.5},{"label":"Frecuente","value":1}]'::JSONB),
    ('q03_omite_agrega', 'Omite o añade letras, sílabas o palabras al leer o escribir.', 13, ARRAY['OMI', 'ADD', 'fonologico']::TEXT[], 'PRODISLEX Lectura/Escritura; TEDE omisiones/agregados.', '[{"label":"Nunca","value":0},{"label":"A veces","value":0.5},{"label":"Frecuente","value":1}]'::JSONB),
    ('q04_sustituye_letras', 'Cambia unas letras por otras al leer o escribir.', 12, ARRAY['SUS', 'ROT', 'FON']::TEXT[], 'PRODISLEX Lectura/Escritura; TEDE confusiones visuales/auditivas.', '[{"label":"Nunca","value":0},{"label":"A veces","value":0.5},{"label":"Frecuente","value":1}]'::JSONB),
    ('q05_lectura_lenta', 'Lee con lentitud o con baja precisión para su grado escolar.', 12, ARRAY['LEN', 'fluidez']::TEXT[], 'PRODISLEX velocidad/precisión lectora; PROLEXIA lectura/RAN.', '[{"label":"Nunca","value":0},{"label":"A veces","value":0.5},{"label":"Frecuente","value":1}]'::JSONB),
    ('q06_evitar_leer_voz_alta', 'Evita leer en voz alta o muestra malestar ante la lectura.', 10, ARRAY['avoidance', 'risk_flag']::TEXT[], 'PRODISLEX lectura pública/malestar ante lectura.', '[{"label":"Nunca","value":0},{"label":"A veces","value":0.5},{"label":"Frecuente","value":1}]'::JSONB),
    ('q07_dictado_copiado', 'Presenta dificultades en dictados, copiados o al tomar apuntes.', 13, ARRAY['FON', 'VIS', 'writing']::TEXT[], 'PRODISLEX dictado/copiado; TEDE/LEE escritura.', '[{"label":"Nunca","value":0},{"label":"A veces","value":0.5},{"label":"Frecuente","value":1}]'::JSONB),
    ('q08_comprension', 'Tiene baja comprensión lectora o se inventa palabras al leer.', 13, ARRAY['COM', 'LEX']::TEXT[], 'PRODISLEX comprensión lectora; PROLEC/DST-J como referencia metodológica.', '[{"label":"Nunca","value":0},{"label":"A veces","value":0.5},{"label":"Frecuente","value":1}]'::JSONB)
ON CONFLICT (item_code) DO UPDATE SET
    prompt = EXCLUDED.prompt,
    weight = EXCLUDED.weight,
    tags = EXCLUDED.tags,
    source_note = EXCLUDED.source_note,
    scale = EXCLUDED.scale;

INSERT INTO assessment.prodislex_observation_items (cycle, item_code, area, item_text, source_page, original_scale, tags)
VALUES
    ('1ciclo', '1CICLO_001_139319f2', 'Historia clínica', 'Presencia de alteración visual. Especificar:', 4, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY['VISUAL']::TEXT[]),
    ('1ciclo', '1CICLO_002_4445e531', 'Historia clínica', 'Presencia de alteración auditiva. Especificar:', 4, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY[]::TEXT[]),
    ('1ciclo', '1CICLO_003_f558a08a', 'Historia clínica', 'Valoración neurológica. Especificar:', 4, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY[]::TEXT[]),
    ('1ciclo', '1CICLO_004_eebdac2d', 'Historia clínica', 'Otras enfermedades. Especificar:', 4, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY[]::TEXT[]),
    ('1ciclo', '1CICLO_005_40f43f27', 'Historia clínica', 'Antecedentes familiares de dificultades de aprendizaje. Especificar:', 4, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY[]::TEXT[]),
    ('1ciclo', '1CICLO_006_e2e50c4c', 'Discrepancias', 'Cociente intelectual y el éxito escolar.', 4, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY[]::TEXT[]),
    ('1ciclo', '1CICLO_007_e807263b', 'Discrepancias', 'Trabajo oral y trabajo escrito.', 4, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY[]::TEXT[]),
    ('1ciclo', '1CICLO_008_34712916', 'Discrepancias', 'Rendimiento en distintas materias.', 4, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY[]::TEXT[]),
    ('1ciclo', '1CICLO_009_6634ba5b', 'Discrepancias', 'Comprensión y memoria.', 4, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY[]::TEXT[]),
    ('1ciclo', '1CICLO_010_32a371da', 'Discrepancias', 'Días buenos y días malos.', 4, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY[]::TEXT[]),
    ('1ciclo', '1CICLO_011_2735c8f7', 'Discrepancias', 'Esfuerzo-trabajo y la calidad del resultado final.', 4, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY[]::TEXT[]),
    ('1ciclo', '1CICLO_012_3cfbcdd6', 'Comprensión y
expresión oral', 'Presenta dificultades de acceso al léxico (vocabulario).', 5, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY[]::TEXT[]),
    ('1ciclo', '1CICLO_013_ca59aa2a', 'Comprensión y
expresión oral', 'Al hablar, da explicaciones largas y complicadas.', 5, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY[]::TEXT[]),
    ('1ciclo', '1CICLO_014_5f2ff14a', 'Comprensión y
expresión oral', 'Al hablar “juega, más de lo habitual, con el tiempo” (um..., eh...).', 5, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY[]::TEXT[]),
    ('1ciclo', '1CICLO_015_8e82c8c1', 'Comprensión y
expresión oral', 'Le cuesta entender lo que le están explicando.', 5, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY[]::TEXT[]),
    ('1ciclo', '1CICLO_016_1933f74b', 'Comprensión y
expresión oral', 'Presenta dificultades a la hora de narrar experiencias propias, expresar emociones...', 5, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY[]::TEXT[]),
    ('1ciclo', '1CICLO_017_06b83ea7', 'Comprensión y
expresión oral', 'Le cuesta seguir una serie de instrucciones.', 5, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY[]::TEXT[]),
    ('1ciclo', '1CICLO_018_793bc9dd', 'Lectura /
Escritura', 'Presenta dificultades significativas en la adquisición de la lectura.', 5, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY[]::TEXT[]),
    ('1ciclo', '1CICLO_019_6c7e9cc6', 'Lectura /
Escritura', 'Presenta dificultades significativas en la adquisición de la escritura.', 5, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY[]::TEXT[]),
    ('1ciclo', '1CICLO_020_12d7c802', 'Lectura /
Escritura', 'Presenta dificultades en palabras multisilábicas.', 5, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY[]::TEXT[]),
    ('1ciclo', '1CICLO_021_d0e16ad2', 'Lectura /
Escritura', 'Aversión a la lectura y la escritura.', 5, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY[]::TEXT[]),
    ('1ciclo', '1CICLO_022_b6ff242f', 'Lectura /
Escritura', 'Cambia, muy frecuentemente, el orden de las letras-sílabas dentro de las palabras (inversión).', 5, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY['INV']::TEXT[]),
    ('1ciclo', '1CICLO_023_372b444e', 'Lectura /
Escritura', 'Omite o añade letras, sílabas o palabras (omisiones y adiciones) muy frecuentemente.', 5, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY['OMI', 'ADD']::TEXT[]),
    ('1ciclo', '1CICLO_024_3a065b4e', 'Lectura /
Escritura', 'Confunde letras simétricas “en espejo” (rotaciones) muy frecuentemente.', 5, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY['ROT']::TEXT[]),
    ('1ciclo', '1CICLO_025_4e776c94', 'Lectura /
Escritura', 'Cambia letras por otras (sustituciones) muy frecuentemente.', 5, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY['SUS']::TEXT[]),
    ('1ciclo', '1CICLO_026_b34e4779', 'Lectura /
Escritura', 'Junta y separa palabras de forma inadecuada (uniones-fragmentaciones) muy frecuentemente.', 5, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY['UNI']::TEXT[]),
    ('1ciclo', '1CICLO_027_44787d09', 'Lectura /
Escritura', 'Presenta dificultades en la segmentación de sonidos.', 5, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY['SEG']::TEXT[]),
    ('1ciclo', '1CICLO_028_0a268867', 'Lectura /
Escritura', 'Presenta dificultades en la unión de sonidos.', 5, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY['UNI']::TEXT[]),
    ('1ciclo', '1CICLO_029_4585144e', 'Lectura /
Escritura', 'Comete un número elevado de faltas de ortografía natural.', 5, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY[]::TEXT[]),
    ('1ciclo', '1CICLO_030_b65e1c80', 'Lectura /
Escritura', 'Le cuesta integrar las reglas ortográficas trabajadas en clase.', 5, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY[]::TEXT[]),
    ('1ciclo', '1CICLO_031_589efe7c', 'Lectura /
Escritura', 'Comete un número elevado de errores de sintaxis.', 5, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY[]::TEXT[]),
    ('1ciclo', '1CICLO_032_9836bfca', 'Lectura /
Escritura', 'Su nivel lector se halla muy por debajo del grupo clase.', 5, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY[]::TEXT[]),
    ('1ciclo', '1CICLO_033_9b5db695', 'Lectura /
Escritura', 'Se salta muy frecuentemente renglones al leer.', 5, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY[]::TEXT[]),
    ('1ciclo', '1CICLO_034_fa90324c', 'Lectura /
Escritura', 'Se inventa palabras al leer o realizar un explicación oral.', 5, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY[]::TEXT[]),
    ('1ciclo', '1CICLO_035_f42854bb', 'Lectura /
Escritura', 'Tiene una baja o nula comprensión lectora.', 5, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY['COM']::TEXT[]),
    ('1ciclo', '1CICLO_036_3b82eb56', 'Lectura /
Escritura', 'Muestra alto grado de malestar ante la lectura.', 5, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY[]::TEXT[]),
    ('1ciclo', '1CICLO_037_207e06dc', 'Lectura /
Escritura', 'Presenta dificultades a la hora de realizar un dictado (no sigue, se pierde, etc.).', 5, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY['DICT']::TEXT[]),
    ('1ciclo', '1CICLO_038_a831c16e', 'Lectura /
Escritura', 'Comete, muy frecuentemente, un número elevado de errores en los copiados.', 5, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY['COPY']::TEXT[]),
    ('1ciclo', '1CICLO_039_a6531ca3', 'Lectura /
Escritura', 'Presenta dificultades significativas en la calidad del grafismo y la organización del espacio.', 5, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY[]::TEXT[]),
    ('1ciclo', '1CICLO_040_5fbb5435', 'Lectura /
Escritura', 'Mayor dificultad para el aprendizaje de lenguas (castellano, catalán, inglés...).', 6, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY[]::TEXT[]),
    ('1ciclo', '1CICLO_041_7bc20605', 'Matemáticas y
comprensión del
tiempo', 'Dificultades en el cálculo mental.', 6, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY[]::TEXT[]),
    ('1ciclo', '1CICLO_042_6b65e2b6', 'Matemáticas y
comprensión del
tiempo', 'Dificultades persistentes en la interpretación y el uso de símbolos matemáticos.', 6, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY[]::TEXT[]),
    ('1ciclo', '1CICLO_043_a77ec7b7', 'Matemáticas y
comprensión del
tiempo', 'Dificultades en la asociación número-cantidad.', 6, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY[]::TEXT[]),
    ('1ciclo', '1CICLO_044_90c30742', 'Matemáticas y
comprensión del
tiempo', 'Presenta dificultades significativas en la integración del concepto de temporalidad (días, meses, horas, fechas, estaciones del año).', 6, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY[]::TEXT[]),
    ('1ciclo', '1CICLO_045_816b882e', 'Matemáticas y
comprensión del
tiempo', 'Confusión significativa en el vocabulario y en los conceptos temporales (hoy, mañana, antes, después, ahora, luego, primero, segundo...).', 6, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY[]::TEXT[]),
    ('1ciclo', '1CICLO_046_aab24040', 'Matemáticas y
comprensión del
tiempo', 'Presenta dificultades significativas en integrar las tablas de multiplicar.', 6, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY[]::TEXT[]),
    ('1ciclo', '1CICLO_047_34d87917', 'Matemáticas y
comprensión del
tiempo', 'Presenta dificultades significativas en la comprensión y resolución de los problemas.', 6, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY[]::TEXT[]),
    ('1ciclo', '1CICLO_048_df03ca2c', 'Aspectos cognitivos:
memoria,
atención y
concentración,
percepción,
orientación,
secuenciación', 'Presenta dificultades a la hora de copiar de la pizarra.', 6, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY['COPY']::TEXT[]),
    ('1ciclo', '1CICLO_049_db82c973', 'Aspectos cognitivos:
memoria,
atención y
concentración,
percepción,
orientación,
secuenciación', 'Se queja del movimiento de las letras en la lectura y/o la escritura.', 6, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY['ROT']::TEXT[]),
    ('1ciclo', '1CICLO_050_273e263e', 'Aspectos cognitivos:
memoria,
atención y
concentración,
percepción,
orientación,
secuenciación', 'Presenta dificultades a la hora de integrar y automatizar el abecedario.', 6, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY[]::TEXT[]),
    ('1ciclo', '1CICLO_051_90ff5495', 'Aspectos cognitivos:
memoria,
atención y
concentración,
percepción,
orientación,
secuenciación', 'Confusión frecuente en el vocabulario y en el concepto vinculado con la orientación espacial (derecha, izquierda, arriba, abajo).', 6, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY['VISUAL']::TEXT[]),
    ('1ciclo', '1CICLO_052_d4ece097', 'Aspectos cognitivos:
memoria,
atención y
concentración,
percepción,
orientación,
secuenciación', 'Baja memoria para datos, etc.', 6, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY[]::TEXT[]),
    ('1ciclo', '1CICLO_053_8ee13441', 'Aspectos cognitivos:
memoria,
atención y
concentración,
percepción,
orientación,
secuenciación', 'Baja memoria para instrucciones, mensajes, recados, etc.', 6, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY[]::TEXT[]),
    ('1ciclo', '1CICLO_054_017d659f', 'Aspectos cognitivos:
memoria,
atención y
concentración,
percepción,
orientación,
secuenciación', 'Presenta dificultades para recordar lo aprendido el día anterior.', 6, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY[]::TEXT[]),
    ('1ciclo', '1CICLO_055_8cd33c58', 'Aspectos cognitivos:
memoria,
atención y
concentración,
percepción,
orientación,
secuenciación', 'Presenta serias dificultades a la hora de recordar información recibida por la vía de la lectura.', 6, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY[]::TEXT[]),
    ('1ciclo', '1CICLO_056_f558bd1e', 'Aspectos cognitivos:
memoria,
atención y
concentración,
percepción,
orientación,
secuenciación', 'Buena memoria a largo plazo (caras, experiencias, lugares, etc.).', 6, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY[]::TEXT[]),
    ('1ciclo', '1CICLO_057_9a9c84d4', 'Aspectos cognitivos:
memoria,
atención y
concentración,
percepción,
orientación,
secuenciación', 'Pierde cosas con facilidad (se olvida de dónde ha dejado las cosas, no trae el material necesario a las clases...).', 6, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY[]::TEXT[]),
    ('1ciclo', '1CICLO_058_7cbc5bfa', 'Aspectos cognitivos:
memoria,
atención y
concentración,
percepción,
orientación,
secuenciación', 'Presenta dificultades con el ritmo (poesía, música, etc.).', 6, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY[]::TEXT[]),
    ('1ciclo', '1CICLO_059_ebaf9815', 'Aspectos cognitivos:
memoria,
atención y
concentración,
percepción,
orientación,
secuenciación', 'Presenta dificultades de atención.', 6, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY['ATTENTION']::TEXT[]),
    ('1ciclo', '1CICLO_060_3298c030', 'Salud', 'En ocasiones es propenso a infecciones de oído.', 6, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY[]::TEXT[]),
    ('1ciclo', '1CICLO_061_2f7c4f86', 'Salud', 'Puede presentar frecuentes dolores de barriga y/o de cabeza.', 6, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY[]::TEXT[]),
    ('1ciclo', '1CICLO_062_a98b0330', 'Salud', 'En ocasiones presenta problemas de enuresis y/o encopresis.', 6, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY[]::TEXT[]),
    ('1ciclo', '1CICLO_063_886d7e37', 'Salud', 'Presenta problemas emocionales asociados: ansiedad, depresión, trastornos de alimentación, trastornos del sueño, problemas de conducta…', 6, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY[]::TEXT[]),
    ('1ciclo', '1CICLO_064_a207c41b', 'Salud', 'Presenta alteraciones cutáneas (dermatitis atópica, eritemas...).', 7, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY[]::TEXT[]),
    ('1ciclo', '1CICLO_065_0ac887a3', 'Personalidad y
organización personal', 'Es desordenado.', 7, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY[]::TEXT[]),
    ('1ciclo', '1CICLO_066_2ba6ffb2', 'Personalidad y
organización personal', 'Le cuesta organizarse (pupitre, deberes, objetos personales).', 7, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY[]::TEXT[]),
    ('1ciclo', '1CICLO_067_1e1932c8', 'Personalidad y
organización personal', 'Presenta dificultades a la hora de estudiar de forma independiente.', 7, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY[]::TEXT[]),
    ('1ciclo', '1CICLO_068_d7ad7cc5', 'Personalidad y
organización personal', 'Le cuesta acabar las tareas y/o deberes en el tiempo esperado.', 7, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY[]::TEXT[]),
    ('1ciclo', '1CICLO_069_5475a51e', 'Personalidad y
organización personal', 'Es emocionalmente sensible.', 7, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY[]::TEXT[]),
    ('1ciclo', '1CICLO_070_12373222', 'Personalidad y
organización personal', 'Puede sufrir a menudo cambios bruscos de humor.', 7, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY[]::TEXT[]),
    ('1ciclo', '1CICLO_071_9bb14baa', 'Personalidad y
organización personal', 'Puede tener una mayor capacidad intuitiva.', 7, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY[]::TEXT[]),
    ('1ciclo', '1CICLO_072_f5dfdc0f', 'Personalidad y
organización personal', 'Puede tener un mayor grado de curiosidad, creatividad e imaginación.', 7, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY[]::TEXT[]),
    ('1ciclo', '1CICLO_073_9d914ec9', 'Personalidad y
organización personal', 'Con frecuencia es catalogado de inmaduro.', 7, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY[]::TEXT[]),
    ('1ciclo', '1CICLO_074_4f2bc235', 'Personalidad y
organización personal', 'Insatisfacción escolar (con los iguales y/o el profesorado).', 7, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY[]::TEXT[]),
    ('1ciclo', '1CICLO_075_e6247b90', 'Personalidad y
organización personal', 'Baja motivación hacia los aprendizajes.', 7, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY[]::TEXT[]),
    ('1ciclo', '1CICLO_076_1e682a35', 'Personalidad y
organización personal', 'Con frecuencia es catalogado de “vago”.', 7, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY[]::TEXT[]),
    ('1ciclo', '1CICLO_077_5d932f75', 'Personalidad y
organización personal', 'Baja resistencia a la fatiga (se cansa con facilidad).', 7, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY[]::TEXT[]),
    ('1ciclo', '1CICLO_078_cf343cd8', 'Personalidad y
organización personal', 'Baja autoestima.', 7, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY[]::TEXT[]),
    ('1ciclo', '1CICLO_079_10b4e0ea', 'Personalidad y
organización personal', 'Muy susceptible.', 7, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY[]::TEXT[]),
    ('1ciclo', '1CICLO_080_b8124aea', 'Personalidad y
organización personal', 'Dificultades de adaptación social (restricción social, agresividad, dificultades con las normas, inhibición…).', 7, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY[]::TEXT[]),
    ('1ciclo', '1CICLO_081_6495496d', 'Coordinación
psicomotriz', 'Tiene dificultades en las habilidades motrices finas (torpeza manual y poco dominio de destrezas).', 7, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY[]::TEXT[]),
    ('1ciclo', '1CICLO_082_1fc7e150', 'Coordinación
psicomotriz', 'Presenta dificultades en las habilidades motrices gruesas: coordinación y/o equilibrio (juegos de pelota, en equipo, correr, saltar, etc.).', 7, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY[]::TEXT[]),
    ('1ciclo', '1CICLO_083_8c125549', 'Coordinación
psicomotriz', 'Con mayor frecuencia que el resto, confunde izquierda-derecha, arriba-abajo, delante- detrás.', 7, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY[]::TEXT[]),
    ('1ciclo', '1CICLO_084_27b14730', 'Coordinación
psicomotriz', 'Dificultades para realizar secuencias motrices.', 7, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY[]::TEXT[]),
    ('2ciclo', '2CICLO_001_139319f2', 'Historia clínica', 'Presencia de alteración visual. Especificar:', 4, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY['VISUAL']::TEXT[]),
    ('2ciclo', '2CICLO_002_4445e531', 'Historia clínica', 'Presencia de alteración auditiva. Especificar:', 4, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY[]::TEXT[]),
    ('2ciclo', '2CICLO_003_f558a08a', 'Historia clínica', 'Valoración neurológica. Especificar:', 4, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY[]::TEXT[]),
    ('2ciclo', '2CICLO_004_eebdac2d', 'Historia clínica', 'Otras enfermedades. Especificar:', 4, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY[]::TEXT[]),
    ('2ciclo', '2CICLO_005_40f43f27', 'Historia clínica', 'Antecedentes familiares de dificultades de aprendizaje. Especificar:', 4, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY[]::TEXT[]),
    ('2ciclo', '2CICLO_006_e2e50c4c', 'Discrepancias', 'Cociente intelectual y el éxito escolar.', 4, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY[]::TEXT[]),
    ('2ciclo', '2CICLO_007_e807263b', 'Discrepancias', 'Trabajo oral y trabajo escrito.', 4, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY[]::TEXT[]),
    ('2ciclo', '2CICLO_008_34712916', 'Discrepancias', 'Rendimiento en distintas materias.', 4, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY[]::TEXT[]),
    ('2ciclo', '2CICLO_009_6634ba5b', 'Discrepancias', 'Comprensión y memoria.', 4, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY[]::TEXT[]),
    ('2ciclo', '2CICLO_010_32a371da', 'Discrepancias', 'Días buenos y días malos.', 4, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY[]::TEXT[]),
    ('2ciclo', '2CICLO_011_2735c8f7', 'Discrepancias', 'Esfuerzo-trabajo y la calidad del resultado final.', 4, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY[]::TEXT[]),
    ('2ciclo', '2CICLO_012_3cfbcdd6', 'Comprensión y
expresión oral', 'Presenta dificultades de acceso al léxico (vocabulario).', 5, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY[]::TEXT[]),
    ('2ciclo', '2CICLO_013_ca59aa2a', 'Comprensión y
expresión oral', 'Al hablar, da explicaciones largas y complicadas.', 5, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY[]::TEXT[]),
    ('2ciclo', '2CICLO_014_b02f4b46', 'Comprensión y
expresión oral', 'Al hablar “juega con el tiempo” (um..., eh...).', 5, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY[]::TEXT[]),
    ('2ciclo', '2CICLO_015_8e82c8c1', 'Comprensión y
expresión oral', 'Le cuesta entender lo que le están explicando.', 5, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY[]::TEXT[]),
    ('2ciclo', '2CICLO_016_1933f74b', 'Comprensión y
expresión oral', 'Presenta dificultades a la hora de narrar experiencias propias, expresar emociones...', 5, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY[]::TEXT[]),
    ('2ciclo', '2CICLO_017_06b83ea7', 'Comprensión y
expresión oral', 'Le cuesta seguir una serie de instrucciones.', 5, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY[]::TEXT[]),
    ('2ciclo', '2CICLO_018_37e35d2e', 'Lectura /
Escritura', 'Presenta dificultades de lectura.', 5, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY[]::TEXT[]),
    ('2ciclo', '2CICLO_019_55d3b098', 'Lectura /
Escritura', 'Presenta dificultades de escritura.', 5, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY[]::TEXT[]),
    ('2ciclo', '2CICLO_020_12d7c802', 'Lectura /
Escritura', 'Presenta dificultades en palabras multisilábicas.', 5, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY[]::TEXT[]),
    ('2ciclo', '2CICLO_021_f0d99e97', 'Lectura /
Escritura', 'Cambia el orden de las letras-sílabas dentro de las palabras (inversión).', 5, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY['INV']::TEXT[]),
    ('2ciclo', '2CICLO_022_5034e0a3', 'Lectura /
Escritura', 'Omite o añade letras, sílabas o palabras (omisiones y adiciones).', 5, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY['OMI', 'ADD']::TEXT[]),
    ('2ciclo', '2CICLO_023_1aa008eb', 'Lectura /
Escritura', 'Confunde letras simétricas “en espejo” (rotaciones).', 5, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY['ROT']::TEXT[]),
    ('2ciclo', '2CICLO_024_71dde6b4', 'Lectura /
Escritura', 'Cambia letras por otras (sustituciones).', 5, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY['SUS']::TEXT[]),
    ('2ciclo', '2CICLO_025_2bad05b1', 'Lectura /
Escritura', 'Junta y separa palabras de forma inadecuada (uniones-fragmentaciones).', 5, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY['UNI']::TEXT[]),
    ('2ciclo', '2CICLO_026_44787d09', 'Lectura /
Escritura', 'Presenta dificultades en la segmentación de sonidos.', 5, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY['SEG']::TEXT[]),
    ('2ciclo', '2CICLO_027_0a268867', 'Lectura /
Escritura', 'Presenta dificultades en la unión de sonidos.', 5, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY['UNI']::TEXT[]),
    ('2ciclo', '2CICLO_028_e305ce33', 'Lectura /
Escritura', 'Comete un número elevado de faltas de ortografía natural y/o arbitraria.', 5, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY[]::TEXT[]),
    ('2ciclo', '2CICLO_029_b65e1c80', 'Lectura /
Escritura', 'Le cuesta integrar las reglas ortográficas trabajadas en clase.', 5, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY[]::TEXT[]),
    ('2ciclo', '2CICLO_030_589efe7c', 'Lectura /
Escritura', 'Comete un número elevado de errores de sintaxis.', 5, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY[]::TEXT[]),
    ('2ciclo', '2CICLO_031_44585465', 'Lectura /
Escritura', 'Presenta dificultades a la hora de identificar conceptos morfosintácticos.', 5, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY[]::TEXT[]),
    ('2ciclo', '2CICLO_032_9f9db834', 'Lectura /
Escritura', 'Comete un número elevado de errores de puntuación (lectura y escritura).', 5, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY[]::TEXT[]),
    ('2ciclo', '2CICLO_033_1f83d686', 'Lectura /
Escritura', 'Su nivel lector es pobre.', 5, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY[]::TEXT[]),
    ('2ciclo', '2CICLO_034_ef869fce', 'Lectura /
Escritura', 'Se salta renglones al leer.', 5, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY[]::TEXT[]),
    ('2ciclo', '2CICLO_035_fa90324c', 'Lectura /
Escritura', 'Se inventa palabras al leer o realizar un explicación oral.', 5, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY[]::TEXT[]),
    ('2ciclo', '2CICLO_036_f0485220', 'Lectura /
Escritura', 'Tiene una baja comprensión lectora.', 5, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY['COM']::TEXT[]),
    ('2ciclo', '2CICLO_037_4743b556', 'Lectura /
Escritura', 'No le gusta leer en público.', 6, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY[]::TEXT[]),
    ('2ciclo', '2CICLO_038_631cc6ed', 'Lectura /
Escritura', 'Comete un número elevado de errores en la lectura.', 6, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY[]::TEXT[]),
    ('2ciclo', '2CICLO_039_207e06dc', 'Lectura /
Escritura', 'Presenta dificultades a la hora de realizar un dictado (no sigue, se pierde, etc.).', 6, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY['DICT']::TEXT[]),
    ('2ciclo', '2CICLO_040_879cf05d', 'Lectura /
Escritura', 'Comete un número elevado de errores en los copiados.', 6, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY['COPY']::TEXT[]),
    ('2ciclo', '2CICLO_041_84a93e42', 'Lectura /
Escritura', 'Presenta dificultades a la hora de tomar apuntes.', 6, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY[]::TEXT[]),
    ('2ciclo', '2CICLO_042_1ceae024', 'Lectura /
Escritura', 'Presenta problemas en la calidad del grafismo y la organización del espacio.', 6, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY[]::TEXT[]),
    ('2ciclo', '2CICLO_043_5fbb5435', 'Lectura /
Escritura', 'Mayor dificultad para el aprendizaje de lenguas (castellano, catalán, inglés...).', 6, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY[]::TEXT[]),
    ('2ciclo', '2CICLO_044_95e76a85', 'Lectura /
Escritura', 'Dificultad para planificar y redactar composiciones escritas.', 6, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY[]::TEXT[]),
    ('2ciclo', '2CICLO_045_7bc20605', 'Matemáticas y
comprensión del
tiempo', 'Dificultades en el cálculo mental.', 6, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY[]::TEXT[]),
    ('2ciclo', '2CICLO_046_ee97184a', 'Matemáticas y
comprensión del
tiempo', 'Presenta dificultades en la interpretación y el uso de símbolos matemáticos.', 6, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY[]::TEXT[]),
    ('2ciclo', '2CICLO_047_a77ec7b7', 'Matemáticas y
comprensión del
tiempo', 'Dificultades en la asociación número-cantidad.', 6, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY[]::TEXT[]),
    ('2ciclo', '2CICLO_048_1bdcaba9', 'Matemáticas y
comprensión del
tiempo', 'Presenta dificultades con el concepto de temporalidad (días, meses, horas, fechas, estaciones del año).', 6, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY[]::TEXT[]),
    ('2ciclo', '2CICLO_049_89ea7e52', 'Matemáticas y
comprensión del
tiempo', 'Confusión en el vocabulario y en los conceptos temporales (hoy, mañana, antes, después, ahora, luego, primero, segundo...).', 6, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY[]::TEXT[]),
    ('2ciclo', '2CICLO_050_38bf5e32', 'Matemáticas y
comprensión del
tiempo', 'Presenta dificultades en aprender las tablas de multiplicar.', 6, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY[]::TEXT[]),
    ('2ciclo', '2CICLO_051_99e070b3', 'Matemáticas y
comprensión del
tiempo', 'Presenta dificultades en la comprensión y resolución de los problemas.', 6, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY[]::TEXT[]),
    ('2ciclo', '2CICLO_052_6dbc5459', 'Aspectos cognitivos:
memoria,
atención y
concentración,
percepción,
orientación,
secuenciación', 'Presenta dificultades a la hora de copiar de la pizarra o de un texto impreso.', 6, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY['COPY']::TEXT[]),
    ('2ciclo', '2CICLO_053_db82c973', 'Aspectos cognitivos:
memoria,
atención y
concentración,
percepción,
orientación,
secuenciación', 'Se queja del movimiento de las letras en la lectura y/o la escritura.', 6, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY['ROT']::TEXT[]),
    ('2ciclo', '2CICLO_054_273e263e', 'Aspectos cognitivos:
memoria,
atención y
concentración,
percepción,
orientación,
secuenciación', 'Presenta dificultades a la hora de integrar y automatizar el abecedario.', 6, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY[]::TEXT[]),
    ('2ciclo', '2CICLO_055_dca1ce38', 'Aspectos cognitivos:
memoria,
atención y
concentración,
percepción,
orientación,
secuenciación', 'Confusión en el vocabulario y en el concepto vinculado con la orientación espacial (derecha, izquierda, arriba, abajo).', 6, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY['VISUAL']::TEXT[]),
    ('2ciclo', '2CICLO_056_d4ece097', 'Aspectos cognitivos:
memoria,
atención y
concentración,
percepción,
orientación,
secuenciación', 'Baja memoria para datos, etc.', 6, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY[]::TEXT[]),
    ('2ciclo', '2CICLO_057_8ee13441', 'Aspectos cognitivos:
memoria,
atención y
concentración,
percepción,
orientación,
secuenciación', 'Baja memoria para instrucciones, mensajes, recados, etc.', 6, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY[]::TEXT[]),
    ('2ciclo', '2CICLO_058_017d659f', 'Aspectos cognitivos:
memoria,
atención y
concentración,
percepción,
orientación,
secuenciación', 'Presenta dificultades para recordar lo aprendido el día anterior.', 6, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY[]::TEXT[]),
    ('2ciclo', '2CICLO_059_80a9cf06', 'Aspectos cognitivos:
memoria,
atención y
concentración,
percepción,
orientación,
secuenciación', 'Presenta serias dificultades para recordar información recibida por la vía de la lectura.', 6, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY[]::TEXT[]),
    ('2ciclo', '2CICLO_060_f558bd1e', 'Aspectos cognitivos:
memoria,
atención y
concentración,
percepción,
orientación,
secuenciación', 'Buena memoria a largo plazo (caras, experiencias, lugares, etc.).', 7, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY[]::TEXT[]),
    ('2ciclo', '2CICLO_061_9a9c84d4', 'Aspectos cognitivos:
memoria,
atención y
concentración,
percepción,
orientación,
secuenciación', 'Pierde cosas con facilidad (se olvida de dónde ha dejado las cosas, no trae el material necesario a las clases...).', 7, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY[]::TEXT[]),
    ('2ciclo', '2CICLO_062_7cbc5bfa', 'Aspectos cognitivos:
memoria,
atención y
concentración,
percepción,
orientación,
secuenciación', 'Presenta dificultades con el ritmo (poesía, música, etc.).', 7, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY[]::TEXT[]),
    ('2ciclo', '2CICLO_063_ebaf9815', 'Aspectos cognitivos:
memoria,
atención y
concentración,
percepción,
orientación,
secuenciación', 'Presenta dificultades de atención.', 7, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY['ATTENTION']::TEXT[]),
    ('2ciclo', '2CICLO_064_3298c030', 'Salud', 'En ocasiones es propenso a infecciones de oído.', 7, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY[]::TEXT[]),
    ('2ciclo', '2CICLO_065_cc82a0f2', 'Salud', 'Presenta frecuentes dolores de barriga y/o de cabeza.', 7, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY[]::TEXT[]),
    ('2ciclo', '2CICLO_066_a98b0330', 'Salud', 'En ocasiones presenta problemas de enuresis y/o encopresis.', 7, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY[]::TEXT[]),
    ('2ciclo', '2CICLO_067_886d7e37', 'Salud', 'Presenta problemas emocionales asociados: ansiedad, depresión, trastornos de alimentación, trastornos del sueño, problemas de conducta…', 7, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY[]::TEXT[]),
    ('2ciclo', '2CICLO_068_a207c41b', 'Salud', 'Presenta alteraciones cutáneas (dermatitis atópica, eritemas...).', 7, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY[]::TEXT[]),
    ('2ciclo', '2CICLO_069_0ac887a3', 'Personalidad y
organización personal', 'Es desordenado.', 7, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY[]::TEXT[]),
    ('2ciclo', '2CICLO_070_2ba6ffb2', 'Personalidad y
organización personal', 'Le cuesta organizarse (pupitre, deberes, objetos personales).', 7, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY[]::TEXT[]),
    ('2ciclo', '2CICLO_071_79e21f73', 'Personalidad y
organización personal', 'Le cuesta tener los libros/cuadernos encesarios en el lugar apropiado.', 7, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY[]::TEXT[]),
    ('2ciclo', '2CICLO_072_1e1932c8', 'Personalidad y
organización personal', 'Presenta dificultades a la hora de estudiar de forma independiente.', 7, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY[]::TEXT[]),
    ('2ciclo', '2CICLO_073_d7ad7cc5', 'Personalidad y
organización personal', 'Le cuesta acabar las tareas y/o deberes en el tiempo esperado.', 7, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY[]::TEXT[]),
    ('2ciclo', '2CICLO_074_5475a51e', 'Personalidad y
organización personal', 'Es emocionalmente sensible.', 7, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY[]::TEXT[]),
    ('2ciclo', '2CICLO_075_12373222', 'Personalidad y
organización personal', 'Puede sufrir a menudo cambios bruscos de humor.', 7, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY[]::TEXT[]),
    ('2ciclo', '2CICLO_076_9bb14baa', 'Personalidad y
organización personal', 'Puede tener una mayor capacidad intuitiva.', 7, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY[]::TEXT[]),
    ('2ciclo', '2CICLO_077_f5dfdc0f', 'Personalidad y
organización personal', 'Puede tener un mayor grado de curiosidad, creatividad e imaginación.', 7, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY[]::TEXT[]),
    ('2ciclo', '2CICLO_078_9d914ec9', 'Personalidad y
organización personal', 'Con frecuencia es catalogado de inmaduro.', 7, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY[]::TEXT[]),
    ('2ciclo', '2CICLO_079_4f2bc235', 'Personalidad y
organización personal', 'Insatisfacción escolar (con los iguales y/o el profesorado).', 7, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY[]::TEXT[]),
    ('2ciclo', '2CICLO_080_e6247b90', 'Personalidad y
organización personal', 'Baja motivación hacia los aprendizajes.', 7, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY[]::TEXT[]),
    ('2ciclo', '2CICLO_081_1e682a35', 'Personalidad y
organización personal', 'Con frecuencia es catalogado de “vago”.', 7, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY[]::TEXT[]),
    ('2ciclo', '2CICLO_082_5d932f75', 'Personalidad y
organización personal', 'Baja resistencia a la fatiga (se cansa con facilidad).', 7, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY[]::TEXT[]),
    ('2ciclo', '2CICLO_083_cf343cd8', 'Personalidad y
organización personal', 'Baja autoestima.', 8, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY[]::TEXT[]),
    ('2ciclo', '2CICLO_084_10b4e0ea', 'Personalidad y
organización personal', 'Muy susceptible.', 8, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY[]::TEXT[]),
    ('2ciclo', '2CICLO_085_b8124aea', 'Personalidad y
organización personal', 'Dificultades de adaptación social (restricción social, agresividad, dificultades con las normas, inhibición…).', 8, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY[]::TEXT[]),
    ('2ciclo', '2CICLO_086_6495496d', 'Coordinación
psicomotriz', 'Tiene dificultades en las habilidades motrices finas (torpeza manual y poco dominio de destrezas).', 8, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY[]::TEXT[]),
    ('2ciclo', '2CICLO_087_1fc7e150', 'Coordinación
psicomotriz', 'Presenta dificultades en las habilidades motrices gruesas: coordinación y/o equilibrio (juegos de pelota, en equipo, correr, saltar, etc.).', 8, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY[]::TEXT[]),
    ('2ciclo', '2CICLO_088_8b7bb8d6', 'Coordinación
psicomotriz', 'Con frecuencia confunde izquierda-derecha, arriba-abajo, delante-detrás.', 8, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY[]::TEXT[]),
    ('2ciclo', '2CICLO_089_27b14730', 'Coordinación
psicomotriz', 'Dificultades para realizar secuencias motrices.', 8, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY[]::TEXT[]),
    ('3ciclo', '3CICLO_001_139319f2', 'Historia clínica', 'Presencia de alteración visual. Especificar:', 4, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY['VISUAL']::TEXT[]),
    ('3ciclo', '3CICLO_002_4445e531', 'Historia clínica', 'Presencia de alteración auditiva. Especificar:', 4, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY[]::TEXT[]),
    ('3ciclo', '3CICLO_003_f558a08a', 'Historia clínica', 'Valoración neurológica. Especificar:', 4, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY[]::TEXT[]),
    ('3ciclo', '3CICLO_004_eebdac2d', 'Historia clínica', 'Otras enfermedades. Especificar:', 4, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY[]::TEXT[]),
    ('3ciclo', '3CICLO_005_40f43f27', 'Historia clínica', 'Antecedentes familiares de dificultades de aprendizaje. Especificar:', 4, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY[]::TEXT[]),
    ('3ciclo', '3CICLO_006_e2e50c4c', 'Discrepancias', 'Cociente intelectual y el éxito escolar.', 4, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY[]::TEXT[]),
    ('3ciclo', '3CICLO_007_e807263b', 'Discrepancias', 'Trabajo oral y trabajo escrito.', 4, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY[]::TEXT[]),
    ('3ciclo', '3CICLO_008_34712916', 'Discrepancias', 'Rendimiento en distintas materias.', 4, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY[]::TEXT[]),
    ('3ciclo', '3CICLO_009_6634ba5b', 'Discrepancias', 'Comprensión y memoria.', 4, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY[]::TEXT[]),
    ('3ciclo', '3CICLO_010_32a371da', 'Discrepancias', 'Días buenos y días malos.', 4, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY[]::TEXT[]),
    ('3ciclo', '3CICLO_011_2735c8f7', 'Discrepancias', 'Esfuerzo-trabajo y la calidad del resultado final.', 4, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY[]::TEXT[]),
    ('3ciclo', '3CICLO_012_3cfbcdd6', 'Comprensión y
expresión oral', 'Presenta dificultades de acceso al léxico (vocabulario).', 5, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY[]::TEXT[]),
    ('3ciclo', '3CICLO_013_ca59aa2a', 'Comprensión y
expresión oral', 'Al hablar, da explicaciones largas y complicadas.', 5, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY[]::TEXT[]),
    ('3ciclo', '3CICLO_014_b02f4b46', 'Comprensión y
expresión oral', 'Al hablar “juega con el tiempo” (um..., eh...).', 5, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY[]::TEXT[]),
    ('3ciclo', '3CICLO_015_8e82c8c1', 'Comprensión y
expresión oral', 'Le cuesta entender lo que le están explicando.', 5, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY[]::TEXT[]),
    ('3ciclo', '3CICLO_016_1933f74b', 'Comprensión y
expresión oral', 'Presenta dificultades a la hora de narrar experiencias propias, expresar emociones...', 5, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY[]::TEXT[]),
    ('3ciclo', '3CICLO_017_06b83ea7', 'Comprensión y
expresión oral', 'Le cuesta seguir una serie de instrucciones.', 5, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY[]::TEXT[]),
    ('3ciclo', '3CICLO_018_37e35d2e', 'Lectura /
Escritura', 'Presenta dificultades de lectura.', 5, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY[]::TEXT[]),
    ('3ciclo', '3CICLO_019_55d3b098', 'Lectura /
Escritura', 'Presenta dificultades de escritura.', 5, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY[]::TEXT[]),
    ('3ciclo', '3CICLO_020_12d7c802', 'Lectura /
Escritura', 'Presenta dificultades en palabras multisilábicas.', 5, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY[]::TEXT[]),
    ('3ciclo', '3CICLO_021_f0d99e97', 'Lectura /
Escritura', 'Cambia el orden de las letras-sílabas dentro de las palabras (inversión).', 5, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY['INV']::TEXT[]),
    ('3ciclo', '3CICLO_022_5034e0a3', 'Lectura /
Escritura', 'Omite o añade letras, sílabas o palabras (omisiones y adiciones).', 5, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY['OMI', 'ADD']::TEXT[]),
    ('3ciclo', '3CICLO_023_1aa008eb', 'Lectura /
Escritura', 'Confunde letras simétricas “en espejo” (rotaciones).', 5, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY['ROT']::TEXT[]),
    ('3ciclo', '3CICLO_024_71dde6b4', 'Lectura /
Escritura', 'Cambia letras por otras (sustituciones).', 5, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY['SUS']::TEXT[]),
    ('3ciclo', '3CICLO_025_2bad05b1', 'Lectura /
Escritura', 'Junta y separa palabras de forma inadecuada (uniones-fragmentaciones).', 5, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY['UNI']::TEXT[]),
    ('3ciclo', '3CICLO_026_e305ce33', 'Lectura /
Escritura', 'Comete un número elevado de faltas de ortografía natural y/o arbitraria.', 5, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY[]::TEXT[]),
    ('3ciclo', '3CICLO_027_b65e1c80', 'Lectura /
Escritura', 'Le cuesta integrar las reglas ortográficas trabajadas en clase.', 5, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY[]::TEXT[]),
    ('3ciclo', '3CICLO_028_589efe7c', 'Lectura /
Escritura', 'Comete un número elevado de errores de sintaxis.', 5, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY[]::TEXT[]),
    ('3ciclo', '3CICLO_029_44585465', 'Lectura /
Escritura', 'Presenta dificultades a la hora de identificar conceptos morfosintácticos.', 5, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY[]::TEXT[]),
    ('3ciclo', '3CICLO_030_9f9db834', 'Lectura /
Escritura', 'Comete un número elevado de errores de puntuación (lectura y escritura).', 5, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY[]::TEXT[]),
    ('3ciclo', '3CICLO_031_9e596790', 'Lectura /
Escritura', 'Su velocidad y precisión lectora no se corresponden con la edad cronológica.', 5, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY['LEN']::TEXT[]),
    ('3ciclo', '3CICLO_032_ef869fce', 'Lectura /
Escritura', 'Se salta renglones al leer.', 5, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY[]::TEXT[]),
    ('3ciclo', '3CICLO_033_fa90324c', 'Lectura /
Escritura', 'Se inventa palabras al leer o realizar un explicación oral.', 5, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY[]::TEXT[]),
    ('3ciclo', '3CICLO_034_f0485220', 'Lectura /
Escritura', 'Tiene una baja comprensión lectora.', 5, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY['COM']::TEXT[]),
    ('3ciclo', '3CICLO_035_4743b556', 'Lectura /
Escritura', 'No le gusta leer en público.', 5, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY[]::TEXT[]),
    ('3ciclo', '3CICLO_036_631cc6ed', 'Lectura /
Escritura', 'Comete un número elevado de errores en la lectura.', 5, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY[]::TEXT[]),
    ('3ciclo', '3CICLO_037_207e06dc', 'Lectura /
Escritura', 'Presenta dificultades a la hora de realizar un dictado (no sigue, se pierde, etc.).', 6, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY['DICT']::TEXT[]),
    ('3ciclo', '3CICLO_038_879cf05d', 'Lectura /
Escritura', 'Comete un número elevado de errores en los copiados.', 6, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY['COPY']::TEXT[]),
    ('3ciclo', '3CICLO_039_84a93e42', 'Lectura /
Escritura', 'Presenta dificultades a la hora de tomar apuntes.', 6, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY[]::TEXT[]),
    ('3ciclo', '3CICLO_040_1ceae024', 'Lectura /
Escritura', 'Presenta problemas en la calidad del grafismo y la organización del espacio.', 6, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY[]::TEXT[]),
    ('3ciclo', '3CICLO_041_1b600098', 'Lectura /
Escritura', 'Mayor dificultad para el aprendizaje de lenguas (francés, inglés...).', 6, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY[]::TEXT[]),
    ('3ciclo', '3CICLO_042_95e76a85', 'Lectura /
Escritura', 'Dificultad para planificar y redactar composiciones escritas.', 6, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY[]::TEXT[]),
    ('3ciclo', '3CICLO_043_7bc20605', 'Matemáticas y
comprensión del
tiempo', 'Dificultades en el cálculo mental.', 6, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY[]::TEXT[]),
    ('3ciclo', '3CICLO_044_ee97184a', 'Matemáticas y
comprensión del
tiempo', 'Presenta dificultades en la interpretación y el uso de símbolos matemáticos.', 6, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY[]::TEXT[]),
    ('3ciclo', '3CICLO_045_a77ec7b7', 'Matemáticas y
comprensión del
tiempo', 'Dificultades en la asociación número-cantidad.', 6, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY[]::TEXT[]),
    ('3ciclo', '3CICLO_046_1bdcaba9', 'Matemáticas y
comprensión del
tiempo', 'Presenta dificultades con el concepto de temporalidad (días, meses, horas, fechas, estaciones del año).', 6, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY[]::TEXT[]),
    ('3ciclo', '3CICLO_047_0cefc1cb', 'Matemáticas y
comprensión del
tiempo', 'Confusión en el vocabulario relacionado con los conceptos temporales (hoy, mañana, antes, después, ahora, luego, primero, segundo...).', 6, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY[]::TEXT[]),
    ('3ciclo', '3CICLO_048_ab60d9f6', 'Matemáticas y
comprensión del
tiempo', 'Presenta dificultades en automatizar las tablas de multiplicar.', 6, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY[]::TEXT[]),
    ('3ciclo', '3CICLO_049_99e070b3', 'Matemáticas y
comprensión del
tiempo', 'Presenta dificultades en la comprensión y resolución de los problemas.', 6, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY[]::TEXT[]),
    ('3ciclo', '3CICLO_050_6dbc5459', 'Aspectos cognitivos:
memoria,
atención y
concentración,
percepción,
orientación,
secuenciación', 'Presenta dificultades a la hora de copiar de la pizarra o de un texto impreso.', 6, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY['COPY']::TEXT[]),
    ('3ciclo', '3CICLO_051_db82c973', 'Aspectos cognitivos:
memoria,
atención y
concentración,
percepción,
orientación,
secuenciación', 'Se queja del movimiento de las letras en la lectura y/o la escritura.', 6, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY['ROT']::TEXT[]),
    ('3ciclo', '3CICLO_052_fea86919', 'Aspectos cognitivos:
memoria,
atención y
concentración,
percepción,
orientación,
secuenciación', 'Presenta dificultades a la hora de automatizar el abecedario (uso del diccionario, índices…).', 6, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY[]::TEXT[]),
    ('3ciclo', '3CICLO_053_dca1ce38', 'Aspectos cognitivos:
memoria,
atención y
concentración,
percepción,
orientación,
secuenciación', 'Confusión en el vocabulario y en el concepto vinculado con la orientación espacial (derecha, izquierda, arriba, abajo).', 6, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY['VISUAL']::TEXT[]),
    ('3ciclo', '3CICLO_054_1134d930', 'Aspectos cognitivos:
memoria,
atención y
concentración,
percepción,
orientación,
secuenciación', 'Baja memoria para datos/formulas/definiciones, etc.', 6, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY[]::TEXT[]),
    ('3ciclo', '3CICLO_055_8ee13441', 'Aspectos cognitivos:
memoria,
atención y
concentración,
percepción,
orientación,
secuenciación', 'Baja memoria para instrucciones, mensajes, recados, etc.', 6, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY[]::TEXT[]),
    ('3ciclo', '3CICLO_056_017d659f', 'Aspectos cognitivos:
memoria,
atención y
concentración,
percepción,
orientación,
secuenciación', 'Presenta dificultades para recordar lo aprendido el día anterior.', 6, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY[]::TEXT[]),
    ('3ciclo', '3CICLO_057_80a9cf06', 'Aspectos cognitivos:
memoria,
atención y
concentración,
percepción,
orientación,
secuenciación', 'Presenta serias dificultades para recordar información recibida por la vía de la lectura.', 6, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY[]::TEXT[]),
    ('3ciclo', '3CICLO_058_f558bd1e', 'Aspectos cognitivos:
memoria,
atención y
concentración,
percepción,
orientación,
secuenciación', 'Buena memoria a largo plazo (caras, experiencias, lugares, etc.).', 6, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY[]::TEXT[]),
    ('3ciclo', '3CICLO_059_9a9c84d4', 'Aspectos cognitivos:
memoria,
atención y
concentración,
percepción,
orientación,
secuenciación', 'Pierde cosas con facilidad (se olvida de dónde ha dejado las cosas, no trae el material necesario a las clases...).', 7, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY[]::TEXT[]),
    ('3ciclo', '3CICLO_060_7cbc5bfa', 'Aspectos cognitivos:
memoria,
atención y
concentración,
percepción,
orientación,
secuenciación', 'Presenta dificultades con el ritmo (poesía, música, etc.).', 7, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY[]::TEXT[]),
    ('3ciclo', '3CICLO_061_ebaf9815', 'Aspectos cognitivos:
memoria,
atención y
concentración,
percepción,
orientación,
secuenciación', 'Presenta dificultades de atención.', 7, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY['ATTENTION']::TEXT[]),
    ('3ciclo', '3CICLO_062_cc82a0f2', 'Salud', 'Presenta frecuentes dolores de barriga y/o de cabeza.', 7, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY[]::TEXT[]),
    ('3ciclo', '3CICLO_063_886d7e37', 'Salud', 'Presenta problemas emocionales asociados: ansiedad, depresión, trastornos de alimentación, trastornos del sueño, problemas de conducta…', 7, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY[]::TEXT[]),
    ('3ciclo', '3CICLO_064_a207c41b', 'Salud', 'Presenta alteraciones cutáneas (dermatitis atópica, eritemas...).', 7, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY[]::TEXT[]),
    ('3ciclo', '3CICLO_065_0ac887a3', 'Personalidad y
organización personal', 'Es desordenado.', 7, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY[]::TEXT[]),
    ('3ciclo', '3CICLO_066_2ba6ffb2', 'Personalidad y
organización personal', 'Le cuesta organizarse (pupitre, deberes, objetos personales).', 7, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY[]::TEXT[]),
    ('3ciclo', '3CICLO_067_79e21f73', 'Personalidad y
organización personal', 'Le cuesta tener los libros/cuadernos encesarios en el lugar apropiado.', 7, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY[]::TEXT[]),
    ('3ciclo', '3CICLO_068_1e1932c8', 'Personalidad y
organización personal', 'Presenta dificultades a la hora de estudiar de forma independiente.', 7, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY[]::TEXT[]),
    ('3ciclo', '3CICLO_069_d7ad7cc5', 'Personalidad y
organización personal', 'Le cuesta acabar las tareas y/o deberes en el tiempo esperado.', 7, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY[]::TEXT[]),
    ('3ciclo', '3CICLO_070_5475a51e', 'Personalidad y
organización personal', 'Es emocionalmente sensible.', 7, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY[]::TEXT[]),
    ('3ciclo', '3CICLO_071_4ef6620f', 'Personalidad y
organización personal', 'Sufre a menudo cambios bruscos de humor.', 7, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY[]::TEXT[]),
    ('3ciclo', '3CICLO_072_2c3051b5', 'Personalidad y
organización personal', 'Tiene una mayor capacidad intuitiva.', 7, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY[]::TEXT[]),
    ('3ciclo', '3CICLO_073_c89c9855', 'Personalidad y
organización personal', 'Tiene un mayor grado de curiosidad, creatividad e imaginación.', 7, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY[]::TEXT[]),
    ('3ciclo', '3CICLO_074_9d914ec9', 'Personalidad y
organización personal', 'Con frecuencia es catalogado de inmaduro.', 7, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY[]::TEXT[]),
    ('3ciclo', '3CICLO_075_4f2bc235', 'Personalidad y
organización personal', 'Insatisfacción escolar (con los iguales y/o el profesorado).', 7, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY[]::TEXT[]),
    ('3ciclo', '3CICLO_076_e6247b90', 'Personalidad y
organización personal', 'Baja motivación hacia los aprendizajes.', 7, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY[]::TEXT[]),
    ('3ciclo', '3CICLO_077_1e682a35', 'Personalidad y
organización personal', 'Con frecuencia es catalogado de “vago”.', 7, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY[]::TEXT[]),
    ('3ciclo', '3CICLO_078_5d932f75', 'Personalidad y
organización personal', 'Baja resistencia a la fatiga (se cansa con facilidad).', 7, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY[]::TEXT[]),
    ('3ciclo', '3CICLO_079_cf343cd8', 'Personalidad y
organización personal', 'Baja autoestima.', 7, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY[]::TEXT[]),
    ('3ciclo', '3CICLO_080_10b4e0ea', 'Personalidad y
organización personal', 'Muy susceptible.', 7, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY[]::TEXT[]),
    ('3ciclo', '3CICLO_081_b8124aea', 'Personalidad y
organización personal', 'Dificultades de adaptación social (restricción social, agresividad, dificultades con las normas, inhibición…).', 7, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY[]::TEXT[]),
    ('3ciclo', '3CICLO_082_6495496d', 'Coordinación
psicomotriz', 'Tiene dificultades en las habilidades motrices finas (torpeza manual y poco dominio de destrezas).', 8, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY[]::TEXT[]),
    ('3ciclo', '3CICLO_083_1fc7e150', 'Coordinación
psicomotriz', 'Presenta dificultades en las habilidades motrices gruesas: coordinación y/o equilibrio (juegos de pelota, en equipo, correr, saltar, etc.).', 8, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY[]::TEXT[]),
    ('3ciclo', '3CICLO_084_8b7bb8d6', 'Coordinación
psicomotriz', 'Con frecuencia confunde izquierda-derecha, arriba-abajo, delante-detrás.', 8, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY[]::TEXT[]),
    ('3ciclo', '3CICLO_085_27b14730', 'Coordinación
psicomotriz', 'Dificultades para realizar secuencias motrices.', 8, ARRAY['SI', 'NO', 'SE']::TEXT[], ARRAY[]::TEXT[])
ON CONFLICT (cycle, item_code) DO UPDATE SET
    area = EXCLUDED.area,
    item_text = EXCLUDED.item_text,
    source_page = EXCLUDED.source_page,
    original_scale = EXCLUDED.original_scale,
    tags = EXCLUDED.tags;

INSERT INTO assessment.item_banks (bank_code, title, source_instrument_code, description, content, license_note)
VALUES
    ('TEDE_ITEM_BANK', 'TEDE - banco de letras, sílabas y errores específicos', 'TEDE', 'Banco estructurado extraído de TEDE/edtv_6 para módulos 3, 4 y 5.', '{"nivel_lector":{"nombre_letra":["b","m","c","l","a","g","d","p","s","e","ch","q","ñ"],"sonido_letra":["l","s","ll","q","r","t","e","ch","j","y","v","d","m"],"silabas_directas_sonido_simple":["sa","te","mo","lu","ri","fa"],"silabas_directas_doble_sonido":["co","ci","ga","ge","cu","gi"],"silabas_directas_consonantes_dobles":["llo","cha","rri","lle","rru","cho"],"silabas_con_u_muda":["gue","qui","gui","que"],"silabas_indirectas_simple":["is","ac","in","em","ul","ar"],"silabas_indirectas_complejo":["ob","et","ap","ex","af","ad"],"silabas_complejas":["til","pur","mos","cam","sec","lin"],"diptongo_simple":["mia","tue","feu","rou","nio","pia"],"diptongo_complejo":["lian","reis","viul","siap","boim","siec"],"fonogramas_simple":["bra","fli","gro","dru","cle","tri"],"fonogramas_complejo":["glus","pron","tris","plaf","blen","frat"],"fonogramas_diptongo_simple":["brio","crue","trau","glio","pleu","drie"],"fonogramas_diptongo_complejo":["crian","flaun","prien","clous","triun","blauc"]},"errores_especificos":{"confundibles_sonido_opciones":[["y","j","s","ll","ch","f","d","t","l","n"],["f","j","v","b","s","ll","ch","ñ","j","g"],["c","k","t","m","d","y","r","j","m","g"],["b","ñ","t","f","p","g","y","ll","j","f"],["s","t","b","m","p","g","s","j","q","c"],["s","m","n","l","b","ll","j","ñ","m","ch"]],"confundibles_sonido_palabras":["chado","deco","fido","llotio","tarpo","gupa","boso","jallón","pola","querpo","mite","ñuma"],"grafia_semejante_pseudopalabras":["nomino","ohnado","deste","alledo","rechido","chaquillo","laqueta","sagueso","quiguifi","ifjuti","voyate","quellimi"],"inversiones_letras":["bado","dipo","babe","quebo","quido","dudo","bapi","quipi","dubopi","pebade","numo","saute"],"inversiones_palabras_completas":["la","sol","se","las","nos","los","al","es","son","le","sal"],"inversiones_letras_en_palabra":["palta","sobra","trota","plumón","turco","trono","balcón","negar","sabré","calvo","nobel","pardo"],"inversion_orden_silaba":["loma","saco","dato","tapa","tala","cabo","sopa","toga","saca","choca","cala","caro"]},"scoring":{"nivel_lector":"1 punto por respuesta correcta; máximo reportado por TEDE: 100.","errores_especificos":"Puntaje = 71 - número de errores; a mayor puntaje, mejor rendimiento.","response_timeout_seconds":5}}'::JSONB, 'Validar permisos si se usa fuera del MVP académico.'),
    ('COGNIFIT_CONTENT_PACK_V1', 'CogniFit Escolar - content pack v1', 'PRODISLEX', 'Estructura completa de módulos, códigos, rutas y seguimiento.', '{"project":{"name":"CogniFit Escolar","scope":"detección temprana de riesgo de dislexia, intervención adaptativa y seguimiento escolar","important_note":"No sustituye diagnóstico clínico ni evaluación de especialista. Debe presentarse como estimación de riesgo y apoyo docente.","target":"alumnos de primaria en México; foco inicial 1o a 5o grado / 6 a 10 años"},"sources":{"contexto":"contexto_chat_1","prolexia":"prolexia_evaluacion_cop","tede_editable":"test_exploratorio_de_dislexia_especi_fica_tede_editable","edtv":"edtv_6","prodislex_3":"protocolo_dislexia_primaria_3ciclo","prodislex_2":"protocolo_dislexia_primaria_2ciclo","prodislex_1":"protocolo_dislexia_primaria_1ciclo","tede_compress":"pdf_test_tede_compress","mvp":"mvp_cognifit_escolar"},"phase_order":["Fase 1: docente completa PRODISLEX digitalizado","Fase 2: alumno realiza batería Flutter","Fase 3: pipeline PLN/ML procesa respuestas","Fase 4: perfil probabilístico","Fase 5: ruta de intervención adaptativa","Fase 6: seguimiento/recalibración"],"teacher_screening":{"scale":[{"label":"Nunca","value":0},{"label":"A veces","value":0.5},{"label":"Frecuente","value":1}],"score_formula":"score = sum(value * weight) con pesos que suman 100","activation_rules":{"score_lt_50":["module_2_phonological_awareness","module_4_real_words","module_8_rapid_naming"],"score_gte_50":"modules_1_to_9_complete_battery"},"questions":[{"id":"q01_confunde_letras_espejo","prompt":"Confunde letras simétricas o en espejo, como b/d, p/q, u/n o m/w.","source":"PRODISLEX Lectura/Escritura; TEDE errores específicos visuales.","tags":["ROT","visual_superficial"],"weight":14},{"id":"q02_invierte_orden","prompt":"Cambia el orden de letras o sílabas dentro de las palabras.","source":"PRODISLEX Lectura/Escritura; TEDE inversiones.","tags":["INV","fonologico_mixto"],"weight":13},{"id":"q03_omite_agrega","prompt":"Omite o añade letras, sílabas o palabras al leer o escribir.","source":"PRODISLEX Lectura/Escritura; TEDE omisiones/agregados.","tags":["OMI","ADD","fonologico"],"weight":13},{"id":"q04_sustituye_letras","prompt":"Cambia unas letras por otras al leer o escribir.","source":"PRODISLEX Lectura/Escritura; TEDE confusiones visuales/auditivas.","tags":["SUS","ROT","FON"],"weight":12},{"id":"q05_lectura_lenta","prompt":"Lee con lentitud o con baja precisión para su grado escolar.","source":"PRODISLEX velocidad/precisión lectora; PROLEXIA lectura/RAN.","tags":["LEN","fluidez"],"weight":12},{"id":"q06_evitar_leer_voz_alta","prompt":"Evita leer en voz alta o muestra malestar ante la lectura.","source":"PRODISLEX lectura pública/malestar ante lectura.","tags":["avoidance","risk_flag"],"weight":10},{"id":"q07_dictado_copiado","prompt":"Presenta dificultades en dictados, copiados o al tomar apuntes.","source":"PRODISLEX dictado/copiado; TEDE/LEE escritura.","tags":["FON","VIS","writing"],"weight":13},{"id":"q08_comprension","prompt":"Tiene baja comprensión lectora o se inventa palabras al leer.","source":"PRODISLEX comprensión lectora; PROLEC/DST-J como referencia metodológica.","tags":["COM","LEX"],"weight":13}]},"modules":[{"number":1,"id":"teacher_prodislex_screening","title":"Cuestionario docente PRODISLEX digitalizado","phase":1,"sources":["Protocolo-Dislexia-Primaria-1ciclo.pdf","Protocolo-Dislexia-Primaria-2ciclo.pdf","Protocolo-Dislexia-Primaria-3ciclo.pdf"],"duration_min":"2-3","input_mode":"docente selecciona Nunca/A veces/Frecuente","captures":["teacher_score_0_100","risk_flags","grade","cycle"],"activation":"Si score >= 50: batería completa. Si score < 50: screening rápido módulos 2, 4 y 8."},{"number":2,"id":"phonological_awareness","title":"Conciencia fonológica","phase":2,"sources":["PROLEXIA_evaluacion_COP.pdf","referencia DST-J del contexto"],"duration_min":"4-5","input_mode":"voz/STT o selección táctil","task_types":["sonido inicial/final","conteo de sílabas","rimas","omisión de sílaba","sustitución de fonema","inversión de sílaba"],"captures":["accuracy","error_code","response_time_ms","audio_uri"]},{"number":3,"id":"letters_syllables","title":"Letras y sílabas","phase":2,"sources":["TEDE Parte 1","edtv_6.pdf fichas"],"duration_min":"3-4","input_mode":"lectura en voz alta con STT o registro docente","item_bank_ref":"tede_item_bank.nivel_lector","captures":["expected","produced","accuracy","response_time_ms","OMI/SUS/INV/ROT"]},{"number":4,"id":"real_words","title":"Palabras reales","phase":2,"sources":["TEDE","PROLEC-3 como referencia metodológica"],"duration_min":"3-4","input_mode":"lectura en voz alta","item_bank_ref":"TEDE errores específicos: palabras reales e inversión","captures":["precision","words_per_minute","autocorrections","word_error_rate"]},{"number":5,"id":"pseudowords","title":"Pseudopalabras","phase":2,"sources":["TEDE Parte 2","PROLEXIA lectura/deletreo/dictado de pseudopalabras","PROLEC-3 como referencia metodológica"],"duration_min":"3-4","input_mode":"lectura en voz alta y/o escritura","item_bank_ref":"tede_item_bank.errores_especificos.grafia_semejante_pseudopalabras + inversiones_letras","captures":["pseudo_error_rate","lexicalization_flag","phonetic_similarity","ngram_overlap"],"risk_weight":0.25},{"number":6,"id":"smart_dictation","title":"Dictado inteligente","phase":2,"sources":["TEDE","LEE como referencia metodológica"],"duration_min":"4-5","input_mode":"TTS reproduce, alumno escribe; opcional STT para lectura posterior","item_bank_strategy":"usar palabras reales y pseudopalabras del banco, graduadas por nivel","captures":["expected_text","produced_text","edit_distance","metaphone_similarity","phonological_vs_orthographic_error"]},{"number":7,"id":"controlled_copy","title":"Copia controlada","phase":2,"sources":["TALE/LEE como referencia metodológica","PRODISLEX copiados"],"duration_min":"2-3","input_mode":"texto visible, alumno copia","captures":["copy_error_rate","dictation_copy_gap","visual_error_flags","graphomotor_notes"]},{"number":8,"id":"rapid_naming","title":"Denominación rápida","phase":2,"sources":["PROLEXIA RAN colores/objetos","DST-J"],"duration_min":"2-3","input_mode":"grilla de 36 estímulos con voz/STT o registro táctil","stimuli":{"colors":["rojo","azul","verde","amarillo","negro","blanco"],"objects":["casa","sol","luna","mesa","silla","vaso"]},"captures":["total_time_sec","ran_errors","LEN_rate","automation_score"]},{"number":9,"id":"reading_comprehension","title":"Comprensión lectora","phase":2,"sources":["PROLEC-3/DST-J como referencia metodológica","PRODISLEX comprensión lectora"],"duration_min":"4-5","input_mode":"lee texto corto y responde preguntas","item_generation":"textos propios de la app por grado; preguntas literales e inferenciales","captures":["literal_accuracy","inferential_accuracy","COM_errors","read_time_ms"]}],"tede_item_bank":{"nivel_lector":{"nombre_letra":["b","m","c","l","a","g","d","p","s","e","ch","q","ñ"],"sonido_letra":["l","s","ll","q","r","t","e","ch","j","y","v","d","m"],"silabas_directas_sonido_simple":["sa","te","mo","lu","ri","fa"],"silabas_directas_doble_sonido":["co","ci","ga","ge","cu","gi"],"silabas_directas_consonantes_dobles":["llo","cha","rri","lle","rru","cho"],"silabas_con_u_muda":["gue","qui","gui","que"],"silabas_indirectas_simple":["is","ac","in","em","ul","ar"],"silabas_indirectas_complejo":["ob","et","ap","ex","af","ad"],"silabas_complejas":["til","pur","mos","cam","sec","lin"],"diptongo_simple":["mia","tue","feu","rou","nio","pia"],"diptongo_complejo":["lian","reis","viul","siap","boim","siec"],"fonogramas_simple":["bra","fli","gro","dru","cle","tri"],"fonogramas_complejo":["glus","pron","tris","plaf","blen","frat"],"fonogramas_diptongo_simple":["brio","crue","trau","glio","pleu","drie"],"fonogramas_diptongo_complejo":["crian","flaun","prien","clous","triun","blauc"]},"errores_especificos":{"confundibles_sonido_opciones":[["y","j","s","ll","ch","f","d","t","l","n"],["f","j","v","b","s","ll","ch","ñ","j","g"],["c","k","t","m","d","y","r","j","m","g"],["b","ñ","t","f","p","g","y","ll","j","f"],["s","t","b","m","p","g","s","j","q","c"],["s","m","n","l","b","ll","j","ñ","m","ch"]],"confundibles_sonido_palabras":["chado","deco","fido","llotio","tarpo","gupa","boso","jallón","pola","querpo","mite","ñuma"],"grafia_semejante_pseudopalabras":["nomino","ohnado","deste","alledo","rechido","chaquillo","laqueta","sagueso","quiguifi","ifjuti","voyate","quellimi"],"inversiones_letras":["bado","dipo","babe","quebo","quido","dudo","bapi","quipi","dubopi","pebade","numo","saute"],"inversiones_palabras_completas":["la","sol","se","las","nos","los","al","es","son","le","sal"],"inversiones_letras_en_palabra":["palta","sobra","trota","plumón","turco","trono","balcón","negar","sabré","calvo","nobel","pardo"],"inversion_orden_silaba":["loma","saco","dato","tapa","tala","cabo","sopa","toga","saca","choca","cala","caro"]},"scoring":{"nivel_lector":"1 punto por respuesta correcta; máximo reportado por TEDE: 100.","errores_especificos":"Puntaje = 71 - número de errores; a mayor puntaje, mejor rendimiento.","response_timeout_seconds":5}},"error_codes":[{"code":"OMI","type":"Omisión","example":"perro -> pero","profile":"fonológico"},{"code":"SUS","type":"Sustitución","example":"dado -> bado","profile":"visual o fonológico"},{"code":"INV","type":"Inversión","example":"plato -> palto","profile":"fonológico/mixto"},{"code":"ROT","type":"Rotación visual","example":"b<->d, p<->q","profile":"visual/superficial"},{"code":"LEX","type":"Lexicalización","example":"pseudopalabra leída como palabra real cercana","profile":"visual/compensación"},{"code":"SEG","type":"Segmentación","example":"conmigo -> con migo","profile":"fonológico"},{"code":"UNI","type":"Unión","example":"la casa -> lacasa","profile":"fonológico"},{"code":"FON","type":"Error fonológico","example":"guitarra -> gitarra","profile":"fonológico"},{"code":"ADD","type":"Adición","example":"cocina -> cocicina","profile":"mixto"},{"code":"LEN","type":"Lentitud","example":"respuesta correcta pero tardía","profile":"fluidez/automatización"},{"code":"COM","type":"Comprensión","example":"respuesta literal/inferencial incorrecta","profile":"comprensión"},{"code":"ACC","type":"Acento","example":"rápido -> rapido","profile":"ortográfico informativo; no suma al score"}],"pipeline":{"nlp_stack":["spaCy es_core_news_md","python-Levenshtein editops","Metaphone/Soundex adaptado a español","n-gramas de caracteres","TF-IDF","Random Forest o SVM con predict_proba"],"feature_vector_28":["OMI_rate","SUS_rate","INV_rate","ROT_rate","LEX_rate","SEG_rate","UNI_rate","FON_rate","ADD_rate","LEN_rate","accuracy","error_rate","pseudo_vs_word_gap","pseudo_error_rate","word_error_rate","avg_time_norm","std_time_norm","slow_response_rate","avg_phonetic_sim","avg_ngram_overlap","rot_sus_ratio","lex_flag","seg_uni_rate","inv_omi_ratio","module_completion_rate_suggested","dominant_error_concentration_suggested","grade_norm","teacher_score_norm"],"classification_output":{"subtype":["fonologico","visual_superficial","mixto","fluidez","comprension","sin_riesgo"],"severity":["leve","moderado","severo"],"risk_probability":"0.0-1.0","risk_level":{"bajo":"0-30%","medio":"31-65%","alto":"66-100%"}},"decision_rules":["pseudo_vs_word_gap > 0.20 sugiere perfil fonológico","pseudo_vs_word_gap < 0.10 con muchos ROT/LEX sugiere perfil visual/superficial","fallo alto en palabras y pseudopalabras con mezcla FON+ROT sugiere perfil mixto","pocos errores con LEN alto sugiere problema de fluidez/automatización","buena lectura de palabras con COM alto sugiere ruta de comprensión"]},"intervention_routes":[{"profile":"fonologico","pattern":"falla pseudopalabras mucho más que palabras reales; muchos OMI/INV/FON","route":["CF_silabas_N1","CF_fonema_inicial_N1","PS_cv_N1","DIC_palabras_simples_N1"]},{"profile":"visual_superficial","pattern":"muchos ROT b/d/p/q y LEX frecuente","route":["VIS_discriminacion_bd_N1","VIS_memoria_palabras_N1","DEN_rapid_letras_N1"]},{"profile":"mixto","pattern":"falla generalizada; combina FON y ROT","route":["MULTI_silabas_cromaticas_N1","MULTI_lectura_auditiva_N1","CF_silabas_N1","PS_cv_N1"]},{"profile":"fluidez","pattern":"pocos errores pero respuesta lenta","route":["DEN_rapid_colores_N1","LEC_repetida_N1","LEC_temporizador_N1"]},{"profile":"comprension","pattern":"lee palabras bien pero falla comprensión","route":["COMP_textos_cortos_N1","apoyo_auditivo","vocabulario_N1"]}],"tracking":{"advance_rule":"sube de nivel si accuracy > 90% en las últimas 3 sesiones del nivel actual","stagnation_rule":"alerta docente si no mejora en 5 sesiones consecutivas","regression_rule":"si la curva de error tiene pendiente positiva, baja nivel y activa apoyo TTS","production_model_thresholds":{"F1_macro_subtipo":">= 0.80","F1_macro_severidad":">= 0.75","balanced_accuracy":">= 0.75","sensibilidad_alto_riesgo":">= 0.85","muestras_por_clase":">= 50"}}}'::JSONB, 'Incluye referencias metodológicas; no sustituye evaluación clínica.')
ON CONFLICT (bank_code) DO UPDATE SET
    title = EXCLUDED.title,
    source_instrument_code = EXCLUDED.source_instrument_code,
    description = EXCLUDED.description,
    content = EXCLUDED.content,
    license_note = EXCLUDED.license_note;

INSERT INTO assessment.tede_items (item_code, section, category, item_order, stimulus_text, expected_response, tags)
VALUES
    ('TEDE_NL_NOMBRE_LETRA_001', 'nivel_lector', 'nombre_letra', 1, 'b', 'b', ARRAY['ROT', 'TEDE']::TEXT[]),
    ('TEDE_NL_NOMBRE_LETRA_002', 'nivel_lector', 'nombre_letra', 2, 'm', 'm', ARRAY['ROT', 'TEDE']::TEXT[]),
    ('TEDE_NL_NOMBRE_LETRA_003', 'nivel_lector', 'nombre_letra', 3, 'c', 'c', ARRAY['TEDE']::TEXT[]),
    ('TEDE_NL_NOMBRE_LETRA_004', 'nivel_lector', 'nombre_letra', 4, 'l', 'l', ARRAY['TEDE']::TEXT[]),
    ('TEDE_NL_NOMBRE_LETRA_005', 'nivel_lector', 'nombre_letra', 5, 'a', 'a', ARRAY['TEDE']::TEXT[]),
    ('TEDE_NL_NOMBRE_LETRA_006', 'nivel_lector', 'nombre_letra', 6, 'g', 'g', ARRAY['TEDE']::TEXT[]),
    ('TEDE_NL_NOMBRE_LETRA_007', 'nivel_lector', 'nombre_letra', 7, 'd', 'd', ARRAY['ROT', 'TEDE']::TEXT[]),
    ('TEDE_NL_NOMBRE_LETRA_008', 'nivel_lector', 'nombre_letra', 8, 'p', 'p', ARRAY['ROT', 'TEDE']::TEXT[]),
    ('TEDE_NL_NOMBRE_LETRA_009', 'nivel_lector', 'nombre_letra', 9, 's', 's', ARRAY['TEDE']::TEXT[]),
    ('TEDE_NL_NOMBRE_LETRA_010', 'nivel_lector', 'nombre_letra', 10, 'e', 'e', ARRAY['TEDE']::TEXT[]),
    ('TEDE_NL_NOMBRE_LETRA_011', 'nivel_lector', 'nombre_letra', 11, 'ch', 'ch', ARRAY['TEDE']::TEXT[]),
    ('TEDE_NL_NOMBRE_LETRA_012', 'nivel_lector', 'nombre_letra', 12, 'q', 'q', ARRAY['ROT', 'TEDE']::TEXT[]),
    ('TEDE_NL_NOMBRE_LETRA_013', 'nivel_lector', 'nombre_letra', 13, 'ñ', 'ñ', ARRAY['TEDE']::TEXT[]),
    ('TEDE_NL_SONIDO_LETRA_014', 'nivel_lector', 'sonido_letra', 14, 'l', 'l', ARRAY['TEDE']::TEXT[]),
    ('TEDE_NL_SONIDO_LETRA_015', 'nivel_lector', 'sonido_letra', 15, 's', 's', ARRAY['TEDE']::TEXT[]),
    ('TEDE_NL_SONIDO_LETRA_016', 'nivel_lector', 'sonido_letra', 16, 'll', 'll', ARRAY['TEDE']::TEXT[]),
    ('TEDE_NL_SONIDO_LETRA_017', 'nivel_lector', 'sonido_letra', 17, 'q', 'q', ARRAY['ROT', 'TEDE']::TEXT[]),
    ('TEDE_NL_SONIDO_LETRA_018', 'nivel_lector', 'sonido_letra', 18, 'r', 'r', ARRAY['TEDE']::TEXT[]),
    ('TEDE_NL_SONIDO_LETRA_019', 'nivel_lector', 'sonido_letra', 19, 't', 't', ARRAY['TEDE']::TEXT[]),
    ('TEDE_NL_SONIDO_LETRA_020', 'nivel_lector', 'sonido_letra', 20, 'e', 'e', ARRAY['TEDE']::TEXT[]),
    ('TEDE_NL_SONIDO_LETRA_021', 'nivel_lector', 'sonido_letra', 21, 'ch', 'ch', ARRAY['TEDE']::TEXT[]),
    ('TEDE_NL_SONIDO_LETRA_022', 'nivel_lector', 'sonido_letra', 22, 'j', 'j', ARRAY['TEDE']::TEXT[]),
    ('TEDE_NL_SONIDO_LETRA_023', 'nivel_lector', 'sonido_letra', 23, 'y', 'y', ARRAY['TEDE']::TEXT[]),
    ('TEDE_NL_SONIDO_LETRA_024', 'nivel_lector', 'sonido_letra', 24, 'v', 'v', ARRAY['TEDE']::TEXT[]),
    ('TEDE_NL_SONIDO_LETRA_025', 'nivel_lector', 'sonido_letra', 25, 'd', 'd', ARRAY['ROT', 'TEDE']::TEXT[]),
    ('TEDE_NL_SONIDO_LETRA_026', 'nivel_lector', 'sonido_letra', 26, 'm', 'm', ARRAY['ROT', 'TEDE']::TEXT[]),
    ('TEDE_NL_SILABAS_DIRECTAS_SONIDO_SIMPLE_027', 'nivel_lector', 'silabas_directas_sonido_simple', 27, 'sa', 'sa', ARRAY['SYLLABLE', 'TEDE']::TEXT[]),
    ('TEDE_NL_SILABAS_DIRECTAS_SONIDO_SIMPLE_028', 'nivel_lector', 'silabas_directas_sonido_simple', 28, 'te', 'te', ARRAY['SYLLABLE', 'TEDE']::TEXT[]),
    ('TEDE_NL_SILABAS_DIRECTAS_SONIDO_SIMPLE_029', 'nivel_lector', 'silabas_directas_sonido_simple', 29, 'mo', 'mo', ARRAY['SYLLABLE', 'TEDE']::TEXT[]),
    ('TEDE_NL_SILABAS_DIRECTAS_SONIDO_SIMPLE_030', 'nivel_lector', 'silabas_directas_sonido_simple', 30, 'lu', 'lu', ARRAY['SYLLABLE', 'TEDE']::TEXT[]),
    ('TEDE_NL_SILABAS_DIRECTAS_SONIDO_SIMPLE_031', 'nivel_lector', 'silabas_directas_sonido_simple', 31, 'ri', 'ri', ARRAY['SYLLABLE', 'TEDE']::TEXT[]),
    ('TEDE_NL_SILABAS_DIRECTAS_SONIDO_SIMPLE_032', 'nivel_lector', 'silabas_directas_sonido_simple', 32, 'fa', 'fa', ARRAY['SYLLABLE', 'TEDE']::TEXT[]),
    ('TEDE_NL_SILABAS_DIRECTAS_DOBLE_SONIDO_033', 'nivel_lector', 'silabas_directas_doble_sonido', 33, 'co', 'co', ARRAY['SYLLABLE', 'TEDE']::TEXT[]),
    ('TEDE_NL_SILABAS_DIRECTAS_DOBLE_SONIDO_034', 'nivel_lector', 'silabas_directas_doble_sonido', 34, 'ci', 'ci', ARRAY['SYLLABLE', 'TEDE']::TEXT[]),
    ('TEDE_NL_SILABAS_DIRECTAS_DOBLE_SONIDO_035', 'nivel_lector', 'silabas_directas_doble_sonido', 35, 'ga', 'ga', ARRAY['SYLLABLE', 'TEDE']::TEXT[]),
    ('TEDE_NL_SILABAS_DIRECTAS_DOBLE_SONIDO_036', 'nivel_lector', 'silabas_directas_doble_sonido', 36, 'ge', 'ge', ARRAY['SYLLABLE', 'TEDE']::TEXT[]),
    ('TEDE_NL_SILABAS_DIRECTAS_DOBLE_SONIDO_037', 'nivel_lector', 'silabas_directas_doble_sonido', 37, 'cu', 'cu', ARRAY['SYLLABLE', 'TEDE']::TEXT[]),
    ('TEDE_NL_SILABAS_DIRECTAS_DOBLE_SONIDO_038', 'nivel_lector', 'silabas_directas_doble_sonido', 38, 'gi', 'gi', ARRAY['SYLLABLE', 'TEDE']::TEXT[]),
    ('TEDE_NL_SILABAS_DIRECTAS_CONSONANTES_DOBLES_039', 'nivel_lector', 'silabas_directas_consonantes_dobles', 39, 'llo', 'llo', ARRAY['SYLLABLE', 'TEDE']::TEXT[]),
    ('TEDE_NL_SILABAS_DIRECTAS_CONSONANTES_DOBLES_040', 'nivel_lector', 'silabas_directas_consonantes_dobles', 40, 'cha', 'cha', ARRAY['SYLLABLE', 'TEDE']::TEXT[]),
    ('TEDE_NL_SILABAS_DIRECTAS_CONSONANTES_DOBLES_041', 'nivel_lector', 'silabas_directas_consonantes_dobles', 41, 'rri', 'rri', ARRAY['SYLLABLE', 'TEDE']::TEXT[]),
    ('TEDE_NL_SILABAS_DIRECTAS_CONSONANTES_DOBLES_042', 'nivel_lector', 'silabas_directas_consonantes_dobles', 42, 'lle', 'lle', ARRAY['SYLLABLE', 'TEDE']::TEXT[]),
    ('TEDE_NL_SILABAS_DIRECTAS_CONSONANTES_DOBLES_043', 'nivel_lector', 'silabas_directas_consonantes_dobles', 43, 'rru', 'rru', ARRAY['SYLLABLE', 'TEDE']::TEXT[]),
    ('TEDE_NL_SILABAS_DIRECTAS_CONSONANTES_DOBLES_044', 'nivel_lector', 'silabas_directas_consonantes_dobles', 44, 'cho', 'cho', ARRAY['SYLLABLE', 'TEDE']::TEXT[]),
    ('TEDE_NL_SILABAS_CON_U_MUDA_045', 'nivel_lector', 'silabas_con_u_muda', 45, 'gue', 'gue', ARRAY['SYLLABLE', 'TEDE']::TEXT[]),
    ('TEDE_NL_SILABAS_CON_U_MUDA_046', 'nivel_lector', 'silabas_con_u_muda', 46, 'qui', 'qui', ARRAY['ROT', 'SYLLABLE', 'TEDE']::TEXT[]),
    ('TEDE_NL_SILABAS_CON_U_MUDA_047', 'nivel_lector', 'silabas_con_u_muda', 47, 'gui', 'gui', ARRAY['SYLLABLE', 'TEDE']::TEXT[]),
    ('TEDE_NL_SILABAS_CON_U_MUDA_048', 'nivel_lector', 'silabas_con_u_muda', 48, 'que', 'que', ARRAY['ROT', 'SYLLABLE', 'TEDE']::TEXT[]),
    ('TEDE_NL_SILABAS_INDIRECTAS_SIMPLE_049', 'nivel_lector', 'silabas_indirectas_simple', 49, 'is', 'is', ARRAY['SYLLABLE', 'TEDE']::TEXT[]),
    ('TEDE_NL_SILABAS_INDIRECTAS_SIMPLE_050', 'nivel_lector', 'silabas_indirectas_simple', 50, 'ac', 'ac', ARRAY['SYLLABLE', 'TEDE']::TEXT[]),
    ('TEDE_NL_SILABAS_INDIRECTAS_SIMPLE_051', 'nivel_lector', 'silabas_indirectas_simple', 51, 'in', 'in', ARRAY['SYLLABLE', 'TEDE']::TEXT[]),
    ('TEDE_NL_SILABAS_INDIRECTAS_SIMPLE_052', 'nivel_lector', 'silabas_indirectas_simple', 52, 'em', 'em', ARRAY['SYLLABLE', 'TEDE']::TEXT[]),
    ('TEDE_NL_SILABAS_INDIRECTAS_SIMPLE_053', 'nivel_lector', 'silabas_indirectas_simple', 53, 'ul', 'ul', ARRAY['SYLLABLE', 'TEDE']::TEXT[]),
    ('TEDE_NL_SILABAS_INDIRECTAS_SIMPLE_054', 'nivel_lector', 'silabas_indirectas_simple', 54, 'ar', 'ar', ARRAY['SYLLABLE', 'TEDE']::TEXT[]),
    ('TEDE_NL_SILABAS_INDIRECTAS_COMPLEJO_055', 'nivel_lector', 'silabas_indirectas_complejo', 55, 'ob', 'ob', ARRAY['ROT', 'SYLLABLE', 'TEDE']::TEXT[]),
    ('TEDE_NL_SILABAS_INDIRECTAS_COMPLEJO_056', 'nivel_lector', 'silabas_indirectas_complejo', 56, 'et', 'et', ARRAY['SYLLABLE', 'TEDE']::TEXT[]),
    ('TEDE_NL_SILABAS_INDIRECTAS_COMPLEJO_057', 'nivel_lector', 'silabas_indirectas_complejo', 57, 'ap', 'ap', ARRAY['ROT', 'SYLLABLE', 'TEDE']::TEXT[]),
    ('TEDE_NL_SILABAS_INDIRECTAS_COMPLEJO_058', 'nivel_lector', 'silabas_indirectas_complejo', 58, 'ex', 'ex', ARRAY['SYLLABLE', 'TEDE']::TEXT[]),
    ('TEDE_NL_SILABAS_INDIRECTAS_COMPLEJO_059', 'nivel_lector', 'silabas_indirectas_complejo', 59, 'af', 'af', ARRAY['SYLLABLE', 'TEDE']::TEXT[]),
    ('TEDE_NL_SILABAS_INDIRECTAS_COMPLEJO_060', 'nivel_lector', 'silabas_indirectas_complejo', 60, 'ad', 'ad', ARRAY['ROT', 'SYLLABLE', 'TEDE']::TEXT[]),
    ('TEDE_NL_SILABAS_COMPLEJAS_061', 'nivel_lector', 'silabas_complejas', 61, 'til', 'til', ARRAY['SYLLABLE', 'TEDE']::TEXT[]),
    ('TEDE_NL_SILABAS_COMPLEJAS_062', 'nivel_lector', 'silabas_complejas', 62, 'pur', 'pur', ARRAY['ROT', 'SYLLABLE', 'TEDE']::TEXT[]),
    ('TEDE_NL_SILABAS_COMPLEJAS_063', 'nivel_lector', 'silabas_complejas', 63, 'mos', 'mos', ARRAY['SYLLABLE', 'TEDE']::TEXT[]),
    ('TEDE_NL_SILABAS_COMPLEJAS_064', 'nivel_lector', 'silabas_complejas', 64, 'cam', 'cam', ARRAY['SYLLABLE', 'TEDE']::TEXT[]),
    ('TEDE_NL_SILABAS_COMPLEJAS_065', 'nivel_lector', 'silabas_complejas', 65, 'sec', 'sec', ARRAY['SYLLABLE', 'TEDE']::TEXT[]),
    ('TEDE_NL_SILABAS_COMPLEJAS_066', 'nivel_lector', 'silabas_complejas', 66, 'lin', 'lin', ARRAY['SYLLABLE', 'TEDE']::TEXT[]),
    ('TEDE_NL_DIPTONGO_SIMPLE_067', 'nivel_lector', 'diptongo_simple', 67, 'mia', 'mia', ARRAY['TEDE']::TEXT[]),
    ('TEDE_NL_DIPTONGO_SIMPLE_068', 'nivel_lector', 'diptongo_simple', 68, 'tue', 'tue', ARRAY['TEDE']::TEXT[]),
    ('TEDE_NL_DIPTONGO_SIMPLE_069', 'nivel_lector', 'diptongo_simple', 69, 'feu', 'feu', ARRAY['TEDE']::TEXT[]),
    ('TEDE_NL_DIPTONGO_SIMPLE_070', 'nivel_lector', 'diptongo_simple', 70, 'rou', 'rou', ARRAY['TEDE']::TEXT[]),
    ('TEDE_NL_DIPTONGO_SIMPLE_071', 'nivel_lector', 'diptongo_simple', 71, 'nio', 'nio', ARRAY['TEDE']::TEXT[]),
    ('TEDE_NL_DIPTONGO_SIMPLE_072', 'nivel_lector', 'diptongo_simple', 72, 'pia', 'pia', ARRAY['ROT', 'TEDE']::TEXT[]),
    ('TEDE_NL_DIPTONGO_COMPLEJO_073', 'nivel_lector', 'diptongo_complejo', 73, 'lian', 'lian', ARRAY['TEDE']::TEXT[]),
    ('TEDE_NL_DIPTONGO_COMPLEJO_074', 'nivel_lector', 'diptongo_complejo', 74, 'reis', 'reis', ARRAY['TEDE']::TEXT[]),
    ('TEDE_NL_DIPTONGO_COMPLEJO_075', 'nivel_lector', 'diptongo_complejo', 75, 'viul', 'viul', ARRAY['TEDE']::TEXT[]),
    ('TEDE_NL_DIPTONGO_COMPLEJO_076', 'nivel_lector', 'diptongo_complejo', 76, 'siap', 'siap', ARRAY['ROT', 'TEDE']::TEXT[]),
    ('TEDE_NL_DIPTONGO_COMPLEJO_077', 'nivel_lector', 'diptongo_complejo', 77, 'boim', 'boim', ARRAY['ROT', 'TEDE']::TEXT[]),
    ('TEDE_NL_DIPTONGO_COMPLEJO_078', 'nivel_lector', 'diptongo_complejo', 78, 'siec', 'siec', ARRAY['TEDE']::TEXT[]),
    ('TEDE_NL_FONOGRAMAS_SIMPLE_079', 'nivel_lector', 'fonogramas_simple', 79, 'bra', 'bra', ARRAY['ROT', 'TEDE']::TEXT[]),
    ('TEDE_NL_FONOGRAMAS_SIMPLE_080', 'nivel_lector', 'fonogramas_simple', 80, 'fli', 'fli', ARRAY['TEDE']::TEXT[]),
    ('TEDE_NL_FONOGRAMAS_SIMPLE_081', 'nivel_lector', 'fonogramas_simple', 81, 'gro', 'gro', ARRAY['TEDE']::TEXT[]),
    ('TEDE_NL_FONOGRAMAS_SIMPLE_082', 'nivel_lector', 'fonogramas_simple', 82, 'dru', 'dru', ARRAY['ROT', 'TEDE']::TEXT[]),
    ('TEDE_NL_FONOGRAMAS_SIMPLE_083', 'nivel_lector', 'fonogramas_simple', 83, 'cle', 'cle', ARRAY['TEDE']::TEXT[]),
    ('TEDE_NL_FONOGRAMAS_SIMPLE_084', 'nivel_lector', 'fonogramas_simple', 84, 'tri', 'tri', ARRAY['TEDE']::TEXT[]),
    ('TEDE_NL_FONOGRAMAS_COMPLEJO_085', 'nivel_lector', 'fonogramas_complejo', 85, 'glus', 'glus', ARRAY['TEDE']::TEXT[]),
    ('TEDE_NL_FONOGRAMAS_COMPLEJO_086', 'nivel_lector', 'fonogramas_complejo', 86, 'pron', 'pron', ARRAY['ROT', 'TEDE']::TEXT[]),
    ('TEDE_NL_FONOGRAMAS_COMPLEJO_087', 'nivel_lector', 'fonogramas_complejo', 87, 'tris', 'tris', ARRAY['TEDE']::TEXT[]),
    ('TEDE_NL_FONOGRAMAS_COMPLEJO_088', 'nivel_lector', 'fonogramas_complejo', 88, 'plaf', 'plaf', ARRAY['ROT', 'TEDE']::TEXT[]),
    ('TEDE_NL_FONOGRAMAS_COMPLEJO_089', 'nivel_lector', 'fonogramas_complejo', 89, 'blen', 'blen', ARRAY['ROT', 'TEDE']::TEXT[]),
    ('TEDE_NL_FONOGRAMAS_COMPLEJO_090', 'nivel_lector', 'fonogramas_complejo', 90, 'frat', 'frat', ARRAY['TEDE']::TEXT[]),
    ('TEDE_NL_FONOGRAMAS_DIPTONGO_SIMPLE_091', 'nivel_lector', 'fonogramas_diptongo_simple', 91, 'brio', 'brio', ARRAY['ROT', 'TEDE']::TEXT[]),
    ('TEDE_NL_FONOGRAMAS_DIPTONGO_SIMPLE_092', 'nivel_lector', 'fonogramas_diptongo_simple', 92, 'crue', 'crue', ARRAY['TEDE']::TEXT[]),
    ('TEDE_NL_FONOGRAMAS_DIPTONGO_SIMPLE_093', 'nivel_lector', 'fonogramas_diptongo_simple', 93, 'trau', 'trau', ARRAY['TEDE']::TEXT[]),
    ('TEDE_NL_FONOGRAMAS_DIPTONGO_SIMPLE_094', 'nivel_lector', 'fonogramas_diptongo_simple', 94, 'glio', 'glio', ARRAY['TEDE']::TEXT[]),
    ('TEDE_NL_FONOGRAMAS_DIPTONGO_SIMPLE_095', 'nivel_lector', 'fonogramas_diptongo_simple', 95, 'pleu', 'pleu', ARRAY['ROT', 'TEDE']::TEXT[]),
    ('TEDE_NL_FONOGRAMAS_DIPTONGO_SIMPLE_096', 'nivel_lector', 'fonogramas_diptongo_simple', 96, 'drie', 'drie', ARRAY['ROT', 'TEDE']::TEXT[]),
    ('TEDE_NL_FONOGRAMAS_DIPTONGO_COMPLEJO_097', 'nivel_lector', 'fonogramas_diptongo_complejo', 97, 'crian', 'crian', ARRAY['TEDE']::TEXT[]),
    ('TEDE_NL_FONOGRAMAS_DIPTONGO_COMPLEJO_098', 'nivel_lector', 'fonogramas_diptongo_complejo', 98, 'flaun', 'flaun', ARRAY['TEDE']::TEXT[]),
    ('TEDE_NL_FONOGRAMAS_DIPTONGO_COMPLEJO_099', 'nivel_lector', 'fonogramas_diptongo_complejo', 99, 'prien', 'prien', ARRAY['ROT', 'TEDE']::TEXT[]),
    ('TEDE_NL_FONOGRAMAS_DIPTONGO_COMPLEJO_100', 'nivel_lector', 'fonogramas_diptongo_complejo', 100, 'clous', 'clous', ARRAY['TEDE']::TEXT[]),
    ('TEDE_NL_FONOGRAMAS_DIPTONGO_COMPLEJO_101', 'nivel_lector', 'fonogramas_diptongo_complejo', 101, 'triun', 'triun', ARRAY['TEDE']::TEXT[]),
    ('TEDE_NL_FONOGRAMAS_DIPTONGO_COMPLEJO_102', 'nivel_lector', 'fonogramas_diptongo_complejo', 102, 'blauc', 'blauc', ARRAY['ROT', 'TEDE']::TEXT[]),
    ('TEDE_EE_CONFUNDIBLES_SONIDO_OPCIONES_103', 'errores_especificos', 'confundibles_sonido_opciones', 103, 'y', 'y', ARRAY['SUS', 'TEDE']::TEXT[]),
    ('TEDE_EE_CONFUNDIBLES_SONIDO_OPCIONES_104', 'errores_especificos', 'confundibles_sonido_opciones', 104, 'j', 'j', ARRAY['SUS', 'TEDE']::TEXT[]),
    ('TEDE_EE_CONFUNDIBLES_SONIDO_OPCIONES_105', 'errores_especificos', 'confundibles_sonido_opciones', 105, 's', 's', ARRAY['SUS', 'TEDE']::TEXT[]),
    ('TEDE_EE_CONFUNDIBLES_SONIDO_OPCIONES_106', 'errores_especificos', 'confundibles_sonido_opciones', 106, 'll', 'll', ARRAY['SUS', 'TEDE']::TEXT[]),
    ('TEDE_EE_CONFUNDIBLES_SONIDO_OPCIONES_107', 'errores_especificos', 'confundibles_sonido_opciones', 107, 'ch', 'ch', ARRAY['SUS', 'TEDE']::TEXT[]),
    ('TEDE_EE_CONFUNDIBLES_SONIDO_OPCIONES_108', 'errores_especificos', 'confundibles_sonido_opciones', 108, 'f', 'f', ARRAY['SUS', 'TEDE']::TEXT[]),
    ('TEDE_EE_CONFUNDIBLES_SONIDO_OPCIONES_109', 'errores_especificos', 'confundibles_sonido_opciones', 109, 'd', 'd', ARRAY['ROT', 'SUS', 'TEDE']::TEXT[]),
    ('TEDE_EE_CONFUNDIBLES_SONIDO_OPCIONES_110', 'errores_especificos', 'confundibles_sonido_opciones', 110, 't', 't', ARRAY['SUS', 'TEDE']::TEXT[]),
    ('TEDE_EE_CONFUNDIBLES_SONIDO_OPCIONES_111', 'errores_especificos', 'confundibles_sonido_opciones', 111, 'l', 'l', ARRAY['SUS', 'TEDE']::TEXT[]),
    ('TEDE_EE_CONFUNDIBLES_SONIDO_OPCIONES_112', 'errores_especificos', 'confundibles_sonido_opciones', 112, 'n', 'n', ARRAY['SUS', 'TEDE']::TEXT[]),
    ('TEDE_EE_CONFUNDIBLES_SONIDO_OPCIONES_113', 'errores_especificos', 'confundibles_sonido_opciones', 113, 'f', 'f', ARRAY['SUS', 'TEDE']::TEXT[]),
    ('TEDE_EE_CONFUNDIBLES_SONIDO_OPCIONES_114', 'errores_especificos', 'confundibles_sonido_opciones', 114, 'j', 'j', ARRAY['SUS', 'TEDE']::TEXT[]),
    ('TEDE_EE_CONFUNDIBLES_SONIDO_OPCIONES_115', 'errores_especificos', 'confundibles_sonido_opciones', 115, 'v', 'v', ARRAY['SUS', 'TEDE']::TEXT[]),
    ('TEDE_EE_CONFUNDIBLES_SONIDO_OPCIONES_116', 'errores_especificos', 'confundibles_sonido_opciones', 116, 'b', 'b', ARRAY['ROT', 'SUS', 'TEDE']::TEXT[]),
    ('TEDE_EE_CONFUNDIBLES_SONIDO_OPCIONES_117', 'errores_especificos', 'confundibles_sonido_opciones', 117, 's', 's', ARRAY['SUS', 'TEDE']::TEXT[]),
    ('TEDE_EE_CONFUNDIBLES_SONIDO_OPCIONES_118', 'errores_especificos', 'confundibles_sonido_opciones', 118, 'll', 'll', ARRAY['SUS', 'TEDE']::TEXT[]),
    ('TEDE_EE_CONFUNDIBLES_SONIDO_OPCIONES_119', 'errores_especificos', 'confundibles_sonido_opciones', 119, 'ch', 'ch', ARRAY['SUS', 'TEDE']::TEXT[]),
    ('TEDE_EE_CONFUNDIBLES_SONIDO_OPCIONES_120', 'errores_especificos', 'confundibles_sonido_opciones', 120, 'ñ', 'ñ', ARRAY['SUS', 'TEDE']::TEXT[]),
    ('TEDE_EE_CONFUNDIBLES_SONIDO_OPCIONES_121', 'errores_especificos', 'confundibles_sonido_opciones', 121, 'j', 'j', ARRAY['SUS', 'TEDE']::TEXT[]),
    ('TEDE_EE_CONFUNDIBLES_SONIDO_OPCIONES_122', 'errores_especificos', 'confundibles_sonido_opciones', 122, 'g', 'g', ARRAY['SUS', 'TEDE']::TEXT[]),
    ('TEDE_EE_CONFUNDIBLES_SONIDO_OPCIONES_123', 'errores_especificos', 'confundibles_sonido_opciones', 123, 'c', 'c', ARRAY['SUS', 'TEDE']::TEXT[]),
    ('TEDE_EE_CONFUNDIBLES_SONIDO_OPCIONES_124', 'errores_especificos', 'confundibles_sonido_opciones', 124, 'k', 'k', ARRAY['SUS', 'TEDE']::TEXT[]),
    ('TEDE_EE_CONFUNDIBLES_SONIDO_OPCIONES_125', 'errores_especificos', 'confundibles_sonido_opciones', 125, 't', 't', ARRAY['SUS', 'TEDE']::TEXT[]),
    ('TEDE_EE_CONFUNDIBLES_SONIDO_OPCIONES_126', 'errores_especificos', 'confundibles_sonido_opciones', 126, 'm', 'm', ARRAY['ROT', 'SUS', 'TEDE']::TEXT[]),
    ('TEDE_EE_CONFUNDIBLES_SONIDO_OPCIONES_127', 'errores_especificos', 'confundibles_sonido_opciones', 127, 'd', 'd', ARRAY['ROT', 'SUS', 'TEDE']::TEXT[]),
    ('TEDE_EE_CONFUNDIBLES_SONIDO_OPCIONES_128', 'errores_especificos', 'confundibles_sonido_opciones', 128, 'y', 'y', ARRAY['SUS', 'TEDE']::TEXT[]),
    ('TEDE_EE_CONFUNDIBLES_SONIDO_OPCIONES_129', 'errores_especificos', 'confundibles_sonido_opciones', 129, 'r', 'r', ARRAY['SUS', 'TEDE']::TEXT[]),
    ('TEDE_EE_CONFUNDIBLES_SONIDO_OPCIONES_130', 'errores_especificos', 'confundibles_sonido_opciones', 130, 'j', 'j', ARRAY['SUS', 'TEDE']::TEXT[]),
    ('TEDE_EE_CONFUNDIBLES_SONIDO_OPCIONES_131', 'errores_especificos', 'confundibles_sonido_opciones', 131, 'm', 'm', ARRAY['ROT', 'SUS', 'TEDE']::TEXT[]),
    ('TEDE_EE_CONFUNDIBLES_SONIDO_OPCIONES_132', 'errores_especificos', 'confundibles_sonido_opciones', 132, 'g', 'g', ARRAY['SUS', 'TEDE']::TEXT[]),
    ('TEDE_EE_CONFUNDIBLES_SONIDO_OPCIONES_133', 'errores_especificos', 'confundibles_sonido_opciones', 133, 'b', 'b', ARRAY['ROT', 'SUS', 'TEDE']::TEXT[]),
    ('TEDE_EE_CONFUNDIBLES_SONIDO_OPCIONES_134', 'errores_especificos', 'confundibles_sonido_opciones', 134, 'ñ', 'ñ', ARRAY['SUS', 'TEDE']::TEXT[]),
    ('TEDE_EE_CONFUNDIBLES_SONIDO_OPCIONES_135', 'errores_especificos', 'confundibles_sonido_opciones', 135, 't', 't', ARRAY['SUS', 'TEDE']::TEXT[]),
    ('TEDE_EE_CONFUNDIBLES_SONIDO_OPCIONES_136', 'errores_especificos', 'confundibles_sonido_opciones', 136, 'f', 'f', ARRAY['SUS', 'TEDE']::TEXT[]),
    ('TEDE_EE_CONFUNDIBLES_SONIDO_OPCIONES_137', 'errores_especificos', 'confundibles_sonido_opciones', 137, 'p', 'p', ARRAY['ROT', 'SUS', 'TEDE']::TEXT[]),
    ('TEDE_EE_CONFUNDIBLES_SONIDO_OPCIONES_138', 'errores_especificos', 'confundibles_sonido_opciones', 138, 'g', 'g', ARRAY['SUS', 'TEDE']::TEXT[]),
    ('TEDE_EE_CONFUNDIBLES_SONIDO_OPCIONES_139', 'errores_especificos', 'confundibles_sonido_opciones', 139, 'y', 'y', ARRAY['SUS', 'TEDE']::TEXT[]),
    ('TEDE_EE_CONFUNDIBLES_SONIDO_OPCIONES_140', 'errores_especificos', 'confundibles_sonido_opciones', 140, 'll', 'll', ARRAY['SUS', 'TEDE']::TEXT[]),
    ('TEDE_EE_CONFUNDIBLES_SONIDO_OPCIONES_141', 'errores_especificos', 'confundibles_sonido_opciones', 141, 'j', 'j', ARRAY['SUS', 'TEDE']::TEXT[]),
    ('TEDE_EE_CONFUNDIBLES_SONIDO_OPCIONES_142', 'errores_especificos', 'confundibles_sonido_opciones', 142, 'f', 'f', ARRAY['SUS', 'TEDE']::TEXT[]),
    ('TEDE_EE_CONFUNDIBLES_SONIDO_OPCIONES_143', 'errores_especificos', 'confundibles_sonido_opciones', 143, 's', 's', ARRAY['SUS', 'TEDE']::TEXT[]),
    ('TEDE_EE_CONFUNDIBLES_SONIDO_OPCIONES_144', 'errores_especificos', 'confundibles_sonido_opciones', 144, 't', 't', ARRAY['SUS', 'TEDE']::TEXT[]),
    ('TEDE_EE_CONFUNDIBLES_SONIDO_OPCIONES_145', 'errores_especificos', 'confundibles_sonido_opciones', 145, 'b', 'b', ARRAY['ROT', 'SUS', 'TEDE']::TEXT[]),
    ('TEDE_EE_CONFUNDIBLES_SONIDO_OPCIONES_146', 'errores_especificos', 'confundibles_sonido_opciones', 146, 'm', 'm', ARRAY['ROT', 'SUS', 'TEDE']::TEXT[]),
    ('TEDE_EE_CONFUNDIBLES_SONIDO_OPCIONES_147', 'errores_especificos', 'confundibles_sonido_opciones', 147, 'p', 'p', ARRAY['ROT', 'SUS', 'TEDE']::TEXT[]),
    ('TEDE_EE_CONFUNDIBLES_SONIDO_OPCIONES_148', 'errores_especificos', 'confundibles_sonido_opciones', 148, 'g', 'g', ARRAY['SUS', 'TEDE']::TEXT[]),
    ('TEDE_EE_CONFUNDIBLES_SONIDO_OPCIONES_149', 'errores_especificos', 'confundibles_sonido_opciones', 149, 's', 's', ARRAY['SUS', 'TEDE']::TEXT[]),
    ('TEDE_EE_CONFUNDIBLES_SONIDO_OPCIONES_150', 'errores_especificos', 'confundibles_sonido_opciones', 150, 'j', 'j', ARRAY['SUS', 'TEDE']::TEXT[]),
    ('TEDE_EE_CONFUNDIBLES_SONIDO_OPCIONES_151', 'errores_especificos', 'confundibles_sonido_opciones', 151, 'q', 'q', ARRAY['ROT', 'SUS', 'TEDE']::TEXT[]),
    ('TEDE_EE_CONFUNDIBLES_SONIDO_OPCIONES_152', 'errores_especificos', 'confundibles_sonido_opciones', 152, 'c', 'c', ARRAY['SUS', 'TEDE']::TEXT[]),
    ('TEDE_EE_CONFUNDIBLES_SONIDO_OPCIONES_153', 'errores_especificos', 'confundibles_sonido_opciones', 153, 's', 's', ARRAY['SUS', 'TEDE']::TEXT[]),
    ('TEDE_EE_CONFUNDIBLES_SONIDO_OPCIONES_154', 'errores_especificos', 'confundibles_sonido_opciones', 154, 'm', 'm', ARRAY['ROT', 'SUS', 'TEDE']::TEXT[]),
    ('TEDE_EE_CONFUNDIBLES_SONIDO_OPCIONES_155', 'errores_especificos', 'confundibles_sonido_opciones', 155, 'n', 'n', ARRAY['SUS', 'TEDE']::TEXT[]),
    ('TEDE_EE_CONFUNDIBLES_SONIDO_OPCIONES_156', 'errores_especificos', 'confundibles_sonido_opciones', 156, 'l', 'l', ARRAY['SUS', 'TEDE']::TEXT[]),
    ('TEDE_EE_CONFUNDIBLES_SONIDO_OPCIONES_157', 'errores_especificos', 'confundibles_sonido_opciones', 157, 'b', 'b', ARRAY['ROT', 'SUS', 'TEDE']::TEXT[]),
    ('TEDE_EE_CONFUNDIBLES_SONIDO_OPCIONES_158', 'errores_especificos', 'confundibles_sonido_opciones', 158, 'll', 'll', ARRAY['SUS', 'TEDE']::TEXT[]),
    ('TEDE_EE_CONFUNDIBLES_SONIDO_OPCIONES_159', 'errores_especificos', 'confundibles_sonido_opciones', 159, 'j', 'j', ARRAY['SUS', 'TEDE']::TEXT[]),
    ('TEDE_EE_CONFUNDIBLES_SONIDO_OPCIONES_160', 'errores_especificos', 'confundibles_sonido_opciones', 160, 'ñ', 'ñ', ARRAY['SUS', 'TEDE']::TEXT[]),
    ('TEDE_EE_CONFUNDIBLES_SONIDO_OPCIONES_161', 'errores_especificos', 'confundibles_sonido_opciones', 161, 'm', 'm', ARRAY['ROT', 'SUS', 'TEDE']::TEXT[]),
    ('TEDE_EE_CONFUNDIBLES_SONIDO_OPCIONES_162', 'errores_especificos', 'confundibles_sonido_opciones', 162, 'ch', 'ch', ARRAY['SUS', 'TEDE']::TEXT[]),
    ('TEDE_EE_CONFUNDIBLES_SONIDO_PALABRAS_163', 'errores_especificos', 'confundibles_sonido_palabras', 163, 'chado', 'chado', ARRAY['ROT', 'SUS', 'TEDE']::TEXT[]),
    ('TEDE_EE_CONFUNDIBLES_SONIDO_PALABRAS_164', 'errores_especificos', 'confundibles_sonido_palabras', 164, 'deco', 'deco', ARRAY['ROT', 'SUS', 'TEDE']::TEXT[]),
    ('TEDE_EE_CONFUNDIBLES_SONIDO_PALABRAS_165', 'errores_especificos', 'confundibles_sonido_palabras', 165, 'fido', 'fido', ARRAY['ROT', 'SUS', 'TEDE']::TEXT[]),
    ('TEDE_EE_CONFUNDIBLES_SONIDO_PALABRAS_166', 'errores_especificos', 'confundibles_sonido_palabras', 166, 'llotio', 'llotio', ARRAY['SUS', 'TEDE']::TEXT[]),
    ('TEDE_EE_CONFUNDIBLES_SONIDO_PALABRAS_167', 'errores_especificos', 'confundibles_sonido_palabras', 167, 'tarpo', 'tarpo', ARRAY['ROT', 'SUS', 'TEDE']::TEXT[]),
    ('TEDE_EE_CONFUNDIBLES_SONIDO_PALABRAS_168', 'errores_especificos', 'confundibles_sonido_palabras', 168, 'gupa', 'gupa', ARRAY['ROT', 'SUS', 'TEDE']::TEXT[]),
    ('TEDE_EE_CONFUNDIBLES_SONIDO_PALABRAS_169', 'errores_especificos', 'confundibles_sonido_palabras', 169, 'boso', 'boso', ARRAY['ROT', 'SUS', 'TEDE']::TEXT[]),
    ('TEDE_EE_CONFUNDIBLES_SONIDO_PALABRAS_170', 'errores_especificos', 'confundibles_sonido_palabras', 170, 'jallón', 'jallón', ARRAY['SUS', 'TEDE']::TEXT[]),
    ('TEDE_EE_CONFUNDIBLES_SONIDO_PALABRAS_171', 'errores_especificos', 'confundibles_sonido_palabras', 171, 'pola', 'pola', ARRAY['ROT', 'SUS', 'TEDE']::TEXT[]),
    ('TEDE_EE_CONFUNDIBLES_SONIDO_PALABRAS_172', 'errores_especificos', 'confundibles_sonido_palabras', 172, 'querpo', 'querpo', ARRAY['ROT', 'SUS', 'TEDE']::TEXT[]),
    ('TEDE_EE_CONFUNDIBLES_SONIDO_PALABRAS_173', 'errores_especificos', 'confundibles_sonido_palabras', 173, 'mite', 'mite', ARRAY['SUS', 'TEDE']::TEXT[]),
    ('TEDE_EE_CONFUNDIBLES_SONIDO_PALABRAS_174', 'errores_especificos', 'confundibles_sonido_palabras', 174, 'ñuma', 'ñuma', ARRAY['SUS', 'TEDE']::TEXT[]),
    ('TEDE_EE_GRAFIA_SEMEJANTE_PSEUDOPALABRAS_175', 'errores_especificos', 'grafia_semejante_pseudopalabras', 175, 'nomino', 'nomino', ARRAY['PSEUDO', 'SUS', 'TEDE']::TEXT[]),
    ('TEDE_EE_GRAFIA_SEMEJANTE_PSEUDOPALABRAS_176', 'errores_especificos', 'grafia_semejante_pseudopalabras', 176, 'ohnado', 'ohnado', ARRAY['PSEUDO', 'ROT', 'SUS', 'TEDE']::TEXT[]),
    ('TEDE_EE_GRAFIA_SEMEJANTE_PSEUDOPALABRAS_177', 'errores_especificos', 'grafia_semejante_pseudopalabras', 177, 'deste', 'deste', ARRAY['PSEUDO', 'ROT', 'SUS', 'TEDE']::TEXT[]),
    ('TEDE_EE_GRAFIA_SEMEJANTE_PSEUDOPALABRAS_178', 'errores_especificos', 'grafia_semejante_pseudopalabras', 178, 'alledo', 'alledo', ARRAY['PSEUDO', 'ROT', 'SUS', 'TEDE']::TEXT[]),
    ('TEDE_EE_GRAFIA_SEMEJANTE_PSEUDOPALABRAS_179', 'errores_especificos', 'grafia_semejante_pseudopalabras', 179, 'rechido', 'rechido', ARRAY['PSEUDO', 'ROT', 'SUS', 'TEDE']::TEXT[]),
    ('TEDE_EE_GRAFIA_SEMEJANTE_PSEUDOPALABRAS_180', 'errores_especificos', 'grafia_semejante_pseudopalabras', 180, 'chaquillo', 'chaquillo', ARRAY['PSEUDO', 'ROT', 'SUS', 'TEDE']::TEXT[]),
    ('TEDE_EE_GRAFIA_SEMEJANTE_PSEUDOPALABRAS_181', 'errores_especificos', 'grafia_semejante_pseudopalabras', 181, 'laqueta', 'laqueta', ARRAY['PSEUDO', 'ROT', 'SUS', 'TEDE']::TEXT[]),
    ('TEDE_EE_GRAFIA_SEMEJANTE_PSEUDOPALABRAS_182', 'errores_especificos', 'grafia_semejante_pseudopalabras', 182, 'sagueso', 'sagueso', ARRAY['PSEUDO', 'SUS', 'TEDE']::TEXT[]),
    ('TEDE_EE_GRAFIA_SEMEJANTE_PSEUDOPALABRAS_183', 'errores_especificos', 'grafia_semejante_pseudopalabras', 183, 'quiguifi', 'quiguifi', ARRAY['PSEUDO', 'ROT', 'SUS', 'TEDE']::TEXT[]),
    ('TEDE_EE_GRAFIA_SEMEJANTE_PSEUDOPALABRAS_184', 'errores_especificos', 'grafia_semejante_pseudopalabras', 184, 'ifjuti', 'ifjuti', ARRAY['PSEUDO', 'SUS', 'TEDE']::TEXT[]),
    ('TEDE_EE_GRAFIA_SEMEJANTE_PSEUDOPALABRAS_185', 'errores_especificos', 'grafia_semejante_pseudopalabras', 185, 'voyate', 'voyate', ARRAY['PSEUDO', 'SUS', 'TEDE']::TEXT[]),
    ('TEDE_EE_GRAFIA_SEMEJANTE_PSEUDOPALABRAS_186', 'errores_especificos', 'grafia_semejante_pseudopalabras', 186, 'quellimi', 'quellimi', ARRAY['PSEUDO', 'ROT', 'SUS', 'TEDE']::TEXT[]),
    ('TEDE_EE_INVERSIONES_LETRAS_187', 'errores_especificos', 'inversiones_letras', 187, 'bado', 'bado', ARRAY['INV', 'PSEUDO', 'ROT', 'TEDE']::TEXT[]),
    ('TEDE_EE_INVERSIONES_LETRAS_188', 'errores_especificos', 'inversiones_letras', 188, 'dipo', 'dipo', ARRAY['INV', 'PSEUDO', 'ROT', 'TEDE']::TEXT[]),
    ('TEDE_EE_INVERSIONES_LETRAS_189', 'errores_especificos', 'inversiones_letras', 189, 'babe', 'babe', ARRAY['INV', 'ROT', 'TEDE']::TEXT[]),
    ('TEDE_EE_INVERSIONES_LETRAS_190', 'errores_especificos', 'inversiones_letras', 190, 'quebo', 'quebo', ARRAY['INV', 'ROT', 'TEDE']::TEXT[]),
    ('TEDE_EE_INVERSIONES_LETRAS_191', 'errores_especificos', 'inversiones_letras', 191, 'quido', 'quido', ARRAY['INV', 'ROT', 'TEDE']::TEXT[]),
    ('TEDE_EE_INVERSIONES_LETRAS_192', 'errores_especificos', 'inversiones_letras', 192, 'dudo', 'dudo', ARRAY['INV', 'ROT', 'TEDE']::TEXT[]),
    ('TEDE_EE_INVERSIONES_LETRAS_193', 'errores_especificos', 'inversiones_letras', 193, 'bapi', 'bapi', ARRAY['INV', 'ROT', 'TEDE']::TEXT[]),
    ('TEDE_EE_INVERSIONES_LETRAS_194', 'errores_especificos', 'inversiones_letras', 194, 'quipi', 'quipi', ARRAY['INV', 'ROT', 'TEDE']::TEXT[]),
    ('TEDE_EE_INVERSIONES_LETRAS_195', 'errores_especificos', 'inversiones_letras', 195, 'dubopi', 'dubopi', ARRAY['INV', 'ROT', 'TEDE']::TEXT[]),
    ('TEDE_EE_INVERSIONES_LETRAS_196', 'errores_especificos', 'inversiones_letras', 196, 'pebade', 'pebade', ARRAY['INV', 'ROT', 'TEDE']::TEXT[]),
    ('TEDE_EE_INVERSIONES_LETRAS_197', 'errores_especificos', 'inversiones_letras', 197, 'numo', 'numo', ARRAY['INV', 'TEDE']::TEXT[]),
    ('TEDE_EE_INVERSIONES_LETRAS_198', 'errores_especificos', 'inversiones_letras', 198, 'saute', 'saute', ARRAY['INV', 'TEDE']::TEXT[]),
    ('TEDE_EE_INVERSIONES_PALABRAS_COMPLETAS_199', 'errores_especificos', 'inversiones_palabras_completas', 199, 'la', 'la', ARRAY['INV', 'TEDE']::TEXT[]),
    ('TEDE_EE_INVERSIONES_PALABRAS_COMPLETAS_200', 'errores_especificos', 'inversiones_palabras_completas', 200, 'sol', 'sol', ARRAY['INV', 'TEDE']::TEXT[]),
    ('TEDE_EE_INVERSIONES_PALABRAS_COMPLETAS_201', 'errores_especificos', 'inversiones_palabras_completas', 201, 'se', 'se', ARRAY['INV', 'TEDE']::TEXT[]),
    ('TEDE_EE_INVERSIONES_PALABRAS_COMPLETAS_202', 'errores_especificos', 'inversiones_palabras_completas', 202, 'las', 'las', ARRAY['INV', 'TEDE']::TEXT[]),
    ('TEDE_EE_INVERSIONES_PALABRAS_COMPLETAS_203', 'errores_especificos', 'inversiones_palabras_completas', 203, 'nos', 'nos', ARRAY['INV', 'TEDE']::TEXT[]),
    ('TEDE_EE_INVERSIONES_PALABRAS_COMPLETAS_204', 'errores_especificos', 'inversiones_palabras_completas', 204, 'los', 'los', ARRAY['INV', 'TEDE']::TEXT[]),
    ('TEDE_EE_INVERSIONES_PALABRAS_COMPLETAS_205', 'errores_especificos', 'inversiones_palabras_completas', 205, 'al', 'al', ARRAY['INV', 'TEDE']::TEXT[]),
    ('TEDE_EE_INVERSIONES_PALABRAS_COMPLETAS_206', 'errores_especificos', 'inversiones_palabras_completas', 206, 'es', 'es', ARRAY['INV', 'TEDE']::TEXT[]),
    ('TEDE_EE_INVERSIONES_PALABRAS_COMPLETAS_207', 'errores_especificos', 'inversiones_palabras_completas', 207, 'son', 'son', ARRAY['INV', 'TEDE']::TEXT[]),
    ('TEDE_EE_INVERSIONES_PALABRAS_COMPLETAS_208', 'errores_especificos', 'inversiones_palabras_completas', 208, 'le', 'le', ARRAY['INV', 'TEDE']::TEXT[]),
    ('TEDE_EE_INVERSIONES_PALABRAS_COMPLETAS_209', 'errores_especificos', 'inversiones_palabras_completas', 209, 'sal', 'sal', ARRAY['INV', 'TEDE']::TEXT[]),
    ('TEDE_EE_INVERSIONES_LETRAS_EN_PALABRA_210', 'errores_especificos', 'inversiones_letras_en_palabra', 210, 'palta', 'palta', ARRAY['INV', 'ROT', 'TEDE']::TEXT[]),
    ('TEDE_EE_INVERSIONES_LETRAS_EN_PALABRA_211', 'errores_especificos', 'inversiones_letras_en_palabra', 211, 'sobra', 'sobra', ARRAY['INV', 'ROT', 'TEDE']::TEXT[]),
    ('TEDE_EE_INVERSIONES_LETRAS_EN_PALABRA_212', 'errores_especificos', 'inversiones_letras_en_palabra', 212, 'trota', 'trota', ARRAY['INV', 'TEDE']::TEXT[]),
    ('TEDE_EE_INVERSIONES_LETRAS_EN_PALABRA_213', 'errores_especificos', 'inversiones_letras_en_palabra', 213, 'plumón', 'plumón', ARRAY['INV', 'ROT', 'TEDE']::TEXT[]),
    ('TEDE_EE_INVERSIONES_LETRAS_EN_PALABRA_214', 'errores_especificos', 'inversiones_letras_en_palabra', 214, 'turco', 'turco', ARRAY['INV', 'TEDE']::TEXT[]),
    ('TEDE_EE_INVERSIONES_LETRAS_EN_PALABRA_215', 'errores_especificos', 'inversiones_letras_en_palabra', 215, 'trono', 'trono', ARRAY['INV', 'TEDE']::TEXT[]),
    ('TEDE_EE_INVERSIONES_LETRAS_EN_PALABRA_216', 'errores_especificos', 'inversiones_letras_en_palabra', 216, 'balcón', 'balcón', ARRAY['INV', 'ROT', 'TEDE']::TEXT[]),
    ('TEDE_EE_INVERSIONES_LETRAS_EN_PALABRA_217', 'errores_especificos', 'inversiones_letras_en_palabra', 217, 'negar', 'negar', ARRAY['INV', 'TEDE']::TEXT[]),
    ('TEDE_EE_INVERSIONES_LETRAS_EN_PALABRA_218', 'errores_especificos', 'inversiones_letras_en_palabra', 218, 'sabré', 'sabré', ARRAY['INV', 'ROT', 'TEDE']::TEXT[]),
    ('TEDE_EE_INVERSIONES_LETRAS_EN_PALABRA_219', 'errores_especificos', 'inversiones_letras_en_palabra', 219, 'calvo', 'calvo', ARRAY['INV', 'TEDE']::TEXT[]),
    ('TEDE_EE_INVERSIONES_LETRAS_EN_PALABRA_220', 'errores_especificos', 'inversiones_letras_en_palabra', 220, 'nobel', 'nobel', ARRAY['INV', 'ROT', 'TEDE']::TEXT[]),
    ('TEDE_EE_INVERSIONES_LETRAS_EN_PALABRA_221', 'errores_especificos', 'inversiones_letras_en_palabra', 221, 'pardo', 'pardo', ARRAY['INV', 'ROT', 'TEDE']::TEXT[]),
    ('TEDE_EE_INVERSION_ORDEN_SILABA_222', 'errores_especificos', 'inversion_orden_silaba', 222, 'loma', 'loma', ARRAY['INV', 'SYLLABLE', 'TEDE']::TEXT[]),
    ('TEDE_EE_INVERSION_ORDEN_SILABA_223', 'errores_especificos', 'inversion_orden_silaba', 223, 'saco', 'saco', ARRAY['INV', 'SYLLABLE', 'TEDE']::TEXT[]),
    ('TEDE_EE_INVERSION_ORDEN_SILABA_224', 'errores_especificos', 'inversion_orden_silaba', 224, 'dato', 'dato', ARRAY['INV', 'ROT', 'SYLLABLE', 'TEDE']::TEXT[]),
    ('TEDE_EE_INVERSION_ORDEN_SILABA_225', 'errores_especificos', 'inversion_orden_silaba', 225, 'tapa', 'tapa', ARRAY['INV', 'ROT', 'SYLLABLE', 'TEDE']::TEXT[]),
    ('TEDE_EE_INVERSION_ORDEN_SILABA_226', 'errores_especificos', 'inversion_orden_silaba', 226, 'tala', 'tala', ARRAY['INV', 'SYLLABLE', 'TEDE']::TEXT[]),
    ('TEDE_EE_INVERSION_ORDEN_SILABA_227', 'errores_especificos', 'inversion_orden_silaba', 227, 'cabo', 'cabo', ARRAY['INV', 'ROT', 'SYLLABLE', 'TEDE']::TEXT[]),
    ('TEDE_EE_INVERSION_ORDEN_SILABA_228', 'errores_especificos', 'inversion_orden_silaba', 228, 'sopa', 'sopa', ARRAY['INV', 'ROT', 'SYLLABLE', 'TEDE']::TEXT[]),
    ('TEDE_EE_INVERSION_ORDEN_SILABA_229', 'errores_especificos', 'inversion_orden_silaba', 229, 'toga', 'toga', ARRAY['INV', 'SYLLABLE', 'TEDE']::TEXT[]),
    ('TEDE_EE_INVERSION_ORDEN_SILABA_230', 'errores_especificos', 'inversion_orden_silaba', 230, 'saca', 'saca', ARRAY['INV', 'SYLLABLE', 'TEDE']::TEXT[]),
    ('TEDE_EE_INVERSION_ORDEN_SILABA_231', 'errores_especificos', 'inversion_orden_silaba', 231, 'choca', 'choca', ARRAY['INV', 'SYLLABLE', 'TEDE']::TEXT[]),
    ('TEDE_EE_INVERSION_ORDEN_SILABA_232', 'errores_especificos', 'inversion_orden_silaba', 232, 'cala', 'cala', ARRAY['INV', 'SYLLABLE', 'TEDE']::TEXT[]),
    ('TEDE_EE_INVERSION_ORDEN_SILABA_233', 'errores_especificos', 'inversion_orden_silaba', 233, 'caro', 'caro', ARRAY['INV', 'SYLLABLE', 'TEDE']::TEXT[])
ON CONFLICT (item_code) DO UPDATE SET
    section = EXCLUDED.section,
    category = EXCLUDED.category,
    item_order = EXCLUDED.item_order,
    stimulus_text = EXCLUDED.stimulus_text,
    expected_response = EXCLUDED.expected_response,
    tags = EXCLUDED.tags;

INSERT INTO diagnosis.error_codes (code, error_type, example, profile_hint, counts_for_risk, description)
VALUES
    ('OMI', 'Omisión', 'perro -> pero', 'fonológico', TRUE, 'Código PLN usado para clasificar errores tipo Omisión.'),
    ('SUS', 'Sustitución', 'dado -> bado', 'visual o fonológico', TRUE, 'Código PLN usado para clasificar errores tipo Sustitución.'),
    ('INV', 'Inversión', 'plato -> palto', 'fonológico/mixto', TRUE, 'Código PLN usado para clasificar errores tipo Inversión.'),
    ('ROT', 'Rotación visual', 'b<->d, p<->q', 'visual/superficial', TRUE, 'Código PLN usado para clasificar errores tipo Rotación visual.'),
    ('LEX', 'Lexicalización', 'pseudopalabra leída como palabra real cercana', 'visual/compensación', TRUE, 'Código PLN usado para clasificar errores tipo Lexicalización.'),
    ('SEG', 'Segmentación', 'conmigo -> con migo', 'fonológico', TRUE, 'Código PLN usado para clasificar errores tipo Segmentación.'),
    ('UNI', 'Unión', 'la casa -> lacasa', 'fonológico', TRUE, 'Código PLN usado para clasificar errores tipo Unión.'),
    ('FON', 'Error fonológico', 'guitarra -> gitarra', 'fonológico', TRUE, 'Código PLN usado para clasificar errores tipo Error fonológico.'),
    ('ADD', 'Adición', 'cocina -> cocicina', 'mixto', TRUE, 'Código PLN usado para clasificar errores tipo Adición.'),
    ('LEN', 'Lentitud', 'respuesta correcta pero tardía', 'fluidez/automatización', TRUE, 'Código PLN usado para clasificar errores tipo Lentitud.'),
    ('COM', 'Comprensión', 'respuesta literal/inferencial incorrecta', 'comprensión', TRUE, 'Código PLN usado para clasificar errores tipo Comprensión.'),
    ('ACC', 'Acento', 'rápido -> rapido', 'ortográfico informativo; no suma al score', FALSE, 'Código PLN usado para clasificar errores tipo Acento.')
ON CONFLICT (code) DO UPDATE SET
    error_type = EXCLUDED.error_type,
    example = EXCLUDED.example,
    profile_hint = EXCLUDED.profile_hint,
    counts_for_risk = EXCLUDED.counts_for_risk,
    description = EXCLUDED.description;

INSERT INTO diagnosis.feature_definitions (feature_index, feature_name, feature_group, description, source_modules)
VALUES
    (0, 'OMI_rate', 'error_rates', 'Dimensión 0 del vector PLN/ML: OMI_rate.', ARRAY[]::TEXT[]),
    (1, 'SUS_rate', 'error_rates', 'Dimensión 1 del vector PLN/ML: SUS_rate.', ARRAY[]::TEXT[]),
    (2, 'INV_rate', 'error_rates', 'Dimensión 2 del vector PLN/ML: INV_rate.', ARRAY[]::TEXT[]),
    (3, 'ROT_rate', 'error_rates', 'Dimensión 3 del vector PLN/ML: ROT_rate.', ARRAY[]::TEXT[]),
    (4, 'LEX_rate', 'error_rates', 'Dimensión 4 del vector PLN/ML: LEX_rate.', ARRAY[]::TEXT[]),
    (5, 'SEG_rate', 'error_rates', 'Dimensión 5 del vector PLN/ML: SEG_rate.', ARRAY[]::TEXT[]),
    (6, 'UNI_rate', 'error_rates', 'Dimensión 6 del vector PLN/ML: UNI_rate.', ARRAY[]::TEXT[]),
    (7, 'FON_rate', 'error_rates', 'Dimensión 7 del vector PLN/ML: FON_rate.', ARRAY[]::TEXT[]),
    (8, 'ADD_rate', 'error_rates', 'Dimensión 8 del vector PLN/ML: ADD_rate.', ARRAY[]::TEXT[]),
    (9, 'LEN_rate', 'error_rates', 'Dimensión 9 del vector PLN/ML: LEN_rate.', ARRAY[]::TEXT[]),
    (10, 'accuracy', 'overall_precision', 'Dimensión 10 del vector PLN/ML: accuracy.', ARRAY[]::TEXT[]),
    (11, 'error_rate', 'overall_precision', 'Dimensión 11 del vector PLN/ML: error_rate.', ARRAY[]::TEXT[]),
    (12, 'pseudo_vs_word_gap', 'overall_precision', 'Diferencia pseudo_error_rate - word_error_rate; discriminador principal fonológico vs visual.', ARRAY['M04_REAL_WORDS', 'M05_PSEUDOWORDS']::TEXT[]),
    (13, 'pseudo_error_rate', 'module_gap', 'Dimensión 13 del vector PLN/ML: pseudo_error_rate.', ARRAY['M04_REAL_WORDS', 'M05_PSEUDOWORDS']::TEXT[]),
    (14, 'word_error_rate', 'module_gap', 'Dimensión 14 del vector PLN/ML: word_error_rate.', ARRAY['M04_REAL_WORDS', 'M05_PSEUDOWORDS']::TEXT[]),
    (15, 'avg_time_norm', 'response_time', 'Dimensión 15 del vector PLN/ML: avg_time_norm.', ARRAY['M03_LETTERS_SYLLABLES', 'M08_RAPID_NAMING']::TEXT[]),
    (16, 'std_time_norm', 'response_time', 'Dimensión 16 del vector PLN/ML: std_time_norm.', ARRAY['M03_LETTERS_SYLLABLES', 'M08_RAPID_NAMING']::TEXT[]),
    (17, 'slow_response_rate', 'response_time', 'Dimensión 17 del vector PLN/ML: slow_response_rate.', ARRAY['M03_LETTERS_SYLLABLES', 'M08_RAPID_NAMING']::TEXT[]),
    (18, 'avg_phonetic_sim', 'phonetic_metrics', 'Dimensión 18 del vector PLN/ML: avg_phonetic_sim.', ARRAY[]::TEXT[]),
    (19, 'avg_ngram_overlap', 'phonetic_metrics', 'Dimensión 19 del vector PLN/ML: avg_ngram_overlap.', ARRAY[]::TEXT[]),
    (20, 'rot_sus_ratio', 'visual_indicators', 'Dimensión 20 del vector PLN/ML: rot_sus_ratio.', ARRAY['M03_LETTERS_SYLLABLES', 'M05_PSEUDOWORDS']::TEXT[]),
    (21, 'lex_flag', 'visual_indicators', 'Dimensión 21 del vector PLN/ML: lex_flag.', ARRAY['M03_LETTERS_SYLLABLES', 'M05_PSEUDOWORDS']::TEXT[]),
    (22, 'seg_uni_rate', 'error_structure', 'Dimensión 22 del vector PLN/ML: seg_uni_rate.', ARRAY[]::TEXT[]),
    (23, 'inv_omi_ratio', 'error_structure', 'Dimensión 23 del vector PLN/ML: inv_omi_ratio.', ARRAY[]::TEXT[]),
    (24, 'module_completion_rate_suggested', 'suggested_fillers', 'Feature propuesta para completar hueco del documento: proporción de módulos completados.', ARRAY[]::TEXT[]),
    (25, 'dominant_error_concentration_suggested', 'suggested_fillers', 'Feature propuesta para completar hueco del documento: concentración del error dominante.', ARRAY[]::TEXT[]),
    (26, 'grade_norm', 'context', 'Grado normalizado como grade/6.', ARRAY[]::TEXT[]),
    (27, 'teacher_score_norm', 'context', 'Score docente normalizado como score_docente/100.', ARRAY['M01_TEACHER_PRODISLEX_SCREENING']::TEXT[])
ON CONFLICT (feature_index) DO UPDATE SET
    feature_name = EXCLUDED.feature_name,
    feature_group = EXCLUDED.feature_group,
    description = EXCLUDED.description,
    source_modules = EXCLUDED.source_modules;

INSERT INTO intervention.route_templates (route_code, profile_code, pattern, ordered_exercise_codes, source_rules)
VALUES
    ('ROUTE_FONOLOGICO', 'fonologico', 'falla pseudopalabras mucho más que palabras reales; muchos OMI/INV/FON', ARRAY['CF_silabas_N1', 'CF_fonema_inicial_N1', 'PS_cv_N1', 'DIC_palabras_simples_N1']::TEXT[], '{"source":"Contexto_chat visual + content_pack","rules":["pseudo_vs_word_gap > 0.20 sugiere perfil fonológico","pseudo_vs_word_gap < 0.10 con muchos ROT/LEX sugiere perfil visual/superficial","fallo alto en palabras y pseudopalabras con mezcla FON+ROT sugiere perfil mixto","pocos errores con LEN alto sugiere problema de fluidez/automatización","buena lectura de palabras con COM alto sugiere ruta de comprensión"]}'::JSONB),
    ('ROUTE_VISUAL_SUPERFICIAL', 'visual_superficial', 'muchos ROT b/d/p/q y LEX frecuente', ARRAY['VIS_discriminacion_bd_N1', 'VIS_memoria_palabras_N1', 'DEN_rapid_letras_N1']::TEXT[], '{"source":"Contexto_chat visual + content_pack","rules":["pseudo_vs_word_gap > 0.20 sugiere perfil fonológico","pseudo_vs_word_gap < 0.10 con muchos ROT/LEX sugiere perfil visual/superficial","fallo alto en palabras y pseudopalabras con mezcla FON+ROT sugiere perfil mixto","pocos errores con LEN alto sugiere problema de fluidez/automatización","buena lectura de palabras con COM alto sugiere ruta de comprensión"]}'::JSONB),
    ('ROUTE_MIXTO', 'mixto', 'falla generalizada; combina FON y ROT', ARRAY['MULTI_silabas_cromaticas_N1', 'MULTI_lectura_auditiva_N1', 'CF_silabas_N1', 'PS_cv_N1']::TEXT[], '{"source":"Contexto_chat visual + content_pack","rules":["pseudo_vs_word_gap > 0.20 sugiere perfil fonológico","pseudo_vs_word_gap < 0.10 con muchos ROT/LEX sugiere perfil visual/superficial","fallo alto en palabras y pseudopalabras con mezcla FON+ROT sugiere perfil mixto","pocos errores con LEN alto sugiere problema de fluidez/automatización","buena lectura de palabras con COM alto sugiere ruta de comprensión"]}'::JSONB),
    ('ROUTE_FLUIDEZ', 'fluidez', 'pocos errores pero respuesta lenta', ARRAY['DEN_rapid_colores_N1', 'LEC_repetida_N1', 'LEC_temporizador_N1']::TEXT[], '{"source":"Contexto_chat visual + content_pack","rules":["pseudo_vs_word_gap > 0.20 sugiere perfil fonológico","pseudo_vs_word_gap < 0.10 con muchos ROT/LEX sugiere perfil visual/superficial","fallo alto en palabras y pseudopalabras con mezcla FON+ROT sugiere perfil mixto","pocos errores con LEN alto sugiere problema de fluidez/automatización","buena lectura de palabras con COM alto sugiere ruta de comprensión"]}'::JSONB),
    ('ROUTE_COMPRENSION', 'comprension', 'lee palabras bien pero falla comprensión', ARRAY['COMP_textos_cortos_N1', 'apoyo_auditivo', 'vocabulario_N1']::TEXT[], '{"source":"Contexto_chat visual + content_pack","rules":["pseudo_vs_word_gap > 0.20 sugiere perfil fonológico","pseudo_vs_word_gap < 0.10 con muchos ROT/LEX sugiere perfil visual/superficial","fallo alto en palabras y pseudopalabras con mezcla FON+ROT sugiere perfil mixto","pocos errores con LEN alto sugiere problema de fluidez/automatización","buena lectura de palabras con COM alto sugiere ruta de comprensión"]}'::JSONB)
ON CONFLICT (route_code) DO UPDATE SET
    profile_code = EXCLUDED.profile_code,
    pattern = EXCLUDED.pattern,
    ordered_exercise_codes = EXCLUDED.ordered_exercise_codes,
    source_rules = EXCLUDED.source_rules;

INSERT INTO intervention.learning_paths (name, target_subtype, target_severity, description)
VALUES
    ('Ruta fonológica N1', 'PHONOLOGICAL', 'MILD', 'Conciencia silábica/fonémica, pseudopalabras CV y dictado simple.'),
    ('Ruta visual superficial N1', 'VISUAL_SURFACE', 'MILD', 'Discriminación b/d/p/q, memoria visual de palabras y denominación rápida.'),
    ('Ruta mixta multisensorial N1', 'MIXED', 'MODERATE', 'Segmentación cromática, apoyo auditivo y pseudopalabras graduadas.'),
    ('Ruta fluidez N1', 'FLUENCY', 'MILD', 'Denominación rápida, lectura repetida y temporizador gradual.'),
    ('Ruta comprensión N1', 'COMPREHENSION', 'MILD', 'Textos cortos, apoyo auditivo y vocabulario contextual.')
ON CONFLICT (name) DO UPDATE SET
    target_subtype = EXCLUDED.target_subtype,
    target_severity = EXCLUDED.target_severity,
    description = EXCLUDED.description;

-- Ejercicios semilla: se asignan a una ruta compatible y quedan listos para el Recommendation Service.
INSERT INTO intervention.exercises
    (learning_path_id, exercise_code, title, exercise_type, difficulty, content, has_tts, has_stt, module_id, skill_target, objective, source_tags, ui_config)
VALUES
    ((SELECT id FROM intervention.learning_paths WHERE target_subtype = 'PHONOLOGICAL' ORDER BY created_at LIMIT 1), 'CF_silabas_N1', 'Cf silabas nivel 1', 'PHONOLOGICAL_AWARENESS', 1, '{"route_profile":"fonologico","sequence_order":1,"code":"CF_silabas_N1","adaptive":true}'::JSONB, FALSE, FALSE, (SELECT id FROM assessment.battery_modules WHERE module_code = 'M02_PHONOLOGICAL_AWARENESS'), 'fonologico', 'falla pseudopalabras mucho más que palabras reales; muchos OMI/INV/FON', ARRAY['fonologico', 'CF_silabas_N1']::TEXT[], '{"level":1,"feedback":"visual_auditiva","offline_supported":true}'::JSONB),
    ((SELECT id FROM intervention.learning_paths WHERE target_subtype = 'PHONOLOGICAL' ORDER BY created_at LIMIT 1), 'CF_fonema_inicial_N1', 'Cf fonema inicial nivel 1', 'PHONOLOGICAL_AWARENESS', 1, '{"route_profile":"fonologico","sequence_order":2,"code":"CF_fonema_inicial_N1","adaptive":true}'::JSONB, FALSE, FALSE, (SELECT id FROM assessment.battery_modules WHERE module_code = 'M02_PHONOLOGICAL_AWARENESS'), 'fonologico', 'falla pseudopalabras mucho más que palabras reales; muchos OMI/INV/FON', ARRAY['fonologico', 'CF_fonema_inicial_N1']::TEXT[], '{"level":1,"feedback":"visual_auditiva","offline_supported":true}'::JSONB),
    ((SELECT id FROM intervention.learning_paths WHERE target_subtype = 'PHONOLOGICAL' ORDER BY created_at LIMIT 1), 'PS_cv_N1', 'Ps cv nivel 1', 'PSEUDOWORD_DECODING', 1, '{"route_profile":"fonologico","sequence_order":3,"code":"PS_cv_N1","adaptive":true}'::JSONB, FALSE, FALSE, (SELECT id FROM assessment.battery_modules WHERE module_code = 'M05_PSEUDOWORDS'), 'fonologico', 'falla pseudopalabras mucho más que palabras reales; muchos OMI/INV/FON', ARRAY['fonologico', 'PS_cv_N1']::TEXT[], '{"level":1,"feedback":"visual_auditiva","offline_supported":true}'::JSONB),
    ((SELECT id FROM intervention.learning_paths WHERE target_subtype = 'PHONOLOGICAL' ORDER BY created_at LIMIT 1), 'DIC_palabras_simples_N1', 'Dic palabras simples nivel 1', 'SMART_DICTATION', 1, '{"route_profile":"fonologico","sequence_order":4,"code":"DIC_palabras_simples_N1","adaptive":true}'::JSONB, TRUE, TRUE, (SELECT id FROM assessment.battery_modules WHERE module_code = 'M06_SMART_DICTATION'), 'fonologico', 'falla pseudopalabras mucho más que palabras reales; muchos OMI/INV/FON', ARRAY['fonologico', 'DIC_palabras_simples_N1']::TEXT[], '{"level":1,"feedback":"visual_auditiva","offline_supported":true}'::JSONB),
    ((SELECT id FROM intervention.learning_paths WHERE target_subtype = 'VISUAL_SURFACE' ORDER BY created_at LIMIT 1), 'VIS_discriminacion_bd_N1', 'Vis discriminacion bd nivel 1', 'VISUAL_DISCRIMINATION', 1, '{"route_profile":"visual_superficial","sequence_order":1,"code":"VIS_discriminacion_bd_N1","adaptive":true}'::JSONB, FALSE, FALSE, (SELECT id FROM assessment.battery_modules WHERE module_code = 'M03_LETTERS_SYLLABLES'), 'visual_superficial', 'muchos ROT b/d/p/q y LEX frecuente', ARRAY['visual_superficial', 'VIS_discriminacion_bd_N1']::TEXT[], '{"level":1,"feedback":"visual_auditiva","offline_supported":true}'::JSONB),
    ((SELECT id FROM intervention.learning_paths WHERE target_subtype = 'VISUAL_SURFACE' ORDER BY created_at LIMIT 1), 'VIS_memoria_palabras_N1', 'Vis memoria palabras nivel 1', 'VISUAL_DISCRIMINATION', 1, '{"route_profile":"visual_superficial","sequence_order":2,"code":"VIS_memoria_palabras_N1","adaptive":true}'::JSONB, FALSE, FALSE, (SELECT id FROM assessment.battery_modules WHERE module_code = 'M03_LETTERS_SYLLABLES'), 'visual_superficial', 'muchos ROT b/d/p/q y LEX frecuente', ARRAY['visual_superficial', 'VIS_memoria_palabras_N1']::TEXT[], '{"level":1,"feedback":"visual_auditiva","offline_supported":true}'::JSONB),
    ((SELECT id FROM intervention.learning_paths WHERE target_subtype = 'VISUAL_SURFACE' ORDER BY created_at LIMIT 1), 'DEN_rapid_letras_N1', 'Den rapid letras nivel 1', 'RAPID_NAMING', 1, '{"route_profile":"visual_superficial","sequence_order":3,"code":"DEN_rapid_letras_N1","adaptive":true}'::JSONB, FALSE, TRUE, (SELECT id FROM assessment.battery_modules WHERE module_code = 'M08_RAPID_NAMING'), 'visual_superficial', 'muchos ROT b/d/p/q y LEX frecuente', ARRAY['visual_superficial', 'DEN_rapid_letras_N1']::TEXT[], '{"level":1,"feedback":"visual_auditiva","offline_supported":true}'::JSONB),
    ((SELECT id FROM intervention.learning_paths WHERE target_subtype = 'MIXED' ORDER BY created_at LIMIT 1), 'MULTI_silabas_cromaticas_N1', 'Multi silabas cromaticas nivel 1', 'MULTISENSORY', 1, '{"route_profile":"mixto","sequence_order":1,"code":"MULTI_silabas_cromaticas_N1","adaptive":true}'::JSONB, TRUE, FALSE, (SELECT id FROM assessment.battery_modules WHERE module_code = 'M02_PHONOLOGICAL_AWARENESS'), 'mixto', 'falla generalizada; combina FON y ROT', ARRAY['mixto', 'MULTI_silabas_cromaticas_N1']::TEXT[], '{"level":1,"feedback":"visual_auditiva","offline_supported":true}'::JSONB),
    ((SELECT id FROM intervention.learning_paths WHERE target_subtype = 'MIXED' ORDER BY created_at LIMIT 1), 'MULTI_lectura_auditiva_N1', 'Multi lectura auditiva nivel 1', 'MULTISENSORY', 1, '{"route_profile":"mixto","sequence_order":2,"code":"MULTI_lectura_auditiva_N1","adaptive":true}'::JSONB, TRUE, FALSE, (SELECT id FROM assessment.battery_modules WHERE module_code = 'M02_PHONOLOGICAL_AWARENESS'), 'mixto', 'falla generalizada; combina FON y ROT', ARRAY['mixto', 'MULTI_lectura_auditiva_N1']::TEXT[], '{"level":1,"feedback":"visual_auditiva","offline_supported":true}'::JSONB),
    ((SELECT id FROM intervention.learning_paths WHERE target_subtype = 'FLUENCY' ORDER BY created_at LIMIT 1), 'DEN_rapid_colores_N1', 'Den rapid colores nivel 1', 'RAPID_NAMING', 1, '{"route_profile":"fluidez","sequence_order":1,"code":"DEN_rapid_colores_N1","adaptive":true}'::JSONB, FALSE, TRUE, (SELECT id FROM assessment.battery_modules WHERE module_code = 'M08_RAPID_NAMING'), 'fluidez', 'pocos errores pero respuesta lenta', ARRAY['fluidez', 'DEN_rapid_colores_N1']::TEXT[], '{"level":1,"feedback":"visual_auditiva","offline_supported":true}'::JSONB),
    ((SELECT id FROM intervention.learning_paths WHERE target_subtype = 'FLUENCY' ORDER BY created_at LIMIT 1), 'LEC_repetida_N1', 'Lec repetida nivel 1', 'REPEATED_READING', 1, '{"route_profile":"fluidez","sequence_order":2,"code":"LEC_repetida_N1","adaptive":true}'::JSONB, TRUE, TRUE, (SELECT id FROM assessment.battery_modules WHERE module_code = 'M04_REAL_WORDS'), 'fluidez', 'pocos errores pero respuesta lenta', ARRAY['fluidez', 'LEC_repetida_N1']::TEXT[], '{"level":1,"feedback":"visual_auditiva","offline_supported":true}'::JSONB),
    ((SELECT id FROM intervention.learning_paths WHERE target_subtype = 'FLUENCY' ORDER BY created_at LIMIT 1), 'LEC_temporizador_N1', 'Lec temporizador nivel 1', 'REPEATED_READING', 1, '{"route_profile":"fluidez","sequence_order":3,"code":"LEC_temporizador_N1","adaptive":true}'::JSONB, TRUE, TRUE, (SELECT id FROM assessment.battery_modules WHERE module_code = 'M04_REAL_WORDS'), 'fluidez', 'pocos errores pero respuesta lenta', ARRAY['fluidez', 'LEC_temporizador_N1']::TEXT[], '{"level":1,"feedback":"visual_auditiva","offline_supported":true}'::JSONB),
    ((SELECT id FROM intervention.learning_paths WHERE target_subtype = 'COMPREHENSION' ORDER BY created_at LIMIT 1), 'COMP_textos_cortos_N1', 'Comp textos cortos nivel 1', 'READING_COMPREHENSION', 1, '{"route_profile":"comprension","sequence_order":1,"code":"COMP_textos_cortos_N1","adaptive":true}'::JSONB, TRUE, FALSE, (SELECT id FROM assessment.battery_modules WHERE module_code = 'M09_READING_COMPREHENSION'), 'comprension', 'lee palabras bien pero falla comprensión', ARRAY['comprension', 'COMP_textos_cortos_N1']::TEXT[], '{"level":1,"feedback":"visual_auditiva","offline_supported":true}'::JSONB),
    ((SELECT id FROM intervention.learning_paths WHERE target_subtype = 'COMPREHENSION' ORDER BY created_at LIMIT 1), 'apoyo_auditivo', 'Apoyo auditivo', 'SUPPORT', 1, '{"route_profile":"comprension","sequence_order":2,"code":"apoyo_auditivo","adaptive":true}'::JSONB, FALSE, FALSE, (SELECT id FROM assessment.battery_modules WHERE module_code = 'M09_READING_COMPREHENSION'), 'comprension', 'lee palabras bien pero falla comprensión', ARRAY['comprension', 'apoyo_auditivo']::TEXT[], '{"level":1,"feedback":"visual_auditiva","offline_supported":true}'::JSONB),
    ((SELECT id FROM intervention.learning_paths WHERE target_subtype = 'COMPREHENSION' ORDER BY created_at LIMIT 1), 'vocabulario_N1', 'Vocabulario nivel 1', 'SUPPORT', 1, '{"route_profile":"comprension","sequence_order":3,"code":"vocabulario_N1","adaptive":true}'::JSONB, FALSE, FALSE, (SELECT id FROM assessment.battery_modules WHERE module_code = 'M09_READING_COMPREHENSION'), 'comprension', 'lee palabras bien pero falla comprensión', ARRAY['comprension', 'vocabulario_N1']::TEXT[], '{"level":1,"feedback":"visual_auditiva","offline_supported":true}'::JSONB)
ON CONFLICT (exercise_code) WHERE exercise_code IS NOT NULL DO UPDATE SET
    title = EXCLUDED.title,
    exercise_type = EXCLUDED.exercise_type,
    difficulty = EXCLUDED.difficulty,
    content = EXCLUDED.content,
    has_tts = EXCLUDED.has_tts,
    has_stt = EXCLUDED.has_stt,
    module_id = EXCLUDED.module_id,
    skill_target = EXCLUDED.skill_target,
    objective = EXCLUDED.objective,
    source_tags = EXCLUDED.source_tags,
    ui_config = EXCLUDED.ui_config;

INSERT INTO assessment.tests
    (name, test_type, target_grades, module_id, source_instruments, scoring_config, estimated_duration_min, estimated_duration_max)
VALUES
    ('Cuestionario docente PRODISLEX digitalizado', 'TEACHER_SCREENING', ARRAY[1,2,3,4,5,6]::SMALLINT[], (SELECT id FROM assessment.battery_modules WHERE module_code = 'M01_TEACHER_PRODISLEX_SCREENING'), '["Protocolo-Dislexia-Primaria-1ciclo.pdf","Protocolo-Dislexia-Primaria-2ciclo.pdf","Protocolo-Dislexia-Primaria-3ciclo.pdf"]'::JSONB, '{"captures":["teacher_score_0_100","risk_flags","grade","cycle"],"module_id":"teacher_prodislex_screening"}'::JSONB, 2, 3),
    ('Conciencia fonológica', 'PHONOLOGICAL_AWARENESS', ARRAY[1,2,3,4,5,6]::SMALLINT[], (SELECT id FROM assessment.battery_modules WHERE module_code = 'M02_PHONOLOGICAL_AWARENESS'), '["PROLEXIA_evaluacion_COP.pdf","referencia DST-J del contexto"]'::JSONB, '{"captures":["accuracy","error_code","response_time_ms","audio_uri"],"module_id":"phonological_awareness"}'::JSONB, 4, 5),
    ('Letras y sílabas', 'LETTERS_SYLLABLES', ARRAY[1,2,3,4,5,6]::SMALLINT[], (SELECT id FROM assessment.battery_modules WHERE module_code = 'M03_LETTERS_SYLLABLES'), '["TEDE Parte 1","edtv_6.pdf fichas"]'::JSONB, '{"captures":["expected","produced","accuracy","response_time_ms","OMI/SUS/INV/ROT"],"module_id":"letters_syllables"}'::JSONB, 3, 4),
    ('Palabras reales', 'REAL_WORDS', ARRAY[1,2,3,4,5,6]::SMALLINT[], (SELECT id FROM assessment.battery_modules WHERE module_code = 'M04_REAL_WORDS'), '["TEDE","PROLEC-3 como referencia metodológica"]'::JSONB, '{"captures":["precision","words_per_minute","autocorrections","word_error_rate"],"module_id":"real_words"}'::JSONB, 3, 4),
    ('Pseudopalabras', 'PSEUDOWORDS', ARRAY[1,2,3,4,5,6]::SMALLINT[], (SELECT id FROM assessment.battery_modules WHERE module_code = 'M05_PSEUDOWORDS'), '["TEDE Parte 2","PROLEXIA lectura/deletreo/dictado de pseudopalabras","PROLEC-3 como referencia metodológica"]'::JSONB, '{"captures":["pseudo_error_rate","lexicalization_flag","phonetic_similarity","ngram_overlap"],"module_id":"pseudowords"}'::JSONB, 3, 4),
    ('Dictado inteligente', 'SMART_DICTATION', ARRAY[1,2,3,4,5,6]::SMALLINT[], (SELECT id FROM assessment.battery_modules WHERE module_code = 'M06_SMART_DICTATION'), '["TEDE","LEE como referencia metodológica"]'::JSONB, '{"captures":["expected_text","produced_text","edit_distance","metaphone_similarity","phonological_vs_orthographic_error"],"module_id":"smart_dictation"}'::JSONB, 4, 5),
    ('Copia controlada', 'CONTROLLED_COPY', ARRAY[1,2,3,4,5,6]::SMALLINT[], (SELECT id FROM assessment.battery_modules WHERE module_code = 'M07_CONTROLLED_COPY'), '["TALE/LEE como referencia metodológica","PRODISLEX copiados"]'::JSONB, '{"captures":["copy_error_rate","dictation_copy_gap","visual_error_flags","graphomotor_notes"],"module_id":"controlled_copy"}'::JSONB, 2, 3),
    ('Denominación rápida', 'RAPID_NAMING', ARRAY[1,2,3,4,5,6]::SMALLINT[], (SELECT id FROM assessment.battery_modules WHERE module_code = 'M08_RAPID_NAMING'), '["PROLEXIA RAN colores/objetos","DST-J"]'::JSONB, '{"captures":["total_time_sec","ran_errors","LEN_rate","automation_score"],"module_id":"rapid_naming"}'::JSONB, 2, 3),
    ('Comprensión lectora', 'READING_COMPREHENSION', ARRAY[1,2,3,4,5,6]::SMALLINT[], (SELECT id FROM assessment.battery_modules WHERE module_code = 'M09_READING_COMPREHENSION'), '["PROLEC-3/DST-J como referencia metodológica","PRODISLEX comprensión lectora"]'::JSONB, '{"captures":["literal_accuracy","inferential_accuracy","COM_errors","read_time_ms"],"module_id":"reading_comprehension"}'::JSONB, 4, 5)
ON CONFLICT (name) DO UPDATE SET
    test_type = EXCLUDED.test_type,
    target_grades = EXCLUDED.target_grades,
    module_id = EXCLUDED.module_id,
    source_instruments = EXCLUDED.source_instruments,
    scoring_config = EXCLUDED.scoring_config,
    estimated_duration_min = EXCLUDED.estimated_duration_min,
    estimated_duration_max = EXCLUDED.estimated_duration_max;

-- Vista útil para dashboard docente y API Gateway.
CREATE OR REPLACE VIEW assessment.v_battery_catalog AS
SELECT
    bm.module_number, bm.module_code, bm.title, bm.test_type, bm.duration_min, bm.duration_max,
    bm.input_modes, bm.captures, bm.source_refs, bm.risk_weight,
    COALESCE(t.id::TEXT, '') AS test_id
FROM assessment.battery_modules bm
LEFT JOIN assessment.tests t ON t.module_id = bm.id
WHERE bm.is_active = TRUE
ORDER BY bm.module_number;

CREATE OR REPLACE VIEW diagnosis.v_latest_student_risk AS
SELECT DISTINCT ON (d.student_id)
    d.student_id, d.id AS diagnosis_id, d.subtype, d.severity, d.risk_probability,
    COALESCE(d.risk_level, CASE WHEN d.risk_probability >= 0.66 THEN 'HIGH' WHEN d.risk_probability >= 0.31 THEN 'MEDIUM' ELSE 'LOW' END) AS risk_level,
    d.main_error_codes, d.diagnosed_at
FROM diagnosis.diagnoses d
ORDER BY d.student_id, d.diagnosed_at DESC;

-- =============================================================
-- Fin migración v2
-- =============================================================
