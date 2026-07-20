-- 019 — Calendario del tamizaje: qué le toca a cada alumno y cuándo.
--
-- POR QUÉ DOS CADENCIAS Y NO UNA
--
-- Repetir la batería completa cada mes no es viable con el banco actual, y el
-- problema no es de código sino de contenido: siete de los nueve módulos no
-- tienen de dónde muestrear. En comprensión lectora son 9 ítems y la muestra
-- son esos mismos 9, así que el alumno vería exactamente los mismos ítems diez
-- veces al año. Para la tercera aplicación los recuerda, y a partir de ahí la
-- prueba mide memoria en vez de comprensión.
--
-- Eso importa especialmente acá, porque el objetivo declarado es ver la curva
-- de avance. Con ítems repetidos la curva sube por efecto de práctica: se
-- vería una mejora y se concluiría que la intervención funciona cuando quizá
-- no está funcionando. Para un sistema cuyo trabajo es avisar si algo no
-- sirve, ese es el peor error posible.
--
-- Además la batería completa dura 27-36 minutos. Mensual durante el ciclo
-- escolar son seis horas de clase por alumno.
--
-- Se separan entonces dos propósitos que estaban mezclados:
--
--   MONITOREO   mensual, ~8 min   ¿está avanzando con la intervención?
--   TAMIZAJE    cuatrimestral     ¿cambió su perfil? ¿hay que redirigir?
--
-- El monitoreo usa solo los dos módulos con banco suficiente. No es una
-- concesión: pseudopalabras es además la mejor medida de curva disponible,
-- porque una pseudopalabra no se puede adivinar por contexto ni por
-- vocabulario —o se decodifica o no— y es justo lo que se mueve cuando la
-- intervención fonológica da resultado.

BEGIN;

-- ─── Qué módulos entran en el monitoreo mensual ──────────────────────────────
ALTER TABLE assessment.tests
    ADD COLUMN IF NOT EXISTS is_monitoring BOOLEAN NOT NULL DEFAULT FALSE;

COMMENT ON COLUMN assessment.tests.is_monitoring IS
    'Entra en el monitoreo mensual de avance. Requiere que el banco tenga más '
    'ítems que una sesión (items_per_session no nulo): si no, el alumno repite '
    'los mismos ítems y la curva sube por práctica, no por aprendizaje.';

UPDATE assessment.tests
   SET is_monitoring = TRUE
 WHERE name IN ('Pseudopalabras', 'Letras y sílabas');

-- Un módulo sin banco no puede monitorear: se dejaría de medir avance para
-- medir memoria. La restricción lo vuelve imposible por construcción.
ALTER TABLE assessment.tests
    DROP CONSTRAINT IF EXISTS tests_monitoring_requiere_banco;
ALTER TABLE assessment.tests
    ADD CONSTRAINT tests_monitoring_requiere_banco
    CHECK (NOT is_monitoring OR items_per_session IS NOT NULL);

-- ─── Cuándo le toca a cada alumno ────────────────────────────────────────────
-- Los intervalos viven en la vista y no en la aplicación para que un cambio de
-- criterio clínico no dependa de un despliegue.
CREATE OR REPLACE VIEW assessment.v_calendario_tamizaje AS
WITH ultimas AS (
    SELECT ta.student_id,
           max(ts.completed_at) FILTER (WHERE t.is_monitoring) AS ult_monitoreo,
           max(ts.completed_at)                                AS ult_cualquiera
    FROM assessment.test_assignments ta
    JOIN assessment.test_sessions ts ON ts.assignment_id = ta.id
    JOIN assessment.battery_modules bm ON bm.id = ts.module_id
    JOIN assessment.tests t ON t.test_type = bm.test_type
    WHERE ts.completed_at IS NOT NULL
    GROUP BY ta.student_id
),
-- Una batería cuenta como hecha solo si se COMPLETARON todos los módulos
-- básicos de esa asignación, no si se asignó con battery_mode = 'FULL'.
-- Marcar la intención bastaba para que un alumno que abandonó la batería tras
-- el primer módulo quedara exento durante 120 días.
baterias AS (
    SELECT ta.student_id, max(ts.completed_at) AS ult_bateria
    FROM assessment.test_assignments ta
    JOIN assessment.test_sessions ts ON ts.assignment_id = ta.id
    WHERE ts.completed_at IS NOT NULL
    GROUP BY ta.student_id, ta.id
    HAVING count(DISTINCT ts.module_id) >= (
        SELECT count(*) FROM assessment.battery_modules WHERE is_active AND is_core
    )
)
SELECT s.id AS student_id,
       s.group_id,
       u.ult_monitoreo,
       b.ult_bateria,
       u.ult_cualquiera,

       (now() - u.ult_monitoreo) > INTERVAL '30 days'  AS monitoreo_vencido,
       (now() - b.ult_bateria)   > INTERVAL '120 days' AS bateria_vencida,

       -- Un alumno sin ninguna aplicación necesita la batería completa: no hay
       -- perfil del cual partir.
       (u.ult_cualquiera IS NULL) AS sin_linea_base,

       CASE
           WHEN u.ult_cualquiera IS NULL                              THEN 'BATERIA_INICIAL'
           WHEN b.ult_bateria IS NULL
             OR (now() - b.ult_bateria) > INTERVAL '120 days'         THEN 'BATERIA'
           WHEN u.ult_monitoreo IS NULL
             OR (now() - u.ult_monitoreo) > INTERVAL '30 days'        THEN 'MONITOREO'
           ELSE 'AL_DIA'
       END AS que_toca
FROM academic.students s
LEFT JOIN ultimas  u ON u.student_id = s.id
LEFT JOIN baterias b ON b.student_id = s.id;

COMMENT ON VIEW assessment.v_calendario_tamizaje IS
    'Qué aplicación le corresponde a cada alumno. MONITOREO cada 30 días con '
    'los módulos is_monitoring; BATERIA completa cada 120 días. La batería '
    'tiene prioridad sobre el monitoreo cuando ambos vencen.';

COMMIT;

-- ─── Verificación ────────────────────────────────────────────────────────────
--
--   SELECT que_toca, count(*) FROM assessment.v_calendario_tamizaje
--    GROUP BY que_toca ORDER BY 2 DESC;
--
-- Y que ningún módulo de monitoreo se quede sin banco:
--
--   SELECT name FROM assessment.tests
--    WHERE is_monitoring AND items_per_session IS NULL;   -- debe salir vacío
