-- 021 — Historia clínica de PRODISLEX: descartar causas sensoriales.
--
-- POR QUÉ
--
-- La definición de dislexia que usa el propio protocolo PRODISLEX dice:
--
--   "dificultad significativa en el aprendizaje de la lectura y de la
--    escritura, EN AUSENCIA DE ALTERACIONES NEUROLÓGICAS Y/O SENSORIALES QUE
--    LO JUSTIFIQUEN"
--
-- Es decir: descartar una causa sensorial no es un dato de contexto, es parte
-- de la definición. Un niño que no ve bien el pizarrón lee mal, y no es
-- disléxico.
--
-- El cuestionario de la aplicación tenía 8 ítems, todos del área de lectura y
-- escritura del protocolo. El bloque de historia clínica —que es el primero
-- del PRODISLEX— no estaba. Sin él, la app puede emitir "fonológico severo"
-- para un alumno que necesita lentes, y nada en el flujo lo detiene. Es el
-- falso positivo más caro que puede cometer un tamizaje.
--
-- POR QUÉ NO SUMAN PUNTAJE
--
-- Estos ítems no indican dislexia: indican una explicación alternativa. Darles
-- peso en la escala 0-100 los haría subir el riesgo, que es exactamente lo
-- contrario de lo que significan. Van con weight = 0 y se marcan con una
-- categoría propia para que el cálculo los excluya.
--
-- Lo que sí hacen es levantar una advertencia que acompaña al diagnóstico.

BEGIN;

ALTER TABLE assessment.teacher_screening_items
    ADD COLUMN IF NOT EXISTS categoria TEXT NOT NULL DEFAULT 'RIESGO';

COMMENT ON COLUMN assessment.teacher_screening_items.categoria IS
    'RIESGO: indica sintomatología de dislexia y suma al puntaje 0-100. '
    'HISTORIA_CLINICA: descarta causas alternativas (sensoriales, '
    'neurológicas); NO suma puntaje y levanta advertencia cuando es afirmativo.';

-- Restricción: lo que no es RIESGO no puede tener peso. Sin esto, agregar un
-- ítem clínico con peso por descuido lo haría subir el riesgo, que es lo
-- contrario de lo que significa.
ALTER TABLE assessment.teacher_screening_items
    DROP CONSTRAINT IF EXISTS tsi_solo_riesgo_pesa;
ALTER TABLE assessment.teacher_screening_items
    ADD CONSTRAINT tsi_solo_riesgo_pesa
    CHECK (categoria = 'RIESGO' OR weight = 0);

-- ─── Los cinco ítems de historia clínica del PRODISLEX ───────────────────────
-- Redactados como pregunta directa al docente, en lugar del "Especificar:" del
-- formulario en papel: la app necesita una respuesta discreta para poder
-- razonar sobre ella.
INSERT INTO assessment.teacher_screening_items
    (item_code, prompt, weight, tags, source_note, scale, categoria, is_active)
VALUES
    ('h01_vision',
     '¿Tiene alguna dificultad de visión sin corregir? (no usa los lentes que necesita, o nunca fue revisado)',
     0, ARRAY['sensorial','vision'],
     'PRODISLEX — Historia clínica: presencia de alteración visual',
     '[{"label":"No","value":0},{"label":"No lo sé","value":0.5},{"label":"Sí","value":1}]'::jsonb,
     'HISTORIA_CLINICA', TRUE),

    ('h02_audicion',
     '¿Tiene alguna dificultad de audición sin corregir, o infecciones de oído frecuentes?',
     0, ARRAY['sensorial','audicion'],
     'PRODISLEX — Historia clínica: presencia de alteración auditiva',
     '[{"label":"No","value":0},{"label":"No lo sé","value":0.5},{"label":"Sí","value":1}]'::jsonb,
     'HISTORIA_CLINICA', TRUE),

    ('h03_neurologico',
     '¿Tiene alguna valoración o diagnóstico neurológico previo?',
     0, ARRAY['neurologico'],
     'PRODISLEX — Historia clínica: valoración neurológica',
     '[{"label":"No","value":0},{"label":"No lo sé","value":0.5},{"label":"Sí","value":1}]'::jsonb,
     'HISTORIA_CLINICA', TRUE),

    ('h04_ausentismo',
     '¿Ha faltado a clases de forma prolongada o llegó tarde a la escolarización?',
     0, ARRAY['oportunidad_escolar'],
     'PRODISLEX — la definición exige haber recibido previamente oportunidades escolares',
     '[{"label":"No","value":0},{"label":"No lo sé","value":0.5},{"label":"Sí","value":1}]'::jsonb,
     'HISTORIA_CLINICA', TRUE),

    ('h05_antecedentes',
     '¿Hay antecedentes familiares de dificultades de lectura o escritura?',
     0, ARRAY['antecedente_familiar'],
     'PRODISLEX — Historia clínica: antecedentes familiares. El protocolo señala '
     'el factor genético como causa inicial conocida',
     '[{"label":"No","value":0},{"label":"No lo sé","value":0.5},{"label":"Sí","value":1}]'::jsonb,
     'HISTORIA_CLINICA', TRUE)
ON CONFLICT (item_code) DO NOTHING;

COMMIT;

-- ─── Verificación ────────────────────────────────────────────────────────────
--
-- Los de riesgo deben seguir sumando exactamente 100:
--
--   SELECT categoria, count(*), sum(weight)
--     FROM assessment.teacher_screening_items
--    WHERE is_active GROUP BY categoria;
--
--   RIESGO           8   100.00
--   HISTORIA_CLINICA 5     0.00
--
-- La opción "No lo sé" existe porque el formulario en papel tiene una tercera
-- columna, SE ("sin evidencias, se necesita más observación"). Obligar al
-- docente a elegir entre sí y no cuando no lo sabe produce un dato inventado.
