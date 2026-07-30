-- 028 — Pagos de licencia vía transferencia SPEI (Conekta).
--
-- POR QUÉ
--
-- El checkout de licencia ya soporta tarjeta (card) y efectivo/OXXO (cash);
-- se agrega SPEI como tercer medio. Igual que cash, es asíncrono: la orden
-- responde con una CLABE para que el ADMIN transfiera desde su banco, y solo
-- se sabe que se pagó cuando llega el webhook order.paid (mismo flujo, mismo
-- handler — ver handle_conekta_webhook.py, no requiere cambios).
--
-- Se agregan columnas spei_* en vez de reutilizar cash_reference/
-- cash_barcode_url: una CLABE no es una referencia OXXO ni tiene barcode, y
-- forzarlas en los mismos campos habría confundido la respuesta del API para
-- quien la consuma.

BEGIN;

-- Busca el nombre real de la constraint en vez de asumir el default de
-- Postgres (payments_payment_method_type_check): si alguna vez se renombró
-- a mano, un DROP CONSTRAINT IF EXISTS con el nombre adivinado no haría
-- nada y el ADD de abajo dejaría DOS checks activos (la vieja seguiría
-- rechazando 'spei').
DO $$
DECLARE
    constraint_name TEXT;
BEGIN
    SELECT con.conname INTO constraint_name
    FROM pg_constraint con
    JOIN pg_class rel ON rel.oid = con.conrelid
    JOIN pg_namespace nsp ON nsp.oid = rel.relnamespace
    WHERE nsp.nspname = 'billing'
      AND rel.relname = 'payments'
      AND con.contype = 'c'
      AND pg_get_constraintdef(con.oid) ILIKE '%payment_method_type%';

    IF constraint_name IS NOT NULL THEN
        EXECUTE format('ALTER TABLE billing.payments DROP CONSTRAINT %I', constraint_name);
    END IF;
END $$;

ALTER TABLE billing.payments
    ADD CONSTRAINT payments_payment_method_type_check
    CHECK (payment_method_type IN ('card', 'cash', 'spei'));

ALTER TABLE billing.payments ADD COLUMN IF NOT EXISTS spei_clabe TEXT;
ALTER TABLE billing.payments ADD COLUMN IF NOT EXISTS spei_bank TEXT;
ALTER TABLE billing.payments ADD COLUMN IF NOT EXISTS spei_expires_at TIMESTAMPTZ;

COMMENT ON COLUMN billing.payments.spei_clabe IS 'CLABE interbancaria a la que el ADMIN debe transferir. Solo aplica a payment_method_type = spei.';
COMMENT ON COLUMN billing.payments.spei_bank IS 'Nombre del banco receptor que devuelve Conekta junto a la CLABE.';

COMMIT;

-- ─── Verificación ────────────────────────────────────────────────────────────
--
-- SELECT payment_method_type, spei_clabe, spei_bank, spei_expires_at
--   FROM billing.payments WHERE payment_method_type = 'spei';
