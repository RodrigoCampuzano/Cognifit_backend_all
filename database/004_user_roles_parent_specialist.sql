-- =============================================================
-- 004 — Completa el catálogo de roles (HU-BD-01: docente, alumno, padre/tutor, administrador).
-- El enum 001 solo traía ADMIN/TEACHER/STUDENT, pero el RBAC del backend
-- (require_roles) usa SPECIALIST y PARENT. Sin estos valores no se puede
-- crear usuarios padre/tutor ni especialista. Idempotente.
-- =============================================================

ALTER TYPE auth.user_role ADD VALUE IF NOT EXISTS 'PARENT';
ALTER TYPE auth.user_role ADD VALUE IF NOT EXISTS 'SPECIALIST';
