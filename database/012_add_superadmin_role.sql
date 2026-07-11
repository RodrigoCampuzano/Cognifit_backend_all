-- =============================================================
-- 012 — Agrega el rol SUPERADMIN (operador de plataforma) al enum
-- auth.user_role. Aislado en su propio archivo: Postgres no permite
-- usar un valor de enum recién agregado en la misma transacción que
-- lo crea (mismo patrón que 004_user_roles_parent_specialist.sql).
-- Idempotente.
-- =============================================================

ALTER TYPE auth.user_role ADD VALUE IF NOT EXISTS 'SUPERADMIN';
