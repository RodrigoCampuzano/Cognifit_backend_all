-- 018 — Muestreo por sesión: cuántos ítems se presentan de cada módulo.
--
-- POR QUÉ
--
-- Hoy una sesión entrega TODOS los ítems del módulo. En los dos módulos
-- grandes eso contradice la propia duración estimada del test:
--
--   Letras y sílabas   103 ítems en 4 min  =  2,3 s por ítem
--   Pseudopalabras      72 ítems en 4 min  =  3,3 s por ítem
--
-- Dos segundos por ítem es imposible para un niño de primaria con dificultad
-- lectora; los demás módulos dan entre 11 y 33 s por ítem, que sí es
-- plausible. Esa contradicción indica que el diseño preveía presentar una
-- muestra del banco, y que el muestreo nunca se implementó.
--
-- Presentar una muestra distinta en cada aplicación tiene además un efecto que
-- importa más: es lo único que evita que el alumno memorice las RESPUESTAS.
-- Barajar el orden —que ya se hacía— solo evita que memorice la secuencia; si
-- ve siempre los mismos 103 ítems, recordar "a esa palabra rara respondí X"
-- funciona igual sin importar en qué posición aparezca.
--
-- LA RESTRICCIÓN QUE OBLIGA A ESTRATIFICAR
--
-- Un tamizaje sirve para comparar al alumno consigo mismo con el tiempo. Si en
-- marzo le tocan ítems fáciles y en junio difíciles, no se sabe si mejoró o si
-- le tocó una muestra más benigna. Por eso el muestreo no puede ser aleatorio
-- simple: tiene que conservar la proporción de cada nivel de dificultad, de
-- modo que dos aplicaciones tengan la misma dificultad promedio aunque los
-- ítems sean distintos.
--
--   Letras y sílabas   39 fáciles · 34 medios · 30 difíciles  (103)
--   Muestra de 30      11 fáciles · 10 medios ·  9 difíciles
--
-- NULL = presentar todos los ítems. Es el valor correcto para los módulos
-- cuyo banco ya es del tamaño de una sesión.

BEGIN;

ALTER TABLE assessment.tests
    ADD COLUMN IF NOT EXISTS items_per_session SMALLINT
        CHECK (items_per_session IS NULL OR items_per_session > 0);

COMMENT ON COLUMN assessment.tests.items_per_session IS
    'Ítems a presentar por sesión, muestreados de forma estratificada por '
    'dificultad. NULL = presentar todos. Los ítems de práctica se incluyen '
    'siempre y no cuentan para este total.';

-- Los dos módulos cuyo banco excede largamente lo que entra en una sesión.
-- Las cantidades salen de la duración declarada del test y de la velocidad por
-- ítem observada en los módulos comparables (11-33 s/ítem).
--
-- REVISAR CON UN ESPECIALISTA: son estimaciones a partir de la duración, no
-- valores validados. Un banco de tamizaje suele fijar el largo de la forma por
-- criterio psicométrico —fiabilidad de la medida—, no por tiempo disponible.
UPDATE assessment.tests SET items_per_session = 30
 WHERE name = 'Letras y sílabas' AND items_per_session IS NULL;

UPDATE assessment.tests SET items_per_session = 24
 WHERE name = 'Pseudopalabras' AND items_per_session IS NULL;

COMMIT;

-- ─── Verificación ────────────────────────────────────────────────────────────
--
--   SELECT t.name, t.items_per_session, count(i.id) AS pool,
--          t.estimated_duration_max AS min
--     FROM assessment.tests t
--     JOIN assessment.test_items i ON i.test_id = t.id
--    WHERE t.is_active
--    GROUP BY t.name, t.items_per_session, t.estimated_duration_max
--    ORDER BY count(i.id) DESC;
--
-- Con la muestra aplicada, la duración por ítem debe quedar en el rango de los
-- módulos comparables en vez de en 2 segundos.
