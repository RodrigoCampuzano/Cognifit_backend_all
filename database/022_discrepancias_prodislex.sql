-- 022 — Discrepancias de PRODISLEX: la firma de la dificultad inesperada.
--
-- QUÉ SON
--
-- El protocolo dedica un bloque entero a las discrepancias, y no es un anexo:
-- es lo que distingue una dificultad ESPECÍFICA de lectura de una dificultad
-- general de aprendizaje.
--
--   Discrepancias entre:
--     · Cociente intelectual y el éxito escolar
--     · Trabajo oral y trabajo escrito
--     · Rendimiento en distintas materias
--     · Comprensión y memoria
--     · Días buenos y días malos
--     · Esfuerzo-trabajo y la calidad del resultado final
--
-- Un alumno que explica todo perfectamente hablando y se derrumba al escribir
-- tiene el patrón clásico. Uno que rinde parejo y bajo en todo probablemente
-- tenga otra cosa. Los ocho ítems de sintomatología que ya existían no
-- distinguen esos dos casos: ambos marcarían "lee lento" y "omite letras".
--
-- POR QUÉ NO SUMAN AL PUNTAJE EXISTENTE
--
-- Los ocho ítems de riesgo tienen pesos con fundamento documentado (PRODISLEX
-- + TEDE) y suman exactamente 100. Ese puntaje decide además qué batería se le
-- aplica al alumno: 50 o más manda la completa. Agregar seis ítems con pesos
-- inventados diluiría una calibración que alguien pensó y correría ese umbral,
-- o sea cambiaría qué prueba recibe un niño por una decisión de implementación.
--
-- Por eso las discrepancias forman un ÍNDICE APARTE, de 0 a 100, que se
-- informa junto al puntaje sin mezclarse. La lectura conjunta es más
-- informativa que un número único:
--
--   síntomas altos + discrepancia alta  -> patrón específico de dislexia
--   síntomas altos + discrepancia baja  -> conviene mirar más allá de la lectura
--
-- El índice usa peso igual para los seis. No es que se crea que pesan lo
-- mismo: es que no hay base para decir que no, y repartirlos a ojo sería
-- inventar precisión.

BEGIN;

-- La restricción de 021 ya obliga a que todo lo que no sea RIESGO tenga peso
-- cero, así que estos ítems no pueden alterar el puntaje ni por descuido.

INSERT INTO assessment.teacher_screening_items
    (item_code, prompt, weight, tags, source_note, scale, categoria, is_active)
VALUES
    ('d01_oral_vs_escrito',
     'Al hablar demuestra saber más de lo que refleja por escrito.',
     0, ARRAY['discrepancia','oral_escrito'],
     'PRODISLEX — Discrepancias: trabajo oral y trabajo escrito',
     '[{"label":"Nunca","value":0},{"label":"A veces","value":0.5},{"label":"Frecuente","value":1}]'::jsonb,
     'DISCREPANCIA', TRUE),

    ('d02_capacidad_vs_notas',
     'Parece más capaz de lo que indican sus calificaciones.',
     0, ARRAY['discrepancia','capacidad_rendimiento'],
     'PRODISLEX — Discrepancias: cociente intelectual y éxito escolar. Se '
     'formula como observación del docente porque no se dispone del CI',
     '[{"label":"Nunca","value":0},{"label":"A veces","value":0.5},{"label":"Frecuente","value":1}]'::jsonb,
     'DISCREPANCIA', TRUE),

    ('d03_entre_materias',
     'Le va claramente mejor en unas materias que en otras, sin que se explique por interés.',
     0, ARRAY['discrepancia','entre_materias'],
     'PRODISLEX — Discrepancias: rendimiento en distintas materias',
     '[{"label":"Nunca","value":0},{"label":"A veces","value":0.5},{"label":"Frecuente","value":1}]'::jsonb,
     'DISCREPANCIA', TRUE),

    ('d04_comprension_vs_memoria',
     'Entiende bien lo que se explica pero le cuesta recordarlo o recuperarlo después.',
     0, ARRAY['discrepancia','comprension_memoria'],
     'PRODISLEX — Discrepancias: comprensión y memoria',
     '[{"label":"Nunca","value":0},{"label":"A veces","value":0.5},{"label":"Frecuente","value":1}]'::jsonb,
     'DISCREPANCIA', TRUE),

    ('d05_dias_buenos_malos',
     'Su rendimiento varía mucho de un día a otro sin causa aparente.',
     0, ARRAY['discrepancia','variabilidad'],
     'PRODISLEX — Discrepancias: días buenos y días malos',
     '[{"label":"Nunca","value":0},{"label":"A veces","value":0.5},{"label":"Frecuente","value":1}]'::jsonb,
     'DISCREPANCIA', TRUE),

    ('d06_esfuerzo_vs_resultado',
     'Se esfuerza mucho más que sus compañeros para llegar a un resultado parecido o peor.',
     0, ARRAY['discrepancia','esfuerzo_resultado'],
     'PRODISLEX — Discrepancias: esfuerzo-trabajo y calidad del resultado final',
     '[{"label":"Nunca","value":0},{"label":"A veces","value":0.5},{"label":"Frecuente","value":1}]'::jsonb,
     'DISCREPANCIA', TRUE)
ON CONFLICT (item_code) DO NOTHING;

COMMIT;

-- ─── Verificación ────────────────────────────────────────────────────────────
--
--   SELECT categoria, count(*), sum(weight)
--     FROM assessment.teacher_screening_items
--    WHERE is_active GROUP BY categoria ORDER BY 1;
--
--   DISCREPANCIA      6    0.00
--   HISTORIA_CLINICA  5    0.00
--   RIESGO            8  100.00
--
-- Los de riesgo siguen definiendo la escala completa, así que el umbral de 50
-- que decide entre batería completa y rápida no se corrió.
