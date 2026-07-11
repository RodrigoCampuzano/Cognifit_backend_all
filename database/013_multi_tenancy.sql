-- =============================================================
-- 013 — Multi-tenancy: cada cuenta pertenece a una institución.
--
-- Hasta ahora auth.users no tenía ningún vínculo con academic.schools,
-- así que ADMIN/SPECIALIST veían datos de TODAS las escuelas del
-- sistema (is_privileged = sin filtro). Esto es inviable en cuanto la
-- app se publique y más de una escuela se registre.
--
-- Agrega institution_id a auth.users, un flujo de aprobación manual
-- para escuelas nuevas (is_active), y consolida las escuelas
-- "Escuela CogniFit" duplicadas del piloto en una sola institución
-- activa antes de aplicar el CHECK constraint.
-- Idempotente.
-- =============================================================

-- 1. Columnas de aprobación en academic.schools
ALTER TABLE academic.schools
    ADD COLUMN IF NOT EXISTS is_active   BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS approved_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS approved_by UUID REFERENCES auth.users(id);

-- 2. institution_id en auth.users (nullable por ahora, se llena en el backfill)
ALTER TABLE auth.users
    ADD COLUMN IF NOT EXISTS institution_id UUID REFERENCES academic.schools(id);

-- 3. Backfill del piloto: consolidar escuelas "Escuela CogniFit" duplicadas.
--    Se queda con la única que tiene grupos reales; el resto (huérfanas,
--    sin academic.groups apuntando a ellas) se eliminan.
DO $$
DECLARE
    canonical_school_id UUID;
BEGIN
    -- Escuela con más grupos asociados = la real del piloto.
    SELECT school_id INTO canonical_school_id
    FROM academic.groups
    GROUP BY school_id
    ORDER BY count(*) DESC
    LIMIT 1;

    IF canonical_school_id IS NOT NULL THEN
        -- Aprobar la institución piloto retroactivamente.
        UPDATE academic.schools
        SET is_active = TRUE, approved_at = COALESCE(approved_at, now())
        WHERE id = canonical_school_id;

        -- Todo usuario existente sin institución (todos, en el piloto) → esa escuela.
        UPDATE auth.users
        SET institution_id = canonical_school_id
        WHERE institution_id IS NULL AND role <> 'SUPERADMIN';

        -- Escuelas huérfanas (sin grupos, distintas de la canónica) son basura
        -- de _ensure_school() creando una por cada docente sin escuela previa.
        DELETE FROM academic.schools
        WHERE id <> canonical_school_id
          AND id NOT IN (SELECT DISTINCT school_id FROM academic.groups);
    END IF;
END $$;

-- 4. Ahora que el backfill terminó, forzar la regla a futuro.
ALTER TABLE auth.users
    DROP CONSTRAINT IF EXISTS ck_users_institution_required;
ALTER TABLE auth.users
    ADD CONSTRAINT ck_users_institution_required
    CHECK (role = 'SUPERADMIN' OR institution_id IS NOT NULL);

CREATE INDEX IF NOT EXISTS idx_users_institution ON auth.users(institution_id);
