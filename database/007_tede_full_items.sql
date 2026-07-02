-- =============================================================
-- 007_tede_full_items.sql
-- Banco TEDE completo extraído de los PDFs originales.
-- Reemplaza ítems COGNIFIT_SEED_V2 de M03 y M05 con los 173
-- ítems reales del TEDE (102 Nivel Lector + 71 Errores Específicos).
-- Idempotente: puede ejecutarse más de una vez sin duplicados.
-- =============================================================

-- Limpiar ítems previos de M03 y M05 (V1, V2 y TEDE por si se re-ejecuta)
DELETE FROM assessment.test_items ti
 WHERE ti.source_instrument_code IN ('COGNIFIT_SEED_V1', 'COGNIFIT_SEED_V2', 'TEDE')
   AND ti.module_id IN (
     SELECT bm.id FROM assessment.battery_modules bm
     WHERE bm.module_code IN ('M03_LETTERS_SYLLABLES', 'M05_PSEUDOWORDS')
   );

-- ─── M03 LETRAS Y SÍLABAS — TEDE Nivel Lector (102 ítems) ───────────────────
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
SELECT m.test_id, m.module_id, v.ord, v.code, v.stim, v.stim,
       'LETTERS_SYLLABLES', v.diff,
       'TEDE', v.tags::text[], FALSE
FROM m CROSS JOIN (VALUES
  -- ── nombre_letra (ord 1-13, diff=1) ──────────────────────────────────────
  (1,  'M03_NL_001', 'b',   1, ARRAY['tede','nivel_lector','nombre_letra']),
  (2,  'M03_NL_002', 'm',   1, ARRAY['tede','nivel_lector','nombre_letra']),
  (3,  'M03_NL_003', 'c',   1, ARRAY['tede','nivel_lector','nombre_letra']),
  (4,  'M03_NL_004', 'l',   1, ARRAY['tede','nivel_lector','nombre_letra']),
  (5,  'M03_NL_005', 'a',   1, ARRAY['tede','nivel_lector','nombre_letra']),
  (6,  'M03_NL_006', 'g',   1, ARRAY['tede','nivel_lector','nombre_letra']),
  (7,  'M03_NL_007', 'd',   1, ARRAY['tede','nivel_lector','nombre_letra']),
  (8,  'M03_NL_008', 'p',   1, ARRAY['tede','nivel_lector','nombre_letra']),
  (9,  'M03_NL_009', 's',   1, ARRAY['tede','nivel_lector','nombre_letra']),
  (10, 'M03_NL_010', 'e',   1, ARRAY['tede','nivel_lector','nombre_letra']),
  (11, 'M03_NL_011', 'ch',  1, ARRAY['tede','nivel_lector','nombre_letra']),
  (12, 'M03_NL_012', 'q',   1, ARRAY['tede','nivel_lector','nombre_letra']),
  (13, 'M03_NL_013', 'ñ',   1, ARRAY['tede','nivel_lector','nombre_letra']),
  -- ── sonido_letra (ord 14-26, diff=1) ─────────────────────────────────────
  (14, 'M03_SL_001', 'l',   1, ARRAY['tede','nivel_lector','sonido_letra']),
  (15, 'M03_SL_002', 's',   1, ARRAY['tede','nivel_lector','sonido_letra']),
  (16, 'M03_SL_003', 'll',  1, ARRAY['tede','nivel_lector','sonido_letra']),
  (17, 'M03_SL_004', 'q',   1, ARRAY['tede','nivel_lector','sonido_letra']),
  (18, 'M03_SL_005', 'r',   1, ARRAY['tede','nivel_lector','sonido_letra']),
  (19, 'M03_SL_006', 't',   1, ARRAY['tede','nivel_lector','sonido_letra']),
  (20, 'M03_SL_007', 'e',   1, ARRAY['tede','nivel_lector','sonido_letra']),
  (21, 'M03_SL_008', 'ch',  1, ARRAY['tede','nivel_lector','sonido_letra']),
  (22, 'M03_SL_009', 'j',   1, ARRAY['tede','nivel_lector','sonido_letra']),
  (23, 'M03_SL_010', 'y',   1, ARRAY['tede','nivel_lector','sonido_letra']),
  (24, 'M03_SL_011', 'v',   1, ARRAY['tede','nivel_lector','sonido_letra']),
  (25, 'M03_SL_012', 'd',   1, ARRAY['tede','nivel_lector','sonido_letra']),
  (26, 'M03_SL_013', 'm',   1, ARRAY['tede','nivel_lector','sonido_letra']),
  -- ── silabas_directas_sonido_simple (ord 27-32, diff=1) ───────────────────
  (27, 'M03_SD_001', 'sa',  1, ARRAY['tede','nivel_lector','silabas_directas_sonido_simple']),
  (28, 'M03_SD_002', 'te',  1, ARRAY['tede','nivel_lector','silabas_directas_sonido_simple']),
  (29, 'M03_SD_003', 'mo',  1, ARRAY['tede','nivel_lector','silabas_directas_sonido_simple']),
  (30, 'M03_SD_004', 'lu',  1, ARRAY['tede','nivel_lector','silabas_directas_sonido_simple']),
  (31, 'M03_SD_005', 'ri',  1, ARRAY['tede','nivel_lector','silabas_directas_sonido_simple']),
  (32, 'M03_SD_006', 'fa',  1, ARRAY['tede','nivel_lector','silabas_directas_sonido_simple']),
  -- ── silabas_directas_doble_sonido (ord 33-38, diff=1) ────────────────────
  (33, 'M03_DD_001', 'co',  1, ARRAY['tede','nivel_lector','silabas_directas_doble_sonido']),
  (34, 'M03_DD_002', 'ci',  1, ARRAY['tede','nivel_lector','silabas_directas_doble_sonido']),
  (35, 'M03_DD_003', 'ga',  1, ARRAY['tede','nivel_lector','silabas_directas_doble_sonido']),
  (36, 'M03_DD_004', 'ge',  1, ARRAY['tede','nivel_lector','silabas_directas_doble_sonido']),
  (37, 'M03_DD_005', 'cu',  1, ARRAY['tede','nivel_lector','silabas_directas_doble_sonido']),
  (38, 'M03_DD_006', 'gi',  1, ARRAY['tede','nivel_lector','silabas_directas_doble_sonido']),
  -- ── silabas_directas_consonantes_dobles (ord 39-44, diff=2) ─────────────
  (39, 'M03_DC_001', 'llo', 2, ARRAY['tede','nivel_lector','silabas_directas_consonantes_dobles']),
  (40, 'M03_DC_002', 'cha', 2, ARRAY['tede','nivel_lector','silabas_directas_consonantes_dobles']),
  (41, 'M03_DC_003', 'rri', 2, ARRAY['tede','nivel_lector','silabas_directas_consonantes_dobles']),
  (42, 'M03_DC_004', 'lle', 2, ARRAY['tede','nivel_lector','silabas_directas_consonantes_dobles']),
  (43, 'M03_DC_005', 'rru', 2, ARRAY['tede','nivel_lector','silabas_directas_consonantes_dobles']),
  (44, 'M03_DC_006', 'cho', 2, ARRAY['tede','nivel_lector','silabas_directas_consonantes_dobles']),
  -- ── silabas_con_u_muda (ord 45-48, diff=2) ───────────────────────────────
  (45, 'M03_UM_001', 'gue', 2, ARRAY['tede','nivel_lector','silabas_con_u_muda']),
  (46, 'M03_UM_002', 'qui', 2, ARRAY['tede','nivel_lector','silabas_con_u_muda']),
  (47, 'M03_UM_003', 'gui', 2, ARRAY['tede','nivel_lector','silabas_con_u_muda']),
  (48, 'M03_UM_004', 'que', 2, ARRAY['tede','nivel_lector','silabas_con_u_muda']),
  -- ── silabas_indirectas_simple (ord 49-54, diff=2) ────────────────────────
  (49, 'M03_IS_001', 'is',  2, ARRAY['tede','nivel_lector','silabas_indirectas_simple']),
  (50, 'M03_IS_002', 'ac',  2, ARRAY['tede','nivel_lector','silabas_indirectas_simple']),
  (51, 'M03_IS_003', 'in',  2, ARRAY['tede','nivel_lector','silabas_indirectas_simple']),
  (52, 'M03_IS_004', 'em',  2, ARRAY['tede','nivel_lector','silabas_indirectas_simple']),
  (53, 'M03_IS_005', 'ul',  2, ARRAY['tede','nivel_lector','silabas_indirectas_simple']),
  (54, 'M03_IS_006', 'ar',  2, ARRAY['tede','nivel_lector','silabas_indirectas_simple']),
  -- ── silabas_indirectas_complejo (ord 55-60, diff=2) ──────────────────────
  (55, 'M03_IC_001', 'ob',  2, ARRAY['tede','nivel_lector','silabas_indirectas_complejo']),
  (56, 'M03_IC_002', 'et',  2, ARRAY['tede','nivel_lector','silabas_indirectas_complejo']),
  (57, 'M03_IC_003', 'ap',  2, ARRAY['tede','nivel_lector','silabas_indirectas_complejo']),
  (58, 'M03_IC_004', 'ex',  2, ARRAY['tede','nivel_lector','silabas_indirectas_complejo']),
  (59, 'M03_IC_005', 'af',  2, ARRAY['tede','nivel_lector','silabas_indirectas_complejo']),
  (60, 'M03_IC_006', 'ad',  2, ARRAY['tede','nivel_lector','silabas_indirectas_complejo']),
  -- ── silabas_complejas (ord 61-66, diff=2) ────────────────────────────────
  (61, 'M03_SC_001', 'til', 2, ARRAY['tede','nivel_lector','silabas_complejas']),
  (62, 'M03_SC_002', 'pur', 2, ARRAY['tede','nivel_lector','silabas_complejas']),
  (63, 'M03_SC_003', 'mos', 2, ARRAY['tede','nivel_lector','silabas_complejas']),
  (64, 'M03_SC_004', 'cam', 2, ARRAY['tede','nivel_lector','silabas_complejas']),
  (65, 'M03_SC_005', 'sec', 2, ARRAY['tede','nivel_lector','silabas_complejas']),
  (66, 'M03_SC_006', 'lin', 2, ARRAY['tede','nivel_lector','silabas_complejas']),
  -- ── diptongo_simple (ord 67-72, diff=2) ──────────────────────────────────
  (67, 'M03_DS_001', 'mia', 2, ARRAY['tede','nivel_lector','diptongo_simple']),
  (68, 'M03_DS_002', 'tue', 2, ARRAY['tede','nivel_lector','diptongo_simple']),
  (69, 'M03_DS_003', 'feu', 2, ARRAY['tede','nivel_lector','diptongo_simple']),
  (70, 'M03_DS_004', 'rou', 2, ARRAY['tede','nivel_lector','diptongo_simple']),
  (71, 'M03_DS_005', 'nio', 2, ARRAY['tede','nivel_lector','diptongo_simple']),
  (72, 'M03_DS_006', 'pia', 2, ARRAY['tede','nivel_lector','diptongo_simple']),
  -- ── diptongo_complejo (ord 73-78, diff=3) ────────────────────────────────
  (73, 'M03_DX_001', 'lian', 3, ARRAY['tede','nivel_lector','diptongo_complejo']),
  (74, 'M03_DX_002', 'reis', 3, ARRAY['tede','nivel_lector','diptongo_complejo']),
  (75, 'M03_DX_003', 'viul', 3, ARRAY['tede','nivel_lector','diptongo_complejo']),
  (76, 'M03_DX_004', 'siap', 3, ARRAY['tede','nivel_lector','diptongo_complejo']),
  (77, 'M03_DX_005', 'boim', 3, ARRAY['tede','nivel_lector','diptongo_complejo']),
  (78, 'M03_DX_006', 'siec', 3, ARRAY['tede','nivel_lector','diptongo_complejo']),
  -- ── fonogramas_simple (ord 79-84, diff=3) ────────────────────────────────
  (79, 'M03_FS_001', 'bra', 3, ARRAY['tede','nivel_lector','fonogramas_simple']),
  (80, 'M03_FS_002', 'fli', 3, ARRAY['tede','nivel_lector','fonogramas_simple']),
  (81, 'M03_FS_003', 'gro', 3, ARRAY['tede','nivel_lector','fonogramas_simple']),
  (82, 'M03_FS_004', 'dru', 3, ARRAY['tede','nivel_lector','fonogramas_simple']),
  (83, 'M03_FS_005', 'cle', 3, ARRAY['tede','nivel_lector','fonogramas_simple']),
  (84, 'M03_FS_006', 'tri', 3, ARRAY['tede','nivel_lector','fonogramas_simple']),
  -- ── fonogramas_complejo (ord 85-90, diff=3) ──────────────────────────────
  (85, 'M03_FX_001', 'glus', 3, ARRAY['tede','nivel_lector','fonogramas_complejo']),
  (86, 'M03_FX_002', 'pron', 3, ARRAY['tede','nivel_lector','fonogramas_complejo']),
  (87, 'M03_FX_003', 'tris', 3, ARRAY['tede','nivel_lector','fonogramas_complejo']),
  (88, 'M03_FX_004', 'plaf', 3, ARRAY['tede','nivel_lector','fonogramas_complejo']),
  (89, 'M03_FX_005', 'blen', 3, ARRAY['tede','nivel_lector','fonogramas_complejo']),
  (90, 'M03_FX_006', 'frat', 3, ARRAY['tede','nivel_lector','fonogramas_complejo']),
  -- ── fonogramas_diptongo_simple (ord 91-96, diff=3) ───────────────────────
  (91, 'M03_FD_001', 'brio', 3, ARRAY['tede','nivel_lector','fonogramas_diptongo_simple']),
  (92, 'M03_FD_002', 'crue', 3, ARRAY['tede','nivel_lector','fonogramas_diptongo_simple']),
  (93, 'M03_FD_003', 'trau', 3, ARRAY['tede','nivel_lector','fonogramas_diptongo_simple']),
  (94, 'M03_FD_004', 'glio', 3, ARRAY['tede','nivel_lector','fonogramas_diptongo_simple']),
  (95, 'M03_FD_005', 'pleu', 3, ARRAY['tede','nivel_lector','fonogramas_diptongo_simple']),
  (96, 'M03_FD_006', 'drie', 3, ARRAY['tede','nivel_lector','fonogramas_diptongo_simple']),
  -- ── fonogramas_diptongo_complejo (ord 97-102, diff=3) ────────────────────
  (97,  'M03_FC_001', 'crian',  3, ARRAY['tede','nivel_lector','fonogramas_diptongo_complejo']),
  (98,  'M03_FC_002', 'flaun',  3, ARRAY['tede','nivel_lector','fonogramas_diptongo_complejo']),
  (99,  'M03_FC_003', 'prien',  3, ARRAY['tede','nivel_lector','fonogramas_diptongo_complejo']),
  (100, 'M03_FC_004', 'clous',  3, ARRAY['tede','nivel_lector','fonogramas_diptongo_complejo']),
  (101, 'M03_FC_005', 'triun',  3, ARRAY['tede','nivel_lector','fonogramas_diptongo_complejo']),
  (102, 'M03_FC_006', 'blauc',  3, ARRAY['tede','nivel_lector','fonogramas_diptongo_complejo'])
) AS v(ord, code, stim, diff, tags);

-- ─── M05 PSEUDOPALABRAS — TEDE Errores Específicos (71 ítems) ────────────────
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
SELECT m.test_id, m.module_id, v.ord, v.code, v.stim, v.stim,
       'PSEUDOWORDS', v.diff,
       'TEDE', v.tags::text[], FALSE
FROM m CROSS JOIN (VALUES
  -- ── confundibles_sonido_palabras (ord 1-12, diff=2) ──────────────────────
  -- Pseudopalabras con fonemas confundibles: testa confusión b/d, f/j, etc.
  (1,  'M05_CS_001', 'chado',   2, ARRAY['tede','errores_especificos','SUS','confundibles_sonido']),
  (2,  'M05_CS_002', 'deco',    2, ARRAY['tede','errores_especificos','SUS','confundibles_sonido']),
  (3,  'M05_CS_003', 'fido',    2, ARRAY['tede','errores_especificos','SUS','confundibles_sonido']),
  (4,  'M05_CS_004', 'llotio',  2, ARRAY['tede','errores_especificos','SUS','confundibles_sonido']),
  (5,  'M05_CS_005', 'tarpo',   2, ARRAY['tede','errores_especificos','SUS','confundibles_sonido']),
  (6,  'M05_CS_006', 'gupa',    2, ARRAY['tede','errores_especificos','SUS','confundibles_sonido']),
  (7,  'M05_CS_007', 'boso',    2, ARRAY['tede','errores_especificos','SUS','confundibles_sonido']),
  (8,  'M05_CS_008', 'jallón',  2, ARRAY['tede','errores_especificos','SUS','confundibles_sonido']),
  (9,  'M05_CS_009', 'pola',    2, ARRAY['tede','errores_especificos','SUS','confundibles_sonido']),
  (10, 'M05_CS_010', 'querpo',  2, ARRAY['tede','errores_especificos','SUS','confundibles_sonido']),
  (11, 'M05_CS_011', 'mite',    2, ARRAY['tede','errores_especificos','SUS','confundibles_sonido']),
  (12, 'M05_CS_012', 'ñuma',    2, ARRAY['tede','errores_especificos','SUS','confundibles_sonido']),
  -- ── grafia_semejante_pseudopalabras (ord 13-24, diff=2-3) ────────────────
  -- Pseudopalabras con grafías semejantes: testa confusión b/d, p/q, etc.
  (13, 'M05_GS_001', 'nomino',    2, ARRAY['tede','errores_especificos','SUS','grafia_semejante']),
  (14, 'M05_GS_002', 'ohnado',    2, ARRAY['tede','errores_especificos','SUS','grafia_semejante']),
  (15, 'M05_GS_003', 'deste',     2, ARRAY['tede','errores_especificos','SUS','grafia_semejante']),
  (16, 'M05_GS_004', 'alledo',    3, ARRAY['tede','errores_especificos','SUS','grafia_semejante']),
  (17, 'M05_GS_005', 'rechido',   3, ARRAY['tede','errores_especificos','SUS','grafia_semejante']),
  (18, 'M05_GS_006', 'chaquillo', 3, ARRAY['tede','errores_especificos','SUS','grafia_semejante']),
  (19, 'M05_GS_007', 'laqueta',   3, ARRAY['tede','errores_especificos','SUS','grafia_semejante']),
  (20, 'M05_GS_008', 'sagueso',   3, ARRAY['tede','errores_especificos','SUS','grafia_semejante']),
  (21, 'M05_GS_009', 'quiguifi',  3, ARRAY['tede','errores_especificos','SUS','grafia_semejante']),
  (22, 'M05_GS_010', 'ifjuti',    3, ARRAY['tede','errores_especificos','SUS','grafia_semejante']),
  (23, 'M05_GS_011', 'voyate',    2, ARRAY['tede','errores_especificos','SUS','grafia_semejante']),
  (24, 'M05_GS_012', 'quellimi',  3, ARRAY['tede','errores_especificos','SUS','grafia_semejante']),
  -- ── inversiones_letras (ord 25-36, diff=2) ───────────────────────────────
  -- Pseudopalabras con b/d/p/q invertibles: detecta inversión de letras
  (25, 'M05_IL_001', 'bado',    2, ARRAY['tede','errores_especificos','INV','ROT','inversiones_letras']),
  (26, 'M05_IL_002', 'dipo',    2, ARRAY['tede','errores_especificos','INV','ROT','inversiones_letras']),
  (27, 'M05_IL_003', 'babe',    2, ARRAY['tede','errores_especificos','INV','ROT','inversiones_letras']),
  (28, 'M05_IL_004', 'quebo',   2, ARRAY['tede','errores_especificos','INV','ROT','inversiones_letras']),
  (29, 'M05_IL_005', 'quido',   2, ARRAY['tede','errores_especificos','INV','ROT','inversiones_letras']),
  (30, 'M05_IL_006', 'dudo',    2, ARRAY['tede','errores_especificos','INV','ROT','inversiones_letras']),
  (31, 'M05_IL_007', 'bapi',    2, ARRAY['tede','errores_especificos','INV','ROT','inversiones_letras']),
  (32, 'M05_IL_008', 'quipi',   2, ARRAY['tede','errores_especificos','INV','ROT','inversiones_letras']),
  (33, 'M05_IL_009', 'dubopi',  3, ARRAY['tede','errores_especificos','INV','ROT','inversiones_letras']),
  (34, 'M05_IL_010', 'pebade',  3, ARRAY['tede','errores_especificos','INV','ROT','inversiones_letras']),
  (35, 'M05_IL_011', 'numo',    2, ARRAY['tede','errores_especificos','INV','ROT','inversiones_letras']),
  (36, 'M05_IL_012', 'saute',   2, ARRAY['tede','errores_especificos','INV','ROT','inversiones_letras']),
  -- ── inversiones_palabras_completas (ord 37-47, diff=1-2) ─────────────────
  -- Palabras simétricas: detecta lectura en espejo de la palabra completa
  (37, 'M05_IP_001', 'la',   1, ARRAY['tede','errores_especificos','INV','inversiones_palabras_completas']),
  (38, 'M05_IP_002', 'sol',  1, ARRAY['tede','errores_especificos','INV','inversiones_palabras_completas']),
  (39, 'M05_IP_003', 'se',   1, ARRAY['tede','errores_especificos','INV','inversiones_palabras_completas']),
  (40, 'M05_IP_004', 'las',  1, ARRAY['tede','errores_especificos','INV','inversiones_palabras_completas']),
  (41, 'M05_IP_005', 'nos',  1, ARRAY['tede','errores_especificos','INV','inversiones_palabras_completas']),
  (42, 'M05_IP_006', 'los',  1, ARRAY['tede','errores_especificos','INV','inversiones_palabras_completas']),
  (43, 'M05_IP_007', 'al',   1, ARRAY['tede','errores_especificos','INV','inversiones_palabras_completas']),
  (44, 'M05_IP_008', 'es',   1, ARRAY['tede','errores_especificos','INV','inversiones_palabras_completas']),
  (45, 'M05_IP_009', 'son',  2, ARRAY['tede','errores_especificos','INV','inversiones_palabras_completas']),
  (46, 'M05_IP_010', 'le',   1, ARRAY['tede','errores_especificos','INV','inversiones_palabras_completas']),
  (47, 'M05_IP_011', 'sal',  2, ARRAY['tede','errores_especificos','INV','inversiones_palabras_completas']),
  -- ── inversiones_letras_en_palabra (ord 48-59, diff=2-3) ──────────────────
  -- Palabras reales con letras invertibles dentro: b↔d, p↔q, n↔u
  (48, 'M05_LW_001', 'palta',   2, ARRAY['tede','errores_especificos','INV','inversiones_letras_en_palabra']),
  (49, 'M05_LW_002', 'sobra',   2, ARRAY['tede','errores_especificos','INV','inversiones_letras_en_palabra']),
  (50, 'M05_LW_003', 'trota',   2, ARRAY['tede','errores_especificos','INV','inversiones_letras_en_palabra']),
  (51, 'M05_LW_004', 'plumón',  2, ARRAY['tede','errores_especificos','INV','inversiones_letras_en_palabra']),
  (52, 'M05_LW_005', 'turco',   2, ARRAY['tede','errores_especificos','INV','inversiones_letras_en_palabra']),
  (53, 'M05_LW_006', 'trono',   2, ARRAY['tede','errores_especificos','INV','inversiones_letras_en_palabra']),
  (54, 'M05_LW_007', 'balcón',  3, ARRAY['tede','errores_especificos','INV','inversiones_letras_en_palabra']),
  (55, 'M05_LW_008', 'negar',   2, ARRAY['tede','errores_especificos','INV','inversiones_letras_en_palabra']),
  (56, 'M05_LW_009', 'sabré',   3, ARRAY['tede','errores_especificos','INV','inversiones_letras_en_palabra']),
  (57, 'M05_LW_010', 'calvo',   3, ARRAY['tede','errores_especificos','INV','inversiones_letras_en_palabra']),
  (58, 'M05_LW_011', 'nobel',   3, ARRAY['tede','errores_especificos','INV','inversiones_letras_en_palabra']),
  (59, 'M05_LW_012', 'pardo',   3, ARRAY['tede','errores_especificos','INV','inversiones_letras_en_palabra']),
  -- ── inversion_orden_silaba (ord 60-71, diff=2-3) ─────────────────────────
  -- Palabras bisílabas: detecta transposición del orden silábico (ej. "loma"→"malo")
  (60, 'M05_OS_001', 'loma',   2, ARRAY['tede','errores_especificos','INV','OMI','inversion_orden_silaba']),
  (61, 'M05_OS_002', 'saco',   2, ARRAY['tede','errores_especificos','INV','OMI','inversion_orden_silaba']),
  (62, 'M05_OS_003', 'dato',   2, ARRAY['tede','errores_especificos','INV','OMI','inversion_orden_silaba']),
  (63, 'M05_OS_004', 'tapa',   2, ARRAY['tede','errores_especificos','INV','OMI','inversion_orden_silaba']),
  (64, 'M05_OS_005', 'tala',   2, ARRAY['tede','errores_especificos','INV','OMI','inversion_orden_silaba']),
  (65, 'M05_OS_006', 'cabo',   2, ARRAY['tede','errores_especificos','INV','OMI','inversion_orden_silaba']),
  (66, 'M05_OS_007', 'sopa',   2, ARRAY['tede','errores_especificos','INV','OMI','inversion_orden_silaba']),
  (67, 'M05_OS_008', 'toga',   2, ARRAY['tede','errores_especificos','INV','OMI','inversion_orden_silaba']),
  (68, 'M05_OS_009', 'saca',   2, ARRAY['tede','errores_especificos','INV','OMI','inversion_orden_silaba']),
  (69, 'M05_OS_010', 'choca',  3, ARRAY['tede','errores_especificos','INV','OMI','inversion_orden_silaba']),
  (70, 'M05_OS_011', 'cala',   2, ARRAY['tede','errores_especificos','INV','OMI','inversion_orden_silaba']),
  (71, 'M05_OS_012', 'caro',   2, ARRAY['tede','errores_especificos','INV','OMI','inversion_orden_silaba'])
) AS v(ord, code, stim, diff, tags);

-- Verificación rápida:
-- SELECT bm.module_code, count(*) AS items
-- FROM assessment.test_items ti
-- JOIN assessment.battery_modules bm ON bm.id = ti.module_id
-- WHERE ti.source_instrument_code = 'TEDE'
-- GROUP BY 1 ORDER BY 1;
-- Esperado: M03_LETTERS_SYLLABLES=102, M05_PSEUDOWORDS=71
