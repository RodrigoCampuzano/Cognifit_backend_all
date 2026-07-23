-- 027 — Solo dos planes de licencia: premium mensual y premium anual.
--
-- POR QUÉ
--
-- El plan institucional se sembró junto con los otros dos en 026 pero no se
-- va a vender por ahora. No se borra la fila (evita romper una FK si algún
-- pago llegara a referenciarla): se desactiva igual que cualquier plan que
-- deja de venderse — GET /payments/plans ya filtra por is_active = TRUE, así
-- que basta con este UPDATE para que deje de aparecer en la app.

BEGIN;

UPDATE billing.plans
   SET is_active = FALSE
 WHERE code = 'institutional_anual';

COMMIT;

-- ─── Verificación ────────────────────────────────────────────────────────────
--
-- Deben quedar exactamente dos planes visibles:
--   SELECT code FROM billing.plans WHERE is_active = TRUE ORDER BY price_cents;
