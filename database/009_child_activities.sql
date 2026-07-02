-- ============================================================
-- Migración 009 — Módulo M10: Actividades infantiles (discriminación visual)
-- Fuente: "Material de apoyo para la Dislexia" (Profra. Juana González García, Maroleón Gto.)
--         + contenido del programa PIENSO / Auxiliar Didáctico UPN
-- ============================================================

-- 1. Extender el CHECK de module_number para aceptar módulos más allá del 9
ALTER TABLE assessment.battery_modules
    DROP CONSTRAINT IF EXISTS battery_modules_module_number_check;
ALTER TABLE assessment.battery_modules
    ADD CONSTRAINT battery_modules_module_number_check
    CHECK (module_number >= 1 AND module_number <= 20);

-- 2. Agregar módulo M10_VD si no existe
INSERT INTO assessment.battery_modules
    (module_code, module_number, title, phase, test_type, input_modes, captures)
VALUES
    ('M10_VD', 10,
     'Discriminación Visual',
     1,               -- fase 1: percepción básica
     'PSEUDOWORDS',   -- tipo más cercano; el item_kind sobreescribe la lógica de presentación
     ARRAY['TACTIL'],
     ARRAY['TACTIL'])
ON CONFLICT (module_code) DO NOTHING;

-- 3. Crear el test asociado
INSERT INTO assessment.tests (module_id, test_type, name, target_grades)
SELECT bm.id, 'PSEUDOWORDS', 'Discriminación Visual — Set 1', ARRAY[1,2,3]::smallint[]
FROM assessment.battery_modules bm
WHERE bm.module_code = 'M10_VD'
  AND NOT EXISTS (
    SELECT 1 FROM assessment.tests t2
    JOIN assessment.battery_modules bm2 ON bm2.id = t2.module_id
    WHERE bm2.module_code = 'M10_VD'
  );

-- 4. Borrar ítems anteriores del módulo M10 (idempotente)
DELETE FROM assessment.test_items
WHERE module_id = (SELECT id FROM assessment.battery_modules WHERE module_code = 'M10_VD');

-- 5. Insertar los 21 ítems de discriminación visual
--    stimulus_text: "opcion1|opcion2|opcion3|opcion4"   (pipe-separated — la app parsea)
--    expected_response: la opción "rara" (el niño debe tocarla)
--    item_kind = 'VISUAL_DISCRIMINATION' — la app detecta esto y muestra tarjetas táctiles
DO $$
DECLARE
    v_module_id UUID;
    v_test_id   UUID;
BEGIN
    SELECT id INTO v_module_id FROM assessment.battery_modules WHERE module_code = 'M10_VD';
    SELECT id INTO v_test_id   FROM assessment.tests WHERE module_id = v_module_id LIMIT 1;

    INSERT INTO assessment.test_items
        (module_id, test_id, item_code, item_order, stimulus_text, expected_response,
         item_kind, difficulty, is_practice, source_instrument_code, tags)
    VALUES
    -- ── Ítem de práctica ──────────────────────────────────────────────────
    (v_module_id, v_test_id, 'M10_P01', 0,
     'a|a|e|a', 'e', 'VISUAL_DISCRIMINATION', 1, TRUE,
     'CUADERNILLO_DISLEXIA', ARRAY['visual_discrimination','practica','letra']),

    -- ── A1: confusión b / d ───────────────────────────────────────────────
    (v_module_id, v_test_id, 'M10_VD_01', 1,
     'b|b|d|b', 'd', 'VISUAL_DISCRIMINATION', 1, FALSE,
     'CUADERNILLO_DISLEXIA', ARRAY['visual_discrimination','b_d','letra','diff_1']),
    (v_module_id, v_test_id, 'M10_VD_02', 2,
     'd|d|b|d', 'b', 'VISUAL_DISCRIMINATION', 1, FALSE,
     'CUADERNILLO_DISLEXIA', ARRAY['visual_discrimination','b_d','letra','diff_1']),

    -- ── A2: confusión p / q ───────────────────────────────────────────────
    (v_module_id, v_test_id, 'M10_VD_03', 3,
     'p|p|q|p', 'q', 'VISUAL_DISCRIMINATION', 1, FALSE,
     'CUADERNILLO_DISLEXIA', ARRAY['visual_discrimination','p_q','letra','diff_1']),
    (v_module_id, v_test_id, 'M10_VD_04', 4,
     'q|q|p|q', 'p', 'VISUAL_DISCRIMINATION', 1, FALSE,
     'CUADERNILLO_DISLEXIA', ARRAY['visual_discrimination','p_q','letra','diff_1']),

    -- ── A3: confusión n / u ───────────────────────────────────────────────
    (v_module_id, v_test_id, 'M10_VD_05', 5,
     'n|n|u|n', 'u', 'VISUAL_DISCRIMINATION', 1, FALSE,
     'CUADERNILLO_DISLEXIA', ARRAY['visual_discrimination','n_u','letra','diff_1']),
    (v_module_id, v_test_id, 'M10_VD_06', 6,
     'u|u|n|u', 'n', 'VISUAL_DISCRIMINATION', 1, FALSE,
     'CUADERNILLO_DISLEXIA', ARRAY['visual_discrimination','n_u','letra','diff_1']),

    -- ── A4: confusión b / p ───────────────────────────────────────────────
    (v_module_id, v_test_id, 'M10_VD_07', 7,
     'b|b|p|b', 'p', 'VISUAL_DISCRIMINATION', 2, FALSE,
     'CUADERNILLO_DISLEXIA', ARRAY['visual_discrimination','b_p','letra','diff_2']),
    (v_module_id, v_test_id, 'M10_VD_08', 8,
     'p|p|b|p', 'b', 'VISUAL_DISCRIMINATION', 2, FALSE,
     'CUADERNILLO_DISLEXIA', ARRAY['visual_discrimination','b_p','letra','diff_2']),

    -- ── A5: confusión d / q ───────────────────────────────────────────────
    (v_module_id, v_test_id, 'M10_VD_09', 9,
     'd|d|q|d', 'q', 'VISUAL_DISCRIMINATION', 2, FALSE,
     'CUADERNILLO_DISLEXIA', ARRAY['visual_discrimination','d_q','letra','diff_2']),

    -- ── A6: confusión m / n ───────────────────────────────────────────────
    (v_module_id, v_test_id, 'M10_VD_10', 10,
     'm|m|n|m', 'n', 'VISUAL_DISCRIMINATION', 2, FALSE,
     'CUADERNILLO_DISLEXIA', ARRAY['visual_discrimination','m_n','letra','diff_2']),

    -- ── B: Sílabas ────────────────────────────────────────────────────────
    (v_module_id, v_test_id, 'M10_VD_11', 11,
     'ba|ba|da|ba', 'da', 'VISUAL_DISCRIMINATION', 2, FALSE,
     'CUADERNILLO_DISLEXIA', ARRAY['visual_discrimination','silaba','b_d','diff_2']),
    (v_module_id, v_test_id, 'M10_VD_12', 12,
     'de|de|be|de', 'be', 'VISUAL_DISCRIMINATION', 2, FALSE,
     'CUADERNILLO_DISLEXIA', ARRAY['visual_discrimination','silaba','b_d','diff_2']),
    (v_module_id, v_test_id, 'M10_VD_13', 13,
     'pi|pi|bi|pi', 'bi', 'VISUAL_DISCRIMINATION', 2, FALSE,
     'CUADERNILLO_DISLEXIA', ARRAY['visual_discrimination','silaba','p_b','diff_2']),
    (v_module_id, v_test_id, 'M10_VD_14', 14,
     'po|po|bo|po', 'bo', 'VISUAL_DISCRIMINATION', 2, FALSE,
     'CUADERNILLO_DISLEXIA', ARRAY['visual_discrimination','silaba','p_b','diff_2']),

    -- ── C: Palabras inversas (especulares) ───────────────────────────────
    (v_module_id, v_test_id, 'M10_VD_15', 15,
     'sol|sol|los|sol', 'los', 'VISUAL_DISCRIMINATION', 3, FALSE,
     'CUADERNILLO_DISLEXIA', ARRAY['visual_discrimination','palabra','inversion','diff_3']),
    (v_module_id, v_test_id, 'M10_VD_16', 16,
     'la|la|al|la', 'al', 'VISUAL_DISCRIMINATION', 3, FALSE,
     'CUADERNILLO_DISLEXIA', ARRAY['visual_discrimination','palabra','inversion','diff_3']),
    (v_module_id, v_test_id, 'M10_VD_17', 17,
     'nos|nos|son|nos', 'son', 'VISUAL_DISCRIMINATION', 3, FALSE,
     'CUADERNILLO_DISLEXIA', ARRAY['visual_discrimination','palabra','inversion','diff_3']),
    (v_module_id, v_test_id, 'M10_VD_18', 18,
     'es|es|se|es', 'se', 'VISUAL_DISCRIMINATION', 3, FALSE,
     'CUADERNILLO_DISLEXIA', ARRAY['visual_discrimination','palabra','inversion','diff_3']),

    -- ── D: Flechas / direcciones (cuadernillo pág. 8 "Las flechas") ──────
    (v_module_id, v_test_id, 'M10_VD_19', 19,
     '→|→|←|→', '←', 'VISUAL_DISCRIMINATION', 2, FALSE,
     'CUADERNILLO_DISLEXIA', ARRAY['visual_discrimination','direccion','flecha','diff_2']),
    (v_module_id, v_test_id, 'M10_VD_20', 20,
     '←|←|→|←', '→', 'VISUAL_DISCRIMINATION', 2, FALSE,
     'CUADERNILLO_DISLEXIA', ARRAY['visual_discrimination','direccion','flecha','diff_2']);
END $$;

-- 6. Verificación
SELECT bm.module_code, count(*) AS total_items,
       count(*) FILTER (WHERE ti.is_practice) AS practice_items
FROM assessment.test_items ti
JOIN assessment.battery_modules bm ON bm.id = ti.module_id
WHERE bm.module_code = 'M10_VD'
GROUP BY 1;
-- Esperado: M10_VD | 21 | 1
