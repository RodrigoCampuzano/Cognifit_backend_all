-- 017 — Corrige el tipo del test de discriminación visual y retira los
-- marcadores vacíos que quedaron del esquema inicial.
--
-- CONTEXTO
--
-- Al inventariar el tamizaje en producción aparecieron dos cosas:
--
-- 1. "Discriminación Visual — Set 1" está registrado con
--    test_type = 'PSEUDOWORDS', pero sus 21 ítems son VISUAL_DISCRIMINATION.
--    Es el mismo módulo (M10_VD) que estuvo meses sin figurar en ninguna ruta:
--    se corrigió el ruteo, pero el tipo del test quedó mal.
--
--    La consecuencia no es cosmética. Cualquier consulta que filtre o agrupe
--    por test_type cuenta esos 21 ítems como pseudopalabras, así que un informe
--    por área daría 93 de pseudopalabras cuando en realidad son 72.
--
-- 2. Cuatro tests se crearon en schema.sql y nunca recibieron ítems. Tres de
--    ellos duplican a un test que sí tiene contenido:
--
--      "Test Pseudopalabras Nivel 1"  (0)  vs "Pseudopalabras"       (72)
--      "Test Léxico-Visual Básico"    (0)  vs "Discriminación Visual"(21)
--      "Test Dictado con STT Nivel 1" (0)  vs "Dictado inteligente"  (13)
--
--    El cuarto, "Cuestionario docente PRODISLEX digitalizado", es un caso
--    distinto y NO se toca: el cuestionario no vive en test_items sino en
--    assessment.teacher_screening_items, donde tiene sus 8 ítems activos. Su
--    fila en `tests` existe para que el módulo aparezca en la batería.
--
-- Un test vacío y activo es peor que uno ausente: se puede asignar a un alumno
-- y abre una sesión sin nada que responder.

BEGIN;

-- ─── 1. El tipo correcto ─────────────────────────────────────────────────────
-- El enum no tiene VISUAL_DISCRIMINATION; el valor equivalente es
-- LEXICO_VISUAL, que es como se llamaba el marcador vacío del esquema.
UPDATE assessment.tests
   SET test_type = 'LEXICO_VISUAL'
 WHERE name = 'Discriminación Visual — Set 1'
   AND test_type = 'PSEUDOWORDS';

-- ─── 2. Los marcadores vacíos que duplican un test real ──────────────────────
-- Se desactivan en vez de borrarse: si alguna asignación vieja los referencia,
-- borrarlos rompería la clave foránea. Desactivar los saca de la batería y
-- conserva el historial.
UPDATE assessment.tests t
   SET is_active = FALSE
 WHERE t.is_active
   AND t.name IN (
        'Test Pseudopalabras Nivel 1',
        'Test Léxico-Visual Básico',
        'Test Dictado con STT Nivel 1'
   )
   AND NOT EXISTS (SELECT 1 FROM assessment.test_items i WHERE i.test_id = t.id);

COMMIT;

-- ─── Verificación ────────────────────────────────────────────────────────────
-- Ningún test activo debe quedar sin ítems, salvo el cuestionario docente,
-- cuyos ítems viven en otra tabla.
--
--   SELECT t.name, t.test_type, count(i.id) AS items
--     FROM assessment.tests t
--     LEFT JOIN assessment.test_items i ON i.test_id = t.id
--    WHERE t.is_active
--    GROUP BY t.name, t.test_type
--   HAVING count(i.id) = 0;
--
-- Y el tipo ya no debe contradecir al contenido:
--
--   SELECT t.name, t.test_type, i.item_kind, count(*)
--     FROM assessment.test_items i
--     JOIN assessment.tests t ON t.id = i.test_id
--    GROUP BY t.name, t.test_type, i.item_kind
--   HAVING t.test_type::text <> i.item_kind::text;
