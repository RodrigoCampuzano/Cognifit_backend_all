-- =============================================================
-- 005_seed_test_items.sql  (GENERADO por scripts/generate_test_items_seed.py)
-- Ítems de la batería para que la app los muestre y el alumno los responda.
-- Idempotente: borra y re-inserta los ítems marcados COGNIFIT_SEED_V1.
-- Ejecutar DESPUÉS de schema.sql, 002, 003 y 004.
-- =============================================================

DELETE FROM assessment.test_items WHERE source_instrument_code = 'COGNIFIT_SEED_V1';

-- M02_PHONOLOGICAL_AWARENESS (8 ítems)
WITH m AS (
  SELECT t.id AS test_id, t.module_id
  FROM assessment.tests t
  JOIN assessment.battery_modules bm ON bm.id = t.module_id
  WHERE bm.module_code = 'M02_PHONOLOGICAL_AWARENESS'
  ORDER BY t.created_at DESC LIMIT 1
)
INSERT INTO assessment.test_items
  (test_id, module_id, item_order, item_code, stimulus_text, expected_response,
   item_kind, difficulty, source_instrument_code, tags, is_practice)
SELECT m.test_id, m.module_id, v.ord, v.code, v.stim, v.expected, 'PHONOLOGICAL_AWARENESS', v.diff,
       'COGNIFIT_SEED_V1', ARRAY['seed','m02_phonological_awareness']::text[], FALSE
FROM m CROSS JOIN (VALUES
  (1, 'M02_001', 'sol', 'sol', 1),
  (2, 'M02_002', 'casa', 'casa', 1),
  (3, 'M02_003', 'mariposa', 'mariposa', 1),
  (4, 'M02_004', 'pan', 'pan', 1),
  (5, 'M02_005', 'luna', 'luna', 1),
  (6, 'M02_006', 'camino', 'camino', 1),
  (7, 'M02_007', 'rosa', 'rosa', 1),
  (8, 'M02_008', 'barco', 'barco', 1)
) AS v(ord, code, stim, expected, diff);

-- M03_LETTERS_SYLLABLES (49 ítems)
WITH m AS (
  SELECT t.id AS test_id, t.module_id
  FROM assessment.tests t
  JOIN assessment.battery_modules bm ON bm.id = t.module_id
  WHERE bm.module_code = 'M03_LETTERS_SYLLABLES'
  ORDER BY t.created_at DESC LIMIT 1
)
INSERT INTO assessment.test_items
  (test_id, module_id, item_order, item_code, stimulus_text, expected_response,
   item_kind, difficulty, source_instrument_code, tags, is_practice)
SELECT m.test_id, m.module_id, v.ord, v.code, v.stim, v.expected, 'LETTERS_SYLLABLES', v.diff,
       'COGNIFIT_SEED_V1', ARRAY['seed','m03_letters_syllables']::text[], FALSE
FROM m CROSS JOIN (VALUES
  (1, 'M03_001', 'b', 'b', 1),
  (2, 'M03_002', 'm', 'm', 1),
  (3, 'M03_003', 'c', 'c', 1),
  (4, 'M03_004', 'l', 'l', 1),
  (5, 'M03_005', 'a', 'a', 1),
  (6, 'M03_006', 'g', 'g', 1),
  (7, 'M03_007', 'd', 'd', 1),
  (8, 'M03_008', 'p', 'p', 1),
  (9, 'M03_009', 's', 's', 1),
  (10, 'M03_010', 'e', 'e', 1),
  (11, 'M03_011', 'ch', 'ch', 1),
  (12, 'M03_012', 'q', 'q', 1),
  (13, 'M03_013', 'ñ', 'ñ', 1),
  (14, 'M03_014', 'll', 'll', 1),
  (15, 'M03_015', 'r', 'r', 1),
  (16, 'M03_016', 't', 't', 1),
  (17, 'M03_017', 'j', 'j', 1),
  (18, 'M03_018', 'y', 'y', 1),
  (19, 'M03_019', 'v', 'v', 1),
  (20, 'M03_020', 'sa', 'sa', 1),
  (21, 'M03_021', 'te', 'te', 1),
  (22, 'M03_022', 'mo', 'mo', 1),
  (23, 'M03_023', 'lu', 'lu', 1),
  (24, 'M03_024', 'ri', 'ri', 1),
  (25, 'M03_025', 'fa', 'fa', 1),
  (26, 'M03_026', 'co', 'co', 1),
  (27, 'M03_027', 'ci', 'ci', 1),
  (28, 'M03_028', 'ga', 'ga', 1),
  (29, 'M03_029', 'ge', 'ge', 1),
  (30, 'M03_030', 'cu', 'cu', 1),
  (31, 'M03_031', 'gi', 'gi', 1),
  (32, 'M03_032', 'is', 'is', 1),
  (33, 'M03_033', 'ac', 'ac', 1),
  (34, 'M03_034', 'in', 'in', 1),
  (35, 'M03_035', 'em', 'em', 1),
  (36, 'M03_036', 'ul', 'ul', 1),
  (37, 'M03_037', 'ar', 'ar', 1),
  (38, 'M03_038', 'til', 'til', 1),
  (39, 'M03_039', 'pur', 'pur', 1),
  (40, 'M03_040', 'mos', 'mos', 1),
  (41, 'M03_041', 'cam', 'cam', 1),
  (42, 'M03_042', 'sec', 'sec', 1),
  (43, 'M03_043', 'lin', 'lin', 1),
  (44, 'M03_044', 'mia', 'mia', 1),
  (45, 'M03_045', 'tue', 'tue', 1),
  (46, 'M03_046', 'feu', 'feu', 1),
  (47, 'M03_047', 'rou', 'rou', 1),
  (48, 'M03_048', 'nio', 'nio', 1),
  (49, 'M03_049', 'pia', 'pia', 1)
) AS v(ord, code, stim, expected, diff);

-- M04_REAL_WORDS (12 ítems)
WITH m AS (
  SELECT t.id AS test_id, t.module_id
  FROM assessment.tests t
  JOIN assessment.battery_modules bm ON bm.id = t.module_id
  WHERE bm.module_code = 'M04_REAL_WORDS'
  ORDER BY t.created_at DESC LIMIT 1
)
INSERT INTO assessment.test_items
  (test_id, module_id, item_order, item_code, stimulus_text, expected_response,
   item_kind, difficulty, source_instrument_code, tags, is_practice)
SELECT m.test_id, m.module_id, v.ord, v.code, v.stim, v.expected, 'REAL_WORDS', v.diff,
       'COGNIFIT_SEED_V1', ARRAY['seed','m04_real_words']::text[], FALSE
FROM m CROSS JOIN (VALUES
  (1, 'M04_001', 'casa', 'casa', 2),
  (2, 'M04_002', 'perro', 'perro', 2),
  (3, 'M04_003', 'mesa', 'mesa', 2),
  (4, 'M04_004', 'sol', 'sol', 2),
  (5, 'M04_005', 'libro', 'libro', 2),
  (6, 'M04_006', 'ventana', 'ventana', 2),
  (7, 'M04_007', 'camino', 'camino', 2),
  (8, 'M04_008', 'mariposa', 'mariposa', 2),
  (9, 'M04_009', 'pelota', 'pelota', 2),
  (10, 'M04_010', 'escuela', 'escuela', 2),
  (11, 'M04_011', 'bicicleta', 'bicicleta', 2),
  (12, 'M04_012', 'tijeras', 'tijeras', 2)
) AS v(ord, code, stim, expected, diff);

-- M05_PSEUDOWORDS (24 ítems)
WITH m AS (
  SELECT t.id AS test_id, t.module_id
  FROM assessment.tests t
  JOIN assessment.battery_modules bm ON bm.id = t.module_id
  WHERE bm.module_code = 'M05_PSEUDOWORDS'
  ORDER BY t.created_at DESC LIMIT 1
)
INSERT INTO assessment.test_items
  (test_id, module_id, item_order, item_code, stimulus_text, expected_response,
   item_kind, difficulty, source_instrument_code, tags, is_practice)
SELECT m.test_id, m.module_id, v.ord, v.code, v.stim, v.expected, 'PSEUDOWORDS', v.diff,
       'COGNIFIT_SEED_V1', ARRAY['seed','m05_pseudowords']::text[], FALSE
FROM m CROSS JOIN (VALUES
  (1, 'M05_001', 'nomino', 'nomino', 3),
  (2, 'M05_002', 'ohnado', 'ohnado', 3),
  (3, 'M05_003', 'deste', 'deste', 3),
  (4, 'M05_004', 'alledo', 'alledo', 3),
  (5, 'M05_005', 'rechido', 'rechido', 3),
  (6, 'M05_006', 'chaquillo', 'chaquillo', 3),
  (7, 'M05_007', 'laqueta', 'laqueta', 3),
  (8, 'M05_008', 'sagueso', 'sagueso', 3),
  (9, 'M05_009', 'quiguifi', 'quiguifi', 3),
  (10, 'M05_010', 'ifjuti', 'ifjuti', 3),
  (11, 'M05_011', 'voyate', 'voyate', 3),
  (12, 'M05_012', 'quellimi', 'quellimi', 3),
  (13, 'M05_013', 'chado', 'chado', 3),
  (14, 'M05_014', 'deco', 'deco', 3),
  (15, 'M05_015', 'fido', 'fido', 3),
  (16, 'M05_016', 'llotio', 'llotio', 3),
  (17, 'M05_017', 'tarpo', 'tarpo', 3),
  (18, 'M05_018', 'gupa', 'gupa', 3),
  (19, 'M05_019', 'boso', 'boso', 3),
  (20, 'M05_020', 'jallón', 'jallón', 3),
  (21, 'M05_021', 'pola', 'pola', 3),
  (22, 'M05_022', 'querpo', 'querpo', 3),
  (23, 'M05_023', 'mite', 'mite', 3),
  (24, 'M05_024', 'ñuma', 'ñuma', 3)
) AS v(ord, code, stim, expected, diff);

-- M06_SMART_DICTATION (8 ítems)
WITH m AS (
  SELECT t.id AS test_id, t.module_id
  FROM assessment.tests t
  JOIN assessment.battery_modules bm ON bm.id = t.module_id
  WHERE bm.module_code = 'M06_SMART_DICTATION'
  ORDER BY t.created_at DESC LIMIT 1
)
INSERT INTO assessment.test_items
  (test_id, module_id, item_order, item_code, stimulus_text, expected_response,
   item_kind, difficulty, source_instrument_code, tags, is_practice)
SELECT m.test_id, m.module_id, v.ord, v.code, v.stim, v.expected, 'SMART_DICTATION', v.diff,
       'COGNIFIT_SEED_V1', ARRAY['seed','m06_smart_dictation']::text[], FALSE
FROM m CROSS JOIN (VALUES
  (1, 'M06_001', 'bota', 'bota', 3),
  (2, 'M06_002', 'queso', 'queso', 3),
  (3, 'M06_003', 'jirafa', 'jirafa', 3),
  (4, 'M06_004', 'guitarra', 'guitarra', 3),
  (5, 'M06_005', 'pingüino', 'pingüino', 3),
  (6, 'M06_006', 'cielo', 'cielo', 3),
  (7, 'M06_007', 'burbuja', 'burbuja', 3),
  (8, 'M06_008', 'chocolate', 'chocolate', 3)
) AS v(ord, code, stim, expected, diff);

-- M07_CONTROLLED_COPY (5 ítems)
WITH m AS (
  SELECT t.id AS test_id, t.module_id
  FROM assessment.tests t
  JOIN assessment.battery_modules bm ON bm.id = t.module_id
  WHERE bm.module_code = 'M07_CONTROLLED_COPY'
  ORDER BY t.created_at DESC LIMIT 1
)
INSERT INTO assessment.test_items
  (test_id, module_id, item_order, item_code, stimulus_text, expected_response,
   item_kind, difficulty, source_instrument_code, tags, is_practice)
SELECT m.test_id, m.module_id, v.ord, v.code, v.stim, v.expected, 'CONTROLLED_COPY', v.diff,
       'COGNIFIT_SEED_V1', ARRAY['seed','m07_controlled_copy']::text[], FALSE
FROM m CROSS JOIN (VALUES
  (1, 'M07_001', 'el gato duerme', 'el gato duerme', 1),
  (2, 'M07_002', 'la niña corre', 'la niña corre', 1),
  (3, 'M07_003', 'mi casa es azul', 'mi casa es azul', 1),
  (4, 'M07_004', 'vamos al parque', 'vamos al parque', 1),
  (5, 'M07_005', 'hoy hace sol', 'hoy hace sol', 1)
) AS v(ord, code, stim, expected, diff);

-- M08_RAPID_NAMING (12 ítems)
WITH m AS (
  SELECT t.id AS test_id, t.module_id
  FROM assessment.tests t
  JOIN assessment.battery_modules bm ON bm.id = t.module_id
  WHERE bm.module_code = 'M08_RAPID_NAMING'
  ORDER BY t.created_at DESC LIMIT 1
)
INSERT INTO assessment.test_items
  (test_id, module_id, item_order, item_code, stimulus_text, expected_response,
   item_kind, difficulty, source_instrument_code, tags, is_practice)
SELECT m.test_id, m.module_id, v.ord, v.code, v.stim, v.expected, 'RAPID_NAMING', v.diff,
       'COGNIFIT_SEED_V1', ARRAY['seed','m08_rapid_naming']::text[], FALSE
FROM m CROSS JOIN (VALUES
  (1, 'M08_001', 'rojo', 'rojo', 1),
  (2, 'M08_002', 'azul', 'azul', 1),
  (3, 'M08_003', 'verde', 'verde', 1),
  (4, 'M08_004', 'amarillo', 'amarillo', 1),
  (5, 'M08_005', 'negro', 'negro', 1),
  (6, 'M08_006', 'blanco', 'blanco', 1),
  (7, 'M08_007', 'casa', 'casa', 1),
  (8, 'M08_008', 'sol', 'sol', 1),
  (9, 'M08_009', 'luna', 'luna', 1),
  (10, 'M08_010', 'mesa', 'mesa', 1),
  (11, 'M08_011', 'silla', 'silla', 1),
  (12, 'M08_012', 'vaso', 'vaso', 1)
) AS v(ord, code, stim, expected, diff);

-- M09_READING_COMPREHENSION (2 ítems)
WITH m AS (
  SELECT t.id AS test_id, t.module_id
  FROM assessment.tests t
  JOIN assessment.battery_modules bm ON bm.id = t.module_id
  WHERE bm.module_code = 'M09_READING_COMPREHENSION'
  ORDER BY t.created_at DESC LIMIT 1
)
INSERT INTO assessment.test_items
  (test_id, module_id, item_order, item_code, stimulus_text, expected_response,
   item_kind, difficulty, source_instrument_code, tags, is_practice)
SELECT m.test_id, m.module_id, v.ord, v.code, v.stim, v.expected, 'READING_COMPREHENSION', v.diff,
       'COGNIFIT_SEED_V1', ARRAY['seed','m09_reading_comprehension']::text[], FALSE
FROM m CROSS JOIN (VALUES
  (1, 'M09_001', 'El perro de Ana es café. Le gusta correr en el parque por las tardes.', 'El perro de Ana es café. Le gusta correr en el parque por las tardes.', 3),
  (2, 'M09_002', 'Pedro tiene una bicicleta roja. Todos los días va a la escuela en ella.', 'Pedro tiene una bicicleta roja. Todos los días va a la escuela en ella.', 3)
) AS v(ord, code, stim, expected, diff);

-- Verificación rápida:
--   SELECT bm.module_code, count(*) FROM assessment.test_items ti
--   JOIN assessment.battery_modules bm ON bm.id=ti.module_id GROUP BY 1 ORDER BY 1;
