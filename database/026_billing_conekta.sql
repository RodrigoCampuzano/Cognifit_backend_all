-- 026 — Pagos de licencia vía Conekta (tarjeta + efectivo/OXXO).
--
-- POR QUÉ
--
-- El modelo de negocio es licenciamiento institucional: academic.schools ya
-- reserva license_tier / license_expires_at pero nada los escribe. Hace falta
-- registrar qué escuela compró qué plan, con qué medio de pago, y en qué
-- estado quedó — sobre todo porque "efectivo" (OXXO) es asíncrono: la orden
-- se crea en estado pendiente y solo se sabe si se pagó cuando llega el
-- webhook de Conekta, minutos u horas (o nunca) después de generarse la
-- referencia.
--
-- Se separa en su propio schema (billing) siguiendo la convención existente
-- de un schema por dominio (auth, academic, assessment, ...).

BEGIN;

CREATE SCHEMA IF NOT EXISTS billing;

-- Catálogo de planes vendibles. No se borra un plan que ya se vendió: se
-- desactiva (is_active = FALSE) para no romper el historial de pagos.
CREATE TABLE IF NOT EXISTS billing.plans (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    code            TEXT UNIQUE NOT NULL,
    name            TEXT NOT NULL,
    license_tier    TEXT NOT NULL CHECK (license_tier IN ('freemium', 'premium', 'institutional')),
    price_cents     INTEGER NOT NULL CHECK (price_cents >= 0),
    currency        TEXT NOT NULL DEFAULT 'MXN',
    billing_period  TEXT NOT NULL CHECK (billing_period IN ('monthly', 'yearly')),
    features        JSONB NOT NULL DEFAULT '{}'::jsonb,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
COMMENT ON TABLE billing.plans IS 'Catálogo de planes de licencia vendibles vía Conekta.';

-- Un customer de Conekta por escuela: se reutiliza en pagos sucesivos (mismo
-- customer_id) en vez de crear uno nuevo en cada checkout.
CREATE TABLE IF NOT EXISTS billing.school_conekta_customers (
    school_id           UUID PRIMARY KEY REFERENCES academic.schools(id) ON DELETE CASCADE,
    conekta_customer_id TEXT UNIQUE NOT NULL,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
COMMENT ON TABLE billing.school_conekta_customers IS 'Mapeo 1:1 escuela -> customer de Conekta.';

CREATE TABLE IF NOT EXISTS billing.payments (
    id                    UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    school_id             UUID NOT NULL REFERENCES academic.schools(id) ON DELETE CASCADE,
    plan_id               UUID NOT NULL REFERENCES billing.plans(id),
    created_by_user_id    UUID NOT NULL REFERENCES auth.users(id),
    conekta_order_id      TEXT UNIQUE,
    payment_method_type   TEXT NOT NULL CHECK (payment_method_type IN ('card', 'cash')),
    status                TEXT NOT NULL DEFAULT 'pending'
                              CHECK (status IN ('pending', 'paid', 'expired', 'canceled', 'failed', 'refunded')),
    amount_cents          INTEGER NOT NULL CHECK (amount_cents >= 0),
    currency              TEXT NOT NULL DEFAULT 'MXN',
    -- Solo aplica a payment_method_type = 'cash' (referencia OXXO).
    cash_reference        TEXT,
    cash_barcode_url      TEXT,
    cash_expires_at       TIMESTAMPTZ,
    paid_at               TIMESTAMPTZ,
    -- Clave que viaja como Idempotency-Key a la API de Conekta: evita crear
    -- dos órdenes si la request de checkout se reintenta (timeout, doble tap).
    idempotency_key       TEXT UNIQUE NOT NULL,
    raw_last_event        JSONB,
    created_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at            TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
COMMENT ON TABLE billing.payments IS 'Un intento/orden de pago de licencia. La verdad de si se pagó llega por webhook, no por la respuesta síncrona del checkout.';

CREATE INDEX IF NOT EXISTS idx_billing_payments_school ON billing.payments(school_id);
CREATE INDEX IF NOT EXISTS idx_billing_payments_status ON billing.payments(status);

-- Log de eventos de webhook recibidos. conekta_event_id es la clave de
-- idempotencia: Conekta puede reenviar el mismo evento (reintentos ante
-- timeout de nuestro lado), y sin esto un mismo pago se procesaría dos veces.
CREATE TABLE IF NOT EXISTS billing.webhook_events (
    id                UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    conekta_event_id  TEXT UNIQUE NOT NULL,
    event_type        TEXT NOT NULL,
    payload           JSONB NOT NULL,
    processed_at      TIMESTAMPTZ,
    processing_error  TEXT,
    received_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
COMMENT ON TABLE billing.webhook_events IS 'Idempotencia de webhooks de Conekta: un conekta_event_id solo se procesa una vez.';

-- Trigger para mantener updated_at sin repetir SET updated_at = now() en cada
-- UPDATE del repositorio.
CREATE OR REPLACE FUNCTION billing.set_updated_at() RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_billing_payments_updated_at ON billing.payments;
CREATE TRIGGER trg_billing_payments_updated_at
    BEFORE UPDATE ON billing.payments
    FOR EACH ROW EXECUTE FUNCTION billing.set_updated_at();

-- Seed de planes iniciales, alineados a mvp_cognifit_escolar.md (freemium ya
-- existe por default en academic.schools y no requiere pago).
INSERT INTO billing.plans (code, name, license_tier, price_cents, currency, billing_period, features)
VALUES
    ('premium_mensual', 'Premium mensual', 'premium', 49900, 'MXN', 'monthly',
        '{"grupos_ilimitados": true, "reportes_pdf": true, "soporte_prioritario": false}'::jsonb),
    ('premium_anual', 'Premium anual', 'premium', 479900, 'MXN', 'yearly',
        '{"grupos_ilimitados": true, "reportes_pdf": true, "soporte_prioritario": false}'::jsonb),
    ('institutional_anual', 'Institucional anual', 'institutional', 1499900, 'MXN', 'yearly',
        '{"grupos_ilimitados": true, "reportes_pdf": true, "soporte_prioritario": true, "multi_plantel": true}'::jsonb)
ON CONFLICT (code) DO NOTHING;

COMMIT;

-- ─── Verificación ────────────────────────────────────────────────────────────
--
-- Planes cargados:
--   SELECT code, license_tier, price_cents, billing_period FROM billing.plans;
--
-- Un pago no puede quedar "paid" sin paid_at (ni al revés):
--   SELECT id FROM billing.payments WHERE (status = 'paid') != (paid_at IS NOT NULL);
