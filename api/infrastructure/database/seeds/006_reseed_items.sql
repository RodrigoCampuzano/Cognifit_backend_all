-- =============================================================
-- 006_reseed_items.sql
-- Re-seed idempotente de ítems de batería (versión V2).
-- Limpia V1 y V2 antes de re-insertar, por si 005 tuvo errores.
-- Cubre M02–M09 con ítems alineados al content pack y TEDE/PROLEXIA.
-- =============================================================

DELETE FROM assessment.test_items
 WHERE source_instrument_code IN ('COGNIFIT_SEED_V1', 'COGNIFIT_SEED_V2');

-- ─── M02 CONCIENCIA FONOLÓGICA (16 ítems) ───────────────────────────────────
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
SELECT m.test_id, m.module_id, v.ord, v.code, v.stim, v.expected,
       'PHONOLOGICAL_AWARENESS', v.diff,
       'COGNIFIT_SEED_V2', ARRAY['seed','m02_phonological_awareness']::text[], v.practice
FROM m CROSS JOIN (VALUES
  (1,  'M02_P01', '¿Cuántas sílabas tiene "casa"?',         '2', 1, TRUE),
  (2,  'M02_001', '¿Cuántas sílabas tiene "mariposa"?',     '4', 1, FALSE),
  (3,  'M02_002', '¿Cuántas sílabas tiene "sol"?',          '1', 1, FALSE),
  (4,  'M02_003', '¿Cuántas sílabas tiene "camino"?',       '3', 1, FALSE),
  (5,  'M02_004', 'Di la primera sílaba de "pelota".',       'pe', 1, FALSE),
  (6,  'M02_005', 'Di la primera sílaba de "barco".',        'bar', 1, FALSE),
  (7,  'M02_006', 'Di la última sílaba de "mesa".',          'sa', 1, FALSE),
  (8,  'M02_007', '¿"sol" y "col" riman?',                  'sí', 1, FALSE),
  (9,  'M02_008', '¿"luna" y "casa" riman?',                'no', 1, FALSE),
  (10, 'M02_009', 'Omite la primera sílaba de "bota".',     'ta', 2, FALSE),
  (11, 'M02_010', 'Omite la primera sílaba de "camisa".',   'misa', 2, FALSE),
  (12, 'M02_011', 'Di "luna" al revés por sílabas.',        'nalu', 2, FALSE),
  (13, 'M02_012', '¿Cuál es el primer sonido de "faro"?',   'f', 2, FALSE),
  (14, 'M02_013', '¿Cuál es el último sonido de "pan"?',    'n', 2, FALSE),
  (15, 'M02_014', 'Sustituye la /p/ de "pato" por /g/.',    'gato', 3, FALSE),
  (16, 'M02_015', 'Sustituye la /m/ de "mesa" por /b/.',    'besa', 3, FALSE)
) AS v(ord, code, stim, expected, diff, practice);

-- ─── M03 LETRAS Y SÍLABAS — TEDE/PROLEXIA (49 ítems) ───────────────────────
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
SELECT m.test_id, m.module_id, v.ord, v.code, v.stim, v.expected,
       'LETTERS_SYLLABLES', v.diff,
       'COGNIFIT_SEED_V2', ARRAY['seed','m03_letters_syllables']::text[], FALSE
FROM m CROSS JOIN (VALUES
  -- letras individuales (nombre de letra)
  (1,  'M03_001', 'b',   'b',   1),
  (2,  'M03_002', 'm',   'm',   1),
  (3,  'M03_003', 'c',   'c',   1),
  (4,  'M03_004', 'l',   'l',   1),
  (5,  'M03_005', 'a',   'a',   1),
  (6,  'M03_006', 'g',   'g',   1),
  (7,  'M03_007', 'd',   'd',   1),
  (8,  'M03_008', 'p',   'p',   1),
  (9,  'M03_009', 's',   's',   1),
  (10, 'M03_010', 'e',   'e',   1),
  (11, 'M03_011', 'ch',  'ch',  1),
  (12, 'M03_012', 'q',   'q',   1),
  (13, 'M03_013', 'ñ',   'ñ',   1),
  (14, 'M03_014', 'll',  'll',  1),
  (15, 'M03_015', 'r',   'r',   1),
  (16, 'M03_016', 't',   't',   1),
  (17, 'M03_017', 'j',   'j',   1),
  (18, 'M03_018', 'y',   'y',   1),
  (19, 'M03_019', 'v',   'v',   1),
  -- sílabas directas simples
  (20, 'M03_020', 'sa',  'sa',  1),
  (21, 'M03_021', 'te',  'te',  1),
  (22, 'M03_022', 'mo',  'mo',  1),
  (23, 'M03_023', 'lu',  'lu',  1),
  (24, 'M03_024', 'ri',  'ri',  1),
  (25, 'M03_025', 'fa',  'fa',  1),
  -- sílabas directas con doble sonido (c/g+e/i)
  (26, 'M03_026', 'co',  'co',  1),
  (27, 'M03_027', 'ci',  'ci',  1),
  (28, 'M03_028', 'ga',  'ga',  1),
  (29, 'M03_029', 'ge',  'ge',  1),
  -- sílabas con u muda
  (30, 'M03_030', 'gue', 'gue', 2),
  (31, 'M03_031', 'qui', 'qui', 2),
  (32, 'M03_032', 'cu',  'cu',  1),
  (33, 'M03_033', 'gi',  'gi',  1),
  -- sílabas indirectas
  (34, 'M03_034', 'is',  'is',  2),
  (35, 'M03_035', 'ac',  'ac',  2),
  (36, 'M03_036', 'in',  'in',  2),
  (37, 'M03_037', 'em',  'em',  2),
  (38, 'M03_038', 'ul',  'ul',  2),
  (39, 'M03_039', 'ar',  'ar',  2),
  -- sílabas complejas (CVC)
  (40, 'M03_040', 'til', 'til', 2),
  (41, 'M03_041', 'pur', 'pur', 2),
  (42, 'M03_042', 'mos', 'mos', 2),
  (43, 'M03_043', 'cam', 'cam', 2),
  (44, 'M03_044', 'sec', 'sec', 2),
  (45, 'M03_045', 'lin', 'lin', 2),
  -- diptongos
  (46, 'M03_046', 'mia', 'mia', 2),
  (47, 'M03_047', 'tue', 'tue', 2),
  (48, 'M03_048', 'feu', 'feu', 3),
  -- fonogramas complejos
  (49, 'M03_049', 'bra', 'bra', 3)
) AS v(ord, code, stim, expected, diff);

-- ─── M04 PALABRAS REALES — TEDE (20 ítems) ──────────────────────────────────
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
SELECT m.test_id, m.module_id, v.ord, v.code, v.stim, v.expected,
       'REAL_WORDS', v.diff,
       'COGNIFIT_SEED_V2', ARRAY['seed','m04_real_words']::text[], FALSE
FROM m CROSS JOIN (VALUES
  (1,  'M04_001', 'sol',        'sol',        1),
  (2,  'M04_002', 'pan',        'pan',        1),
  (3,  'M04_003', 'casa',       'casa',       1),
  (4,  'M04_004', 'mesa',       'mesa',       1),
  (5,  'M04_005', 'perro',      'perro',      1),
  (6,  'M04_006', 'libro',      'libro',      2),
  (7,  'M04_007', 'ventana',    'ventana',    2),
  (8,  'M04_008', 'camino',     'camino',     2),
  (9,  'M04_009', 'mariposa',   'mariposa',   2),
  (10, 'M04_010', 'pelota',     'pelota',     2),
  (11, 'M04_011', 'escuela',    'escuela',    2),
  (12, 'M04_012', 'bicicleta',  'bicicleta',  2),
  (13, 'M04_013', 'tijeras',    'tijeras',    2),
  (14, 'M04_014', 'paraguas',   'paraguas',   3),
  (15, 'M04_015', 'murciélago', 'murciélago', 3),
  (16, 'M04_016', 'helicóptero','helicóptero',3),
  (17, 'M04_017', 'dragón',     'dragón',     3),
  (18, 'M04_018', 'cohete',     'cohete',     3),
  (19, 'M04_019', 'jirafas',    'jirafas',    3),
  (20, 'M04_020', 'estrella',   'estrella',   2)
) AS v(ord, code, stim, expected, diff);

-- ─── M05 PSEUDOPALABRAS — PROLEXIA/TEDE (24 ítems) ─────────────────────────
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
SELECT m.test_id, m.module_id, v.ord, v.code, v.stim, v.expected,
       'PSEUDOWORDS', v.diff,
       'COGNIFIT_SEED_V2', ARRAY['seed','m05_pseudowords']::text[], FALSE
FROM m CROSS JOIN (VALUES
  -- confundibles grafía
  (1,  'M05_001', 'nomino',    'nomino',    2),
  (2,  'M05_002', 'ohnado',    'ohnado',    2),
  (3,  'M05_003', 'deste',     'deste',     2),
  (4,  'M05_004', 'alledo',    'alledo',    3),
  (5,  'M05_005', 'rechido',   'rechido',   3),
  -- confundibles sonido
  (6,  'M05_006', 'chaquillo', 'chaquillo', 3),
  (7,  'M05_007', 'laqueta',   'laqueta',   3),
  (8,  'M05_008', 'sagueso',   'sagueso',   3),
  (9,  'M05_009', 'quiguifi',  'quiguifi',  3),
  (10, 'M05_010', 'ifjuti',    'ifjuti',    3),
  -- inversiones letras
  (11, 'M05_011', 'voyate',    'voyate',    2),
  (12, 'M05_012', 'quellimi',  'quellimi',  3),
  (13, 'M05_013', 'chado',     'chado',     2),
  (14, 'M05_014', 'deco',      'deco',      2),
  -- grafia semejante
  (15, 'M05_015', 'fido',      'fido',      2),
  (16, 'M05_016', 'llotio',    'llotio',    3),
  (17, 'M05_017', 'tarpo',     'tarpo',     2),
  (18, 'M05_018', 'gupa',      'gupa',      2),
  (19, 'M05_019', 'boso',      'boso',      2),
  (20, 'M05_020', 'jallón',    'jallón',    3),
  (21, 'M05_021', 'pola',      'pola',      2),
  (22, 'M05_022', 'querpo',    'querpo',    3),
  (23, 'M05_023', 'mite',      'mite',      2),
  (24, 'M05_024', 'ñuma',      'ñuma',      3)
) AS v(ord, code, stim, expected, diff);

-- ─── M06 DICTADO INTELIGENTE (12 ítems — el stim es lo que se dicta) ────────
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
SELECT m.test_id, m.module_id, v.ord, v.code, v.stim, v.expected,
       'SMART_DICTATION', v.diff,
       'COGNIFIT_SEED_V2', ARRAY['seed','m06_smart_dictation']::text[], v.practice
FROM m CROSS JOIN (VALUES
  (1,  'M06_P01', 'sol',       'sol',       1, TRUE),
  (2,  'M06_001', 'bota',      'bota',      2, FALSE),
  (3,  'M06_002', 'queso',     'queso',     2, FALSE),
  (4,  'M06_003', 'jirafa',    'jirafa',    2, FALSE),
  (5,  'M06_004', 'guitarra',  'guitarra',  3, FALSE),
  (6,  'M06_005', 'pingüino',  'pingüino',  3, FALSE),
  (7,  'M06_006', 'cielo',     'cielo',     2, FALSE),
  (8,  'M06_007', 'burbuja',   'burbuja',   3, FALSE),
  (9,  'M06_008', 'chocolate', 'chocolate', 3, FALSE),
  (10, 'M06_009', 'lluvia',    'lluvia',    3, FALSE),
  (11, 'M06_010', 'huella',    'huella',    3, FALSE),
  (12, 'M06_011', 'vacuna',    'vacuna',    2, FALSE)
) AS v(ord, code, stim, expected, diff, practice);

-- ─── M07 COPIA CONTROLADA (8 ítems) ─────────────────────────────────────────
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
SELECT m.test_id, m.module_id, v.ord, v.code, v.stim, v.expected,
       'CONTROLLED_COPY', v.diff,
       'COGNIFIT_SEED_V2', ARRAY['seed','m07_controlled_copy']::text[], FALSE
FROM m CROSS JOIN (VALUES
  (1, 'M07_001', 'el gato duerme',         'el gato duerme',         1),
  (2, 'M07_002', 'la niña corre',           'la niña corre',           1),
  (3, 'M07_003', 'mi casa es azul',         'mi casa es azul',         1),
  (4, 'M07_004', 'vamos al parque',         'vamos al parque',         2),
  (5, 'M07_005', 'hoy hace sol y viento',   'hoy hace sol y viento',   2),
  (6, 'M07_006', 'el perro jugaba con Ana', 'el perro jugaba con Ana', 2),
  (7, 'M07_007', 'mi mamá compró jirafas',  'mi mamá compró jirafas',  3),
  (8, 'M07_008', 'llueve sobre la ciudad',  'llueve sobre la ciudad',  3)
) AS v(ord, code, stim, expected, diff);

-- ─── M08 DENOMINACIÓN RÁPIDA (18 ítems — colores y objetos RAN) ─────────────
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
SELECT m.test_id, m.module_id, v.ord, v.code, v.stim, v.expected,
       'RAPID_NAMING', v.diff,
       'COGNIFIT_SEED_V2', ARRAY['seed','m08_rapid_naming']::text[], FALSE
FROM m CROSS JOIN (VALUES
  -- colores (RAN colores)
  (1,  'M08_001', 'rojo',     'rojo',     1),
  (2,  'M08_002', 'azul',     'azul',     1),
  (3,  'M08_003', 'verde',    'verde',    1),
  (4,  'M08_004', 'amarillo', 'amarillo', 1),
  (5,  'M08_005', 'negro',    'negro',    1),
  (6,  'M08_006', 'blanco',   'blanco',   1),
  (7,  'M08_007', 'naranja',  'naranja',  1),
  (8,  'M08_008', 'morado',   'morado',   1),
  (9,  'M08_009', 'rosa',     'rosa',     1),
  -- objetos (RAN objetos)
  (10, 'M08_010', 'casa',     'casa',     1),
  (11, 'M08_011', 'sol',      'sol',      1),
  (12, 'M08_012', 'luna',     'luna',     1),
  (13, 'M08_013', 'mesa',     'mesa',     1),
  (14, 'M08_014', 'silla',    'silla',    1),
  (15, 'M08_015', 'vaso',     'vaso',     1),
  (16, 'M08_016', 'perro',    'perro',    1),
  (17, 'M08_017', 'árbol',    'árbol',    1),
  (18, 'M08_018', 'libro',    'libro',    1)
) AS v(ord, code, stim, expected, diff);

-- ─── M09 COMPRENSIÓN LECTORA (8 ítems — texto + preguntas literales e inferenciales) ─
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
SELECT m.test_id, m.module_id, v.ord, v.code, v.stim, v.expected,
       'READING_COMPREHENSION', v.diff,
       'COGNIFIT_SEED_V2', ARRAY['seed','m09_reading_comprehension']::text[], FALSE
FROM m CROSS JOIN (VALUES
  -- Texto 1: Ana y su perro (preguntas literales)
  (1, 'M09_001',
   'Lee: "Ana tiene un perro café que se llama Canelo. A Canelo le gusta correr en el parque. Todos los días Ana lo saca a pasear por las tardes." — ¿Cómo se llama el perro de Ana?',
   'Canelo', 2),
  (2, 'M09_002',
   '¿De qué color es el perro de Ana?',
   'café', 2),
  (3, 'M09_003',
   '¿Cuándo saca Ana a su perro de paseo?',
   'por las tardes', 2),
  -- Texto 1: preguntas inferenciales
  (4, 'M09_004',
   '¿Por qué crees que Ana saca a Canelo al parque?',
   'le gusta correr', 3),
  -- Texto 2: Pedro y su bicicleta
  (5, 'M09_005',
   'Lee: "Pedro tiene una bicicleta roja. Todos los días va a la escuela en ella. Un día su bicicleta se ponchó y Pedro tuvo que caminar." — ¿De qué color es la bicicleta de Pedro?',
   'roja', 2),
  (6, 'M09_006',
   '¿Cómo va Pedro a la escuela normalmente?',
   'en bicicleta', 2),
  (7, 'M09_007',
   '¿Qué pasó un día con la bicicleta de Pedro?',
   'se ponchó', 2),
  (8, 'M09_008',
   '¿Cómo llegó Pedro a la escuela el día que se ponchó su bicicleta?',
   'caminando', 3)
) AS v(ord, code, stim, expected, diff);

-- Verificación rápida (comentada para referencia):
-- SELECT bm.module_code, count(*) AS items
-- FROM assessment.test_items ti
-- JOIN assessment.battery_modules bm ON bm.id = ti.module_id
-- GROUP BY 1 ORDER BY 1;
