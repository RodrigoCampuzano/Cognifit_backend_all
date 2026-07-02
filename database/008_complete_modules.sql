-- =============================================================
-- 008_complete_modules.sql
-- Completa los módulos M02, M04, M06, M07, M09 con ítems bien
-- estructurados (práctica + progresión diff 1→3) y añade ítems
-- de práctica a M03, M05 y M08.
-- Idempotente: puede ejecutarse más de una vez.
-- =============================================================

-- Limpiar módulos a reemplazar (cualquier fuente)
DELETE FROM assessment.test_items ti
 WHERE ti.module_id IN (
   SELECT bm.id FROM assessment.battery_modules bm
   WHERE bm.module_code IN (
     'M02_PHONOLOGICAL_AWARENESS',
     'M04_REAL_WORDS',
     'M06_SMART_DICTATION',
     'M07_CONTROLLED_COPY',
     'M09_READING_COMPREHENSION'
   )
 );

-- Limpiar práctica previa de M03, M05 y M08 para re-insertar limpio
DELETE FROM assessment.test_items ti
 WHERE ti.is_practice = TRUE
   AND ti.source_instrument_code = 'COGNIFIT_SEED_V3'
   AND ti.module_id IN (
     SELECT bm.id FROM assessment.battery_modules bm
     WHERE bm.module_code IN (
       'M03_LETTERS_SYLLABLES',
       'M05_PSEUDOWORDS',
       'M08_RAPID_NAMING'
     )
   );

-- ─── M02 CONCIENCIA FONOLÓGICA — 17 ítems (1 práctica + 16) ─────────────────
WITH m AS (
  SELECT t.id AS test_id, t.module_id FROM assessment.tests t
  JOIN assessment.battery_modules bm ON bm.id = t.module_id
  WHERE bm.module_code = 'M02_PHONOLOGICAL_AWARENESS'
  ORDER BY t.created_at DESC LIMIT 1
)
INSERT INTO assessment.test_items
  (test_id, module_id, item_order, item_code, stimulus_text, expected_response,
   item_kind, difficulty, source_instrument_code, tags, is_practice)
SELECT m.test_id, m.module_id, v.ord, v.code, v.stim, v.expected,
       'PHONOLOGICAL_AWARENESS', v.diff, 'COGNIFIT_SEED_V3',
       ARRAY['m02','conciencia_fonologica']::text[], v.practice
FROM m CROSS JOIN (VALUES
  -- práctica
  (0,  'M02_P01', '¿Cuántas sílabas tiene "sol"?',                 '1',    1, TRUE),
  -- nivel 1 — conteo de sílabas y rima básica
  (1,  'M02_001', '¿Cuántas sílabas tiene "mesa"?',                '2',    1, FALSE),
  (2,  'M02_002', '¿Cuántas sílabas tiene "camino"?',              '3',    1, FALSE),
  (3,  'M02_003', '¿Cuántas sílabas tiene "mariposa"?',            '4',    1, FALSE),
  (4,  'M02_004', '¿Cuántas sílabas tiene "pan"?',                 '1',    1, FALSE),
  (5,  'M02_005', '¿"sol" y "col" riman?',                         'sí',   1, FALSE),
  (6,  'M02_006', '¿"luna" y "mesa" riman?',                       'no',   1, FALSE),
  (7,  'M02_007', '¿"gato" y "pato" riman?',                       'sí',   1, FALSE),
  -- nivel 2 — identificación y omisión de sílabas, fonema inicial/final
  (8,  'M02_008', 'Di la primera sílaba de "pelota".',              'pe',   2, FALSE),
  (9,  'M02_009', 'Di la primera sílaba de "barco".',               'bar',  2, FALSE),
  (10, 'M02_010', 'Di la última sílaba de "ventana".',              'na',   2, FALSE),
  (11, 'M02_011', 'Di "camisa" sin la primera sílaba.',             'misa', 2, FALSE),
  (12, 'M02_012', '¿Cuál es el primer sonido de "faro"?',           'f',    2, FALSE),
  (13, 'M02_013', '¿Cuál es el último sonido de "pan"?',            'n',    2, FALSE),
  -- nivel 3 — manipulación de fonemas y reversión
  (14, 'M02_014', 'Di "luna" al revés sílaba por sílaba.',          'nalu', 3, FALSE),
  (15, 'M02_015', 'Sustituye la /p/ de "pato" por /g/.',            'gato', 3, FALSE),
  (16, 'M02_016', 'Sustituye la /m/ de "mesa" por /b/.',            'besa', 3, FALSE),
  (17, 'M02_017', 'Di "ventana" sin la primera sílaba.',            'tana', 3, FALSE)
) AS v(ord, code, stim, expected, diff, practice);

-- ─── M04 PALABRAS REALES — 21 ítems (1 práctica + 20) ───────────────────────
WITH m AS (
  SELECT t.id AS test_id, t.module_id FROM assessment.tests t
  JOIN assessment.battery_modules bm ON bm.id = t.module_id
  WHERE bm.module_code = 'M04_REAL_WORDS'
  ORDER BY t.created_at DESC LIMIT 1
)
INSERT INTO assessment.test_items
  (test_id, module_id, item_order, item_code, stimulus_text, expected_response,
   item_kind, difficulty, source_instrument_code, tags, is_practice)
SELECT m.test_id, m.module_id, v.ord, v.code, v.stim, v.stim,
       'REAL_WORDS', v.diff, 'COGNIFIT_SEED_V3',
       ARRAY['m04','palabras_reales']::text[], v.practice
FROM m CROSS JOIN (VALUES
  -- práctica
  (0,  'M04_P01', 'gato',        1, TRUE),
  -- nivel 1 — monosílabas y palabras muy cortas comunes
  (1,  'M04_001', 'sol',         1, FALSE),
  (2,  'M04_002', 'pan',         1, FALSE),
  (3,  'M04_003', 'luz',         1, FALSE),
  (4,  'M04_004', 'mar',         1, FALSE),
  (5,  'M04_005', 'pie',         1, FALSE),
  (6,  'M04_006', 'flor',        1, FALSE),
  -- nivel 2 — palabras bisílabas y trisílabas comunes
  (7,  'M04_007', 'casa',        2, FALSE),
  (8,  'M04_008', 'mesa',        2, FALSE),
  (9,  'M04_009', 'perro',       2, FALSE),
  (10, 'M04_010', 'libro',       2, FALSE),
  (11, 'M04_011', 'camino',      2, FALSE),
  (12, 'M04_012', 'pelota',      2, FALSE),
  (13, 'M04_013', 'ventana',     2, FALSE),
  (14, 'M04_014', 'escuela',     2, FALSE),
  -- nivel 3 — polisílabas, acentos, grupos consonánticos complejos
  (15, 'M04_015', 'dragón',      3, FALSE),
  (16, 'M04_016', 'paraguas',    3, FALSE),
  (17, 'M04_017', 'murciélago',  3, FALSE),
  (18, 'M04_018', 'helicóptero', 3, FALSE),
  (19, 'M04_019', 'bicicleta',   3, FALSE),
  (20, 'M04_020', 'mariposa',    3, FALSE)
) AS v(ord, code, stim, diff, practice);

-- ─── M06 DICTADO INTELIGENTE — 13 ítems (1 práctica + 12) ───────────────────
-- El examinador dicta la palabra; el niño la escribe/deletrea en voz alta.
-- stimulus_text = lo que se dicta; expected_response = escritura correcta.
WITH m AS (
  SELECT t.id AS test_id, t.module_id FROM assessment.tests t
  JOIN assessment.battery_modules bm ON bm.id = t.module_id
  WHERE bm.module_code = 'M06_SMART_DICTATION'
  ORDER BY t.created_at DESC LIMIT 1
)
INSERT INTO assessment.test_items
  (test_id, module_id, item_order, item_code, stimulus_text, expected_response,
   item_kind, difficulty, source_instrument_code, tags, is_practice)
SELECT m.test_id, m.module_id, v.ord, v.code, v.stim, v.stim,
       'SMART_DICTATION', v.diff, 'COGNIFIT_SEED_V3',
       ARRAY['m06','dictado']::text[], v.practice
FROM m CROSS JOIN (VALUES
  -- práctica
  (0,  'M06_P01', 'sol',       1, TRUE),
  -- nivel 1 — fonética directa, sin reglas ortográficas complejas
  (1,  'M06_001', 'pan',       1, FALSE),
  (2,  'M06_002', 'mesa',      1, FALSE),
  (3,  'M06_003', 'pato',      1, FALSE),
  -- nivel 2 — reglas ortográficas: b/v, h, j/c/q
  (4,  'M06_004', 'vaca',      2, FALSE),
  (5,  'M06_005', 'bota',      2, FALSE),
  (6,  'M06_006', 'hoja',      2, FALSE),
  (7,  'M06_007', 'jirafa',    2, FALSE),
  (8,  'M06_008', 'cielo',     2, FALSE),
  (9,  'M06_009', 'queso',     2, FALSE),
  -- nivel 3 — grupos complejos: gu/gü, ll/y, rr, tilde
  (10, 'M06_010', 'guitarra',  3, FALSE),
  (11, 'M06_011', 'pingüino',  3, FALSE),
  (12, 'M06_012', 'lluvia',    3, FALSE)
) AS v(ord, code, stim, diff, practice);

-- ─── M07 COPIA CONTROLADA — 9 ítems (1 práctica + 8) ────────────────────────
-- El niño ve la frase brevemente y la reproduce de memoria.
WITH m AS (
  SELECT t.id AS test_id, t.module_id FROM assessment.tests t
  JOIN assessment.battery_modules bm ON bm.id = t.module_id
  WHERE bm.module_code = 'M07_CONTROLLED_COPY'
  ORDER BY t.created_at DESC LIMIT 1
)
INSERT INTO assessment.test_items
  (test_id, module_id, item_order, item_code, stimulus_text, expected_response,
   item_kind, difficulty, source_instrument_code, tags, is_practice)
SELECT m.test_id, m.module_id, v.ord, v.code, v.stim, v.stim,
       'CONTROLLED_COPY', v.diff, 'COGNIFIT_SEED_V3',
       ARRAY['m07','copia_controlada']::text[], v.practice
FROM m CROSS JOIN (VALUES
  -- práctica
  (0, 'M07_P01', 'el sol',                                    1, TRUE),
  -- nivel 1 — frases de 3-4 palabras
  (1, 'M07_001', 'el gato duerme',                            1, FALSE),
  (2, 'M07_002', 'la niña corre',                             1, FALSE),
  (3, 'M07_003', 'mi casa es azul',                           1, FALSE),
  -- nivel 2 — frases de 5-6 palabras con mayor carga ortográfica
  (4, 'M07_004', 'vamos al parque hoy',                       2, FALSE),
  (5, 'M07_005', 'hoy hace sol y viento',                     2, FALSE),
  (6, 'M07_006', 'el perro jugaba con Ana',                   2, FALSE),
  -- nivel 3 — frases largas con tildes y palabras complejas
  (7, 'M07_007', 'mi mamá compró jirafas en el zoológico',    3, FALSE),
  (8, 'M07_008', 'llueve sobre la ciudad gris de madrugada',  3, FALSE)
) AS v(ord, code, stim, diff, practice);

-- ─── M09 COMPRENSIÓN LECTORA — 9 ítems (1 práctica + 8) ─────────────────────
-- El texto se presenta en el primer ítem del bloque; las preguntas
-- siguientes lo dan por leído (la app mantiene el texto visible).
WITH m AS (
  SELECT t.id AS test_id, t.module_id FROM assessment.tests t
  JOIN assessment.battery_modules bm ON bm.id = t.module_id
  WHERE bm.module_code = 'M09_READING_COMPREHENSION'
  ORDER BY t.created_at DESC LIMIT 1
)
INSERT INTO assessment.test_items
  (test_id, module_id, item_order, item_code, stimulus_text, expected_response,
   item_kind, difficulty, source_instrument_code, tags, is_practice)
SELECT m.test_id, m.module_id, v.ord, v.code, v.stim, v.expected,
       'READING_COMPREHENSION', v.diff, 'COGNIFIT_SEED_V3',
       v.tags::text[], v.practice
FROM m CROSS JOIN (VALUES
  -- práctica
  (0, 'M09_P01',
   'Lee: "El sol brilla en el cielo azul." — ¿Qué brilla?',
   'el sol', 1, ARRAY['m09','practica','literal'], TRUE),
  -- ── Texto 1: Ana y su perro Canelo ──────────────────────────────────────
  (1, 'M09_001',
   'Lee: "Ana tiene un perro café que se llama Canelo. A Canelo le gusta correr en el parque. Todos los días Ana lo saca a pasear por las tardes." — ¿Cómo se llama el perro de Ana?',
   'Canelo', 2, ARRAY['m09','literal','texto1'], FALSE),
  (2, 'M09_002',
   '¿De qué color es el perro de Ana?',
   'café', 2, ARRAY['m09','literal','texto1'], FALSE),
  (3, 'M09_003',
   '¿Cuándo saca Ana a pasear a su perro?',
   'por las tardes', 2, ARRAY['m09','literal','texto1'], FALSE),
  (4, 'M09_004',
   '¿Por qué crees que Ana lleva a Canelo al parque?',
   'le gusta correr', 3, ARRAY['m09','inferencial','texto1'], FALSE),
  -- ── Texto 2: Pedro y su bicicleta ───────────────────────────────────────
  (5, 'M09_005',
   'Lee: "Pedro tiene una bicicleta roja. Todos los días va a la escuela en ella. Un día la bicicleta se ponchó y Pedro tuvo que caminar." — ¿De qué color es la bicicleta de Pedro?',
   'roja', 2, ARRAY['m09','literal','texto2'], FALSE),
  (6, 'M09_006',
   '¿Cómo va Pedro normalmente a la escuela?',
   'en bicicleta', 2, ARRAY['m09','literal','texto2'], FALSE),
  (7, 'M09_007',
   '¿Qué le pasó a la bicicleta de Pedro un día?',
   'se ponchó', 2, ARRAY['m09','literal','texto2'], FALSE),
  (8, 'M09_008',
   '¿Cómo llegó Pedro a la escuela el día que se ponchó la bicicleta?',
   'caminando', 3, ARRAY['m09','inferencial','texto2'], FALSE)
) AS v(ord, code, stim, expected, diff, tags, practice);

-- ─── PRÁCTICA para M03, M05 y M08 (un ítem por módulo) ──────────────────────
-- M03: letra de calentamiento antes del TEDE Nivel Lector
WITH m AS (
  SELECT t.id AS test_id, t.module_id FROM assessment.tests t
  JOIN assessment.battery_modules bm ON bm.id = t.module_id
  WHERE bm.module_code = 'M03_LETTERS_SYLLABLES'
  ORDER BY t.created_at DESC LIMIT 1
)
INSERT INTO assessment.test_items
  (test_id, module_id, item_order, item_code, stimulus_text, expected_response,
   item_kind, difficulty, source_instrument_code, tags, is_practice)
SELECT m.test_id, m.module_id, 0, 'M03_P01', 'o', 'o',
       'LETTERS_SYLLABLES', 1, 'COGNIFIT_SEED_V3',
       ARRAY['m03','practica']::text[], TRUE
FROM m;

-- M05: pseudopalabra simple de calentamiento antes del TEDE Errores Específicos
WITH m AS (
  SELECT t.id AS test_id, t.module_id FROM assessment.tests t
  JOIN assessment.battery_modules bm ON bm.id = t.module_id
  WHERE bm.module_code = 'M05_PSEUDOWORDS'
  ORDER BY t.created_at DESC LIMIT 1
)
INSERT INTO assessment.test_items
  (test_id, module_id, item_order, item_code, stimulus_text, expected_response,
   item_kind, difficulty, source_instrument_code, tags, is_practice)
SELECT m.test_id, m.module_id, 0, 'M05_P01', 'tamo', 'tamo',
       'PSEUDOWORDS', 1, 'COGNIFIT_SEED_V3',
       ARRAY['m05','practica']::text[], TRUE
FROM m;

-- M08: color simple de calentamiento antes de la denominación rápida
WITH m AS (
  SELECT t.id AS test_id, t.module_id FROM assessment.tests t
  JOIN assessment.battery_modules bm ON bm.id = t.module_id
  WHERE bm.module_code = 'M08_RAPID_NAMING'
  ORDER BY t.created_at DESC LIMIT 1
)
INSERT INTO assessment.test_items
  (test_id, module_id, item_order, item_code, stimulus_text, expected_response,
   item_kind, difficulty, source_instrument_code, tags, is_practice)
SELECT m.test_id, m.module_id, 0, 'M08_P01', 'azul', 'azul',
       'RAPID_NAMING', 1, 'COGNIFIT_SEED_V3',
       ARRAY['m08','practica']::text[], TRUE
FROM m;

-- Verificación rápida (comentada para referencia):
-- SELECT bm.module_code,
--        count(*) AS total,
--        count(*) FILTER (WHERE is_practice) AS practice,
--        min(difficulty) AS min_diff, max(difficulty) AS max_diff
-- FROM assessment.test_items ti
-- JOIN assessment.battery_modules bm ON bm.id = ti.module_id
-- GROUP BY bm.module_code, bm.module_number ORDER BY bm.module_number;
