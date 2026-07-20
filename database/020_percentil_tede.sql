-- 020 — Guarda el percentil normativo del TEDE junto al diagnóstico.
--
-- POR QUÉ
--
-- La severidad que ve el docente (leve/moderado/severo) sale del modelo de
-- aprendizaje automático. Ese modelo se entrenó con datos sintéticos y
-- `diagnosis.training_labels` tiene **cero** etiquetas de especialista, así
-- que hoy no hay forma de saber si acierta.
--
-- Al mismo tiempo, el proyecto ya tenía digitalizadas las tablas de
-- percentiles del TEDE (Condemarín-Blomquist, estandarización de Berdicewsky,
-- Milicic y Orellana, 1974) en `Pln/diagnosis_service/app/tede_scoring.py`.
-- Nadie las llamaba: eran código muerto. Alguien hizo el trabajo de
-- transcribirlas y el resultado nunca llegó a un docente.
--
-- Un percentil no reemplaza al modelo: lo acompaña. Si coinciden, el docente
-- tiene respaldo normativo para una decisión que afecta a un niño. Si
-- difieren, ese desacuerdo es la única señal disponible de que el modelo
-- necesita revisión mientras no haya etiquetas con qué validarlo.
--
-- Además el percentil es comparable en el tiempo por construcción, que es
-- justo lo que hace falta para leer la curva de avance.
--
-- QUÉ SE GUARDA
--
-- Solo el subtest de Nivel Lector. El TEDE tiene un segundo subtest, Errores
-- Específicos, que puntúa sobre 71 ítems fijos restando los errores; nuestro
-- conteo de errores no corresponde a esa escala y llevarlo a esa tabla daría
-- un número con apariencia normativa y sin fundamento.
--
-- JSONB y no columnas sueltas porque el objeto lleva el percentil por edad, el
-- percentil por curso, los aciertos, cuántos ítems se administraron y si el
-- puntaje se escaló. Ese último dato importa para saber cuánta confianza
-- darle: no es lo mismo derivarlo de 100 ítems que de 30.

BEGIN;

ALTER TABLE diagnosis.diagnoses
    ADD COLUMN IF NOT EXISTS tede_nivel_lector JSONB;

COMMENT ON COLUMN diagnosis.diagnoses.tede_nivel_lector IS
    'Percentil normativo del subtest Nivel Lector del TEDE, por edad y por '
    'curso. NULL cuando la sesión no incluyó ítems de lectura de letras y '
    'sílabas: es preferible no informar percentil a informar uno sin '
    'fundamento. Incluye `escalado` para indicar si el puntaje se llevó a la '
    'escala de 100 del baremo desde una administración más corta.';

COMMIT;

-- ─── Verificación ────────────────────────────────────────────────────────────
--
--   SELECT d.diagnosed_at,
--          d.severity            AS severidad_modelo,
--          d.tede_nivel_lector->>'percentil_por_grado' AS percentil_tede,
--          d.tede_nivel_lector->>'escalado'            AS escalado
--     FROM diagnosis.diagnoses d
--    ORDER BY d.diagnosed_at DESC;
--
-- Cuando haya varios diagnósticos, la comparación entre `severidad_modelo` y
-- `percentil_tede` es la que dice si el modelo se puede empezar a creer.
