-- 023 — PRODISLEX por ciclo: el cuestionario deja de ser uno solo.
--
-- POR QUÉ
--
-- PRODISLEX no es un protocolo: son tres, uno por ciclo de primaria, y sus
-- indicadores no coinciden. Comparados los tres PDF, la progresión es
-- deliberada:
--
--   1er ciclo (6-8)   ¿está ADQUIRIENDO la lectura?
--                     segmentación de sonidos, unión de sonidos, adquisición
--                     de la lectura y la escritura, nivel lector frente al
--                     grupo clase
--
--   2º ciclo (8-10)   ¿la CONSOLIDÓ?
--                     aparecen morfosintaxis, puntuación, redacción de
--                     composiciones y toma de apuntes; siguen presentes la
--                     segmentación y la unión de sonidos
--
--   3er ciclo (10-12) ¿la AUTOMATIZÓ?
--                     desaparecen los indicadores fonológicos básicos y el
--                     referente de velocidad pasa a ser la edad cronológica,
--                     no el grupo; aparece el uso de la lectura para aprender
--                     (diccionario, índices, otras lenguas)
--
-- La aplicación usaba los mismos ítems para un niño de 6 años y uno de 12: le
-- preguntaba al de 1º si toma bien apuntes, y al de 6º no le preguntaba por
-- segmentación de sonidos. Como el objetivo es seguir el avance en el tiempo,
-- usar el mismo instrumento a los 6 y a los 12 mide cosas distintas con la
-- misma vara.
--
-- CÓMO
--
-- `ciclos` es un arreglo: un ítem común lleva {1,2,3} y uno específico solo su
-- ciclo. Evita duplicar dieciséis veces la misma pregunta y deja explícito
-- qué comparte cada protocolo.
--
-- El puntaje sigue saliendo 0-100 sin tocar nada: `calculate_teacher_score` ya
-- normaliza dividiendo por el peso total cuando no suma 100, así que cada
-- ciclo se escala solo aunque tenga distinta cantidad de ítems.

BEGIN;

ALTER TABLE assessment.teacher_screening_items
    ADD COLUMN IF NOT EXISTS ciclos SMALLINT[] NOT NULL DEFAULT ARRAY[1,2,3];

COMMENT ON COLUMN assessment.teacher_screening_items.ciclos IS
    'Ciclos de primaria en los que aplica el ítem: 1 (1º-2º), 2 (3º-4º), '
    '3 (5º-6º). PRODISLEX tiene un protocolo por ciclo y sus indicadores '
    'difieren: lo fonológico básico desaparece hacia el tercero y aparece el '
    'uso de la lectura para aprender.';

ALTER TABLE assessment.teacher_screening_items
    DROP CONSTRAINT IF EXISTS tsi_ciclos_validos;
ALTER TABLE assessment.teacher_screening_items
    ADD CONSTRAINT tsi_ciclos_validos
    CHECK (ciclos <@ ARRAY[1,2,3]::SMALLINT[] AND array_length(ciclos, 1) >= 1);

-- ─── Ajuste de los ítems que ya existían ─────────────────────────────────────
-- Los errores de tipo rotación, inversión, omisión y sustitución están en los
-- tres protocolos; el rechazo a leer solo en los dos primeros —en el tercero
-- el protocolo lo formula como "no le gusta leer en público", ya presente
-- desde el segundo.
UPDATE assessment.teacher_screening_items
   SET ciclos = ARRAY[1,2]::SMALLINT[]
 WHERE item_code = 'q06_evita_leer';

-- ─── Ítems propios de cada ciclo ─────────────────────────────────────────────
-- Peso 8: es la media aproximada de los ocho ítems que ya existían (12.5)
-- reducida para no desplazar demasiado su calibración documentada. REVISAR con
-- un especialista: a diferencia de los ocho originales —cuyos pesos citan
-- PRODISLEX y TEDE— este valor no tiene respaldo, es una decisión de
-- implementación para que el ítem cuente sin dominar.
INSERT INTO assessment.teacher_screening_items
    (item_code, prompt, weight, tags, source_note, scale, categoria, ciclos, is_active)
VALUES
    -- ── Solo 1er ciclo: adquisición y conciencia fonológica ──
    ('c1_segmentacion',
     'Le cuesta separar una palabra en sus sonidos o sílabas.',
     8, ARRAY['SEG','fonologico'],
     'PRODISLEX 1er y 2º ciclo — dificultades en la segmentación de sonidos. '
     'REVISAR peso: sin respaldo documentado',
     '[{"label":"Nunca","value":0},{"label":"A veces","value":0.5},{"label":"Frecuente","value":1}]'::jsonb,
     'RIESGO', ARRAY[1,2]::SMALLINT[], TRUE),

    ('c1_union_sonidos',
     'Le cuesta juntar sonidos sueltos para formar una palabra.',
     8, ARRAY['UNI','fonologico'],
     'PRODISLEX 1er y 2º ciclo — dificultades en la unión de sonidos. '
     'REVISAR peso: sin respaldo documentado',
     '[{"label":"Nunca","value":0},{"label":"A veces","value":0.5},{"label":"Frecuente","value":1}]'::jsonb,
     'RIESGO', ARRAY[1,2]::SMALLINT[], TRUE),

    ('c1_adquisicion',
     'Le está costando aprender a leer o a escribir más que a sus compañeros.',
     8, ARRAY['adquisicion'],
     'PRODISLEX 1er ciclo — dificultades significativas en la adquisición de '
     'la lectura y la escritura. REVISAR peso: sin respaldo documentado',
     '[{"label":"Nunca","value":0},{"label":"A veces","value":0.5},{"label":"Frecuente","value":1}]'::jsonb,
     'RIESGO', ARRAY[1]::SMALLINT[], TRUE),

    -- ── 2º y 3er ciclo: consolidación y uso de la lectura ──
    ('c2_morfosintaxis',
     'Le cuesta identificar conceptos gramaticales (sujeto, verbo, tipos de palabra).',
     8, ARRAY['morfosintaxis'],
     'PRODISLEX 2º y 3er ciclo — dificultades para identificar conceptos '
     'morfosintácticos. REVISAR peso: sin respaldo documentado',
     '[{"label":"Nunca","value":0},{"label":"A veces","value":0.5},{"label":"Frecuente","value":1}]'::jsonb,
     'RIESGO', ARRAY[2,3]::SMALLINT[], TRUE),

    ('c2_puntuacion',
     'Comete muchos errores de puntuación al leer y al escribir.',
     8, ARRAY['puntuacion'],
     'PRODISLEX 2º y 3er ciclo — número elevado de errores de puntuación. '
     'REVISAR peso: sin respaldo documentado',
     '[{"label":"Nunca","value":0},{"label":"A veces","value":0.5},{"label":"Frecuente","value":1}]'::jsonb,
     'RIESGO', ARRAY[2,3]::SMALLINT[], TRUE),

    ('c2_composiciones',
     'Le cuesta planificar y redactar un texto propio.',
     8, ARRAY['composicion_escrita'],
     'PRODISLEX 2º y 3er ciclo — dificultad para planificar y redactar '
     'composiciones escritas. REVISAR peso: sin respaldo documentado',
     '[{"label":"Nunca","value":0},{"label":"A veces","value":0.5},{"label":"Frecuente","value":1}]'::jsonb,
     'RIESGO', ARRAY[2,3]::SMALLINT[], TRUE),

    ('c2_apuntes',
     'Le cuesta tomar apuntes mientras se explica.',
     8, ARRAY['apuntes'],
     'PRODISLEX 2º y 3er ciclo — dificultades a la hora de tomar apuntes. '
     'REVISAR peso: sin respaldo documentado',
     '[{"label":"Nunca","value":0},{"label":"A veces","value":0.5},{"label":"Frecuente","value":1}]'::jsonb,
     'RIESGO', ARRAY[2,3]::SMALLINT[], TRUE),

    -- ── Solo 3er ciclo: la lectura como herramienta ──
    ('c3_velocidad_edad',
     'Su velocidad y precisión al leer no corresponden a su edad.',
     8, ARRAY['fluidez'],
     'PRODISLEX 3er ciclo — la velocidad y precisión lectora no se '
     'corresponden con la edad cronológica. Nótese que el referente cambia: '
     'en 1er ciclo se compara contra el grupo clase. '
     'REVISAR peso: sin respaldo documentado',
     '[{"label":"Nunca","value":0},{"label":"A veces","value":0.5},{"label":"Frecuente","value":1}]'::jsonb,
     'RIESGO', ARRAY[3]::SMALLINT[], TRUE),

    ('c3_uso_para_aprender',
     'Le cuesta usar la lectura para estudiar: buscar en el diccionario, seguir un índice, aprender otra lengua.',
     8, ARRAY['lectura_instrumental'],
     'PRODISLEX 3er ciclo — automatizar el abecedario (uso del diccionario, '
     'índices) y mayor dificultad en el aprendizaje de lenguas. '
     'REVISAR peso: sin respaldo documentado',
     '[{"label":"Nunca","value":0},{"label":"A veces","value":0.5},{"label":"Frecuente","value":1}]'::jsonb,
     'RIESGO', ARRAY[3]::SMALLINT[], TRUE)
ON CONFLICT (item_code) DO NOTHING;

COMMIT;

-- ─── Verificación ────────────────────────────────────────────────────────────
--
--   SELECT c AS ciclo, count(*) FILTER (WHERE categoria='RIESGO') AS riesgo,
--          sum(weight) FILTER (WHERE categoria='RIESGO') AS peso
--     FROM assessment.teacher_screening_items, unnest(ciclos) c
--    WHERE is_active GROUP BY c ORDER BY c;
--
-- Los pesos ya no suman 100 en cada ciclo, y no hace falta:
-- calculate_teacher_score normaliza dividiendo por el peso total cuando no es
-- 100, así que cada ciclo se escala a 0-100 por su cuenta.
