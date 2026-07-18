-- =============================================================
-- 016 — Desglose del tiempo de respuesta
--
-- POR QUÉ: `response_time_ms` es un solo número, y es la entrada de la
-- feature con más peso del modelo (`avg_time_norm`, importancia 0.163 de 28).
-- Hasta la corrección de la Etapa 1 ese número mezclaba tres cosas distintas:
-- el tiempo que el niño tardó en resolver, la reproducción del audio de apoyo
-- y el tiempo con la app en segundo plano.
--
-- Guardar el desglose permite:
--   1. auditar de dónde salió cada tiempo (hoy es imposible saber si un ítem
--      lento lo fue por el niño o por 4s de audio);
--   2. alimentar el reentrenamiento con métricas mejores — normalizar por
--      longitud del estímulo requiere saber cuántas palabras tenía el ítem,
--      y eso hoy no se persiste en ningún lado.
--
-- Se usa JSONB y no columnas sueltas porque el set de métricas va a crecer
-- con la Etapa 3 (tiempo por palabra, latencia relativa al grado) y no
-- conviene una migración por cada una.
--
-- `response_time_ms` se conserva intacto: es lo que consume el pipeline hoy y
-- lo que envían los clientes viejos.
--
-- Idempotente. Requiere 001 (schema.sql).
-- =============================================================

ALTER TABLE assessment.student_responses
    ADD COLUMN IF NOT EXISTS timing_detail JSONB NOT NULL DEFAULT '{}'::JSONB;

COMMENT ON COLUMN assessment.student_responses.timing_detail IS
    'Desglose del tiempo del ítem: {total_ms, tts_ms, background_ms, net_ms, '
    'stimulus_chars, stimulus_words, difficulty}. net_ms = total - tts - background '
    'y es el que viaja como response_time_ms. Vacío {} en respuestas anteriores a '
    'la migración 016 o enviadas por clientes viejos.';
