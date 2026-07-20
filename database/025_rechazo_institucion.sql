-- 025 — Rechazo de una solicitud de institución.
--
-- POR QUÉ
--
-- El alta de una escuela tenía dos salidas de hecho: aprobada (is_active =
-- TRUE) o pendiente para siempre. No había forma de rechazar una solicitud, así
-- que una escuela ilegítima o duplicada quedaba en /pending sin caducar, y su
-- solicitante nunca recibía respuesta.
--
-- No alcanza con dejarla en is_active = FALSE: /pending filtra exactamente por
-- eso, así que una rechazada volvería a aparecer en la lista del SUPERADMIN en
-- cada carga. Hace falta un estado que distinga "todavía sin decidir" de
-- "decidido que no".
--
-- Se guarda además el motivo y quién rechazó, por dos razones: el solicitante
-- merece saber por qué, y el rechazo de una escuela es una decisión que
-- conviene poder auditar.

BEGIN;

ALTER TABLE academic.schools
    ADD COLUMN IF NOT EXISTS rejected_at   TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS rejected_by   UUID REFERENCES auth.users(id),
    ADD COLUMN IF NOT EXISTS rejection_reason TEXT;

COMMENT ON COLUMN academic.schools.rejected_at IS
    'Cuándo se rechazó la solicitud. Con rejected_at no nulo la escuela deja '
    'de aparecer en /pending aunque siga inactiva.';

-- Una escuela no puede estar aprobada y rechazada a la vez.
ALTER TABLE academic.schools
    DROP CONSTRAINT IF EXISTS schools_no_aprobada_y_rechazada;
ALTER TABLE academic.schools
    ADD CONSTRAINT schools_no_aprobada_y_rechazada
    CHECK (NOT (is_active AND rejected_at IS NOT NULL));

COMMIT;

-- ─── Verificación ────────────────────────────────────────────────────────────
--
-- /pending debe listar solo lo que sigue sin decidir:
--
--   SELECT count(*) FROM academic.schools
--    WHERE is_active = FALSE AND rejected_at IS NULL;
