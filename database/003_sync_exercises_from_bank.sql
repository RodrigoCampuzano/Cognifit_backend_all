-- =============================================================
-- 003 — Sincroniza el banco de ejercicios del Recommendation Service (8002)
-- hacia intervention.exercises. Idempotente (ON CONFLICT exercise_code).
-- Generado automáticamente desde banco_ejercicios_intervencion.json (29 ejercicios).
-- =============================================================

INSERT INTO intervention.exercises
    (learning_path_id, title, exercise_type, difficulty, content, has_tts, has_stt, exercise_code, skill_target, objective, source_tags)
SELECT lp.id, $ej$¿Cuántas sílabas tiene?$ej$, 'CONCIENCIA_FONOLOGICA', 1, $ej${"exercise_id": "CF_silabas_N1", "tipo": "conciencia_fonologica", "subtipo": "segmentacion_silabica", "perfil_objetivo": ["fonologico", "mixto"], "nivel": 1, "grados": ["1", "2"], "titulo": "¿Cuántas sílabas tiene?", "instruccion": "Escucha la palabra y toca cuántas sílabas tiene.", "modalidad": "tactil_tts", "usa_tts": true, "usa_stt": false, "items": [{"palabra": "sol", "silabas": 1}, {"palabra": "casa", "silabas": 2}, {"palabra": "camino", "silabas": 3}, {"palabra": "mariposa", "silabas": 4}, {"palabra": "pan", "silabas": 1}, {"palabra": "libro", "silabas": 2}, {"palabra": "escuela", "silabas": 3}, {"palabra": "bicicleta", "silabas": 4}, {"palabra": "luz", "silabas": 1}, {"palabra": "perro", "silabas": 2}]}$ej$::jsonb, TRUE, FALSE, 'CF_silabas_N1', $ej$segmentacion_silabica$ej$, $ej$Escucha la palabra y toca cuántas sílabas tiene.$ej$, ARRAY['fonologico']::TEXT[]
FROM intervention.learning_paths lp WHERE lp.target_subtype = 'PHONOLOGICAL'
ON CONFLICT (exercise_code) WHERE exercise_code IS NOT NULL
DO UPDATE SET content=EXCLUDED.content, title=EXCLUDED.title, has_tts=EXCLUDED.has_tts,
    has_stt=EXCLUDED.has_stt, skill_target=EXCLUDED.skill_target, difficulty=EXCLUDED.difficulty;

INSERT INTO intervention.exercises
    (learning_path_id, title, exercise_type, difficulty, content, has_tts, has_stt, exercise_code, skill_target, objective, source_tags)
SELECT lp.id, $ej$¿Con qué sonido empieza?$ej$, 'CONCIENCIA_FONOLOGICA', 1, $ej${"exercise_id": "CF_fonema_inicial_N1", "tipo": "conciencia_fonologica", "subtipo": "fonema_inicial", "perfil_objetivo": ["fonologico", "mixto"], "nivel": 1, "grados": ["1", "2"], "titulo": "¿Con qué sonido empieza?", "instruccion": "Escucha la palabra y di con qué sonido empieza.", "modalidad": "stt_tts", "usa_tts": true, "usa_stt": true, "items": [{"palabra": "mama", "fonema_inicial": "m"}, {"palabra": "boca", "fonema_inicial": "b"}, {"palabra": "dedo", "fonema_inicial": "d"}, {"palabra": "pato", "fonema_inicial": "p"}, {"palabra": "luna", "fonema_inicial": "l"}, {"palabra": "sapo", "fonema_inicial": "s"}, {"palabra": "foca", "fonema_inicial": "f"}, {"palabra": "nido", "fonema_inicial": "n"}, {"palabra": "ropa", "fonema_inicial": "r"}, {"palabra": "taza", "fonema_inicial": "t"}]}$ej$::jsonb, TRUE, TRUE, 'CF_fonema_inicial_N1', $ej$fonema_inicial$ej$, $ej$Escucha la palabra y di con qué sonido empieza.$ej$, ARRAY['fonologico']::TEXT[]
FROM intervention.learning_paths lp WHERE lp.target_subtype = 'PHONOLOGICAL'
ON CONFLICT (exercise_code) WHERE exercise_code IS NOT NULL
DO UPDATE SET content=EXCLUDED.content, title=EXCLUDED.title, has_tts=EXCLUDED.has_tts,
    has_stt=EXCLUDED.has_stt, skill_target=EXCLUDED.skill_target, difficulty=EXCLUDED.difficulty;

INSERT INTO intervention.exercises
    (learning_path_id, title, exercise_type, difficulty, content, has_tts, has_stt, exercise_code, skill_target, objective, source_tags)
SELECT lp.id, $ej$¿Cuál rima?$ej$, 'CONCIENCIA_FONOLOGICA', 1, $ej${"exercise_id": "CF_rima_N1", "tipo": "conciencia_fonologica", "subtipo": "conciencia_rima", "perfil_objetivo": ["fonologico"], "nivel": 1, "grados": ["1", "2"], "titulo": "¿Cuál rima?", "instruccion": "Escucha la palabra y toca la imagen que rima con ella.", "modalidad": "tactil_tts", "usa_tts": true, "usa_stt": false, "items": [{"palabra_base": "sol", "opciones": ["col", "pan", "mesa", "libro"], "correcta": "col"}, {"palabra_base": "gato", "opciones": ["perro", "pato", "casa", "árbol"], "correcta": "pato"}, {"palabra_base": "pez", "opciones": ["tez", "sol", "luna", "campo"], "correcta": "tez"}, {"palabra_base": "flor", "opciones": ["calor", "mesa", "libro", "casa"], "correcta": "calor"}, {"palabra_base": "pan", "opciones": ["can", "sol", "mar", "loma"], "correcta": "can"}]}$ej$::jsonb, TRUE, FALSE, 'CF_rima_N1', $ej$conciencia_rima$ej$, $ej$Escucha la palabra y toca la imagen que rima con ella.$ej$, ARRAY['fonologico']::TEXT[]
FROM intervention.learning_paths lp WHERE lp.target_subtype = 'PHONOLOGICAL'
ON CONFLICT (exercise_code) WHERE exercise_code IS NOT NULL
DO UPDATE SET content=EXCLUDED.content, title=EXCLUDED.title, has_tts=EXCLUDED.has_tts,
    has_stt=EXCLUDED.has_stt, skill_target=EXCLUDED.skill_target, difficulty=EXCLUDED.difficulty;

INSERT INTO intervention.exercises
    (learning_path_id, title, exercise_type, difficulty, content, has_tts, has_stt, exercise_code, skill_target, objective, source_tags)
SELECT lp.id, $ej$Quita la sílaba$ej$, 'CONCIENCIA_FONOLOGICA', 2, $ej${"exercise_id": "CF_supresion_N1", "tipo": "conciencia_fonologica", "subtipo": "supresion_silabica", "perfil_objetivo": ["fonologico", "mixto"], "nivel": 2, "grados": ["2", "3"], "titulo": "Quita la sílaba", "instruccion": "Escucha la palabra. Quita la primera sílaba y di qué queda.", "modalidad": "stt_tts", "usa_tts": true, "usa_stt": true, "items": [{"palabra": "camino", "suprime": "ca", "resultado": "mino"}, {"palabra": "paloma", "suprime": "pa", "resultado": "loma"}, {"palabra": "maleta", "suprime": "ma", "resultado": "leta"}, {"palabra": "tomate", "suprime": "to", "resultado": "mate"}, {"palabra": "sábado", "suprime": "sá", "resultado": "bado"}]}$ej$::jsonb, TRUE, TRUE, 'CF_supresion_N1', $ej$supresion_silabica$ej$, $ej$Escucha la palabra. Quita la primera sílaba y di qué queda.$ej$, ARRAY['fonologico']::TEXT[]
FROM intervention.learning_paths lp WHERE lp.target_subtype = 'PHONOLOGICAL'
ON CONFLICT (exercise_code) WHERE exercise_code IS NOT NULL
DO UPDATE SET content=EXCLUDED.content, title=EXCLUDED.title, has_tts=EXCLUDED.has_tts,
    has_stt=EXCLUDED.has_stt, skill_target=EXCLUDED.skill_target, difficulty=EXCLUDED.difficulty;

INSERT INTO intervention.exercises
    (learning_path_id, title, exercise_type, difficulty, content, has_tts, has_stt, exercise_code, skill_target, objective, source_tags)
SELECT lp.id, $ej$Cambia el sonido$ej$, 'CONCIENCIA_FONOLOGICA', 3, $ej${"exercise_id": "CF_sustitucion_N1", "tipo": "conciencia_fonologica", "subtipo": "sustitucion_fonemica", "perfil_objetivo": ["fonologico"], "nivel": 3, "grados": ["2", "3"], "titulo": "Cambia el sonido", "instruccion": "Cambia el primer sonido de la palabra por el que te digo.", "modalidad": "stt_tts", "usa_tts": true, "usa_stt": true, "items": [{"palabra": "boca", "cambia_por": "f", "resultado": "foca"}, {"palabra": "mesa", "cambia_por": "p", "resultado": "pesa"}, {"palabra": "tela", "cambia_por": "s", "resultado": "sela"}, {"palabra": "doma", "cambia_por": "r", "resultado": "roma"}, {"palabra": "pala", "cambia_por": "b", "resultado": "bala"}]}$ej$::jsonb, TRUE, TRUE, 'CF_sustitucion_N1', $ej$sustitucion_fonemica$ej$, $ej$Cambia el primer sonido de la palabra por el que te digo.$ej$, ARRAY['fonologico']::TEXT[]
FROM intervention.learning_paths lp WHERE lp.target_subtype = 'PHONOLOGICAL'
ON CONFLICT (exercise_code) WHERE exercise_code IS NOT NULL
DO UPDATE SET content=EXCLUDED.content, title=EXCLUDED.title, has_tts=EXCLUDED.has_tts,
    has_stt=EXCLUDED.has_stt, skill_target=EXCLUDED.skill_target, difficulty=EXCLUDED.difficulty;

INSERT INTO intervention.exercises
    (learning_path_id, title, exercise_type, difficulty, content, has_tts, has_stt, exercise_code, skill_target, objective, source_tags)
SELECT lp.id, $ej$Lee esta palabra inventada$ej$, 'PSEUDOPALABRAS', 1, $ej${"exercise_id": "PS_cv_N1", "tipo": "pseudopalabras", "subtipo": "lectura_pseudopalabras", "perfil_objetivo": ["fonologico", "visual", "mixto"], "nivel": 1, "grados": ["1", "2"], "titulo": "Lee esta palabra inventada", "instruccion": "Esta palabra no existe, pero trata de leerla como suena.", "modalidad": "stt", "usa_tts": false, "usa_stt": true, "items": [{"target": "mibo", "pares_confusion": ["b", "d"]}, {"target": "dapi", "pares_confusion": ["d", "b"]}, {"target": "rano", "pares_confusion": []}, {"target": "telo", "pares_confusion": []}, {"target": "bado", "pares_confusion": ["b", "d"], "fuente": "TEDE_EE18"}, {"target": "dipo", "pares_confusion": ["d", "b"], "fuente": "TEDE_EE18"}, {"target": "numo", "pares_confusion": [], "fuente": "TEDE_EE18"}, {"target": "quibo", "pares_confusion": ["q", "p"]}, {"target": "fuma", "pares_confusion": []}, {"target": "saute", "pares_confusion": [], "fuente": "TEDE_EE18"}]}$ej$::jsonb, FALSE, TRUE, 'PS_cv_N1', $ej$lectura_pseudopalabras$ej$, $ej$Esta palabra no existe, pero trata de leerla como suena.$ej$, ARRAY['fonologico']::TEXT[]
FROM intervention.learning_paths lp WHERE lp.target_subtype = 'PHONOLOGICAL'
ON CONFLICT (exercise_code) WHERE exercise_code IS NOT NULL
DO UPDATE SET content=EXCLUDED.content, title=EXCLUDED.title, has_tts=EXCLUDED.has_tts,
    has_stt=EXCLUDED.has_stt, skill_target=EXCLUDED.skill_target, difficulty=EXCLUDED.difficulty;

INSERT INTO intervention.exercises
    (learning_path_id, title, exercise_type, difficulty, content, has_tts, has_stt, exercise_code, skill_target, objective, source_tags)
SELECT lp.id, $ej$Lee esta palabra inventada (con apoyo)$ej$, 'PSEUDOPALABRAS', 1, $ej${"exercise_id": "PS_cv_N1_refuerzo", "tipo": "pseudopalabras", "subtipo": "lectura_pseudopalabras", "perfil_objetivo": ["fonologico", "mixto"], "nivel": 1, "grados": ["1", "2"], "titulo": "Lee esta palabra inventada (con apoyo)", "instruccion": "Escucha primero cómo suena y luego léela tú.", "modalidad": "stt_tts", "usa_tts": true, "usa_stt": true, "nota": "TTS lee primero el target para dar modelo auditivo", "items": [{"target": "mibo"}, {"target": "telo"}, {"target": "rano"}, {"target": "fuma"}, {"target": "pilo"}, {"target": "nusa"}, {"target": "bapi", "fuente": "TEDE_EE18"}, {"target": "quido", "fuente": "TEDE_EE18"}]}$ej$::jsonb, TRUE, TRUE, 'PS_cv_N1_refuerzo', $ej$lectura_pseudopalabras$ej$, $ej$Escucha primero cómo suena y luego léela tú.$ej$, ARRAY['fonologico']::TEXT[]
FROM intervention.learning_paths lp WHERE lp.target_subtype = 'PHONOLOGICAL'
ON CONFLICT (exercise_code) WHERE exercise_code IS NOT NULL
DO UPDATE SET content=EXCLUDED.content, title=EXCLUDED.title, has_tts=EXCLUDED.has_tts,
    has_stt=EXCLUDED.has_stt, skill_target=EXCLUDED.skill_target, difficulty=EXCLUDED.difficulty;

INSERT INTO intervention.exercises
    (learning_path_id, title, exercise_type, difficulty, content, has_tts, has_stt, exercise_code, skill_target, objective, source_tags)
SELECT lp.id, $ej$Lee esta palabra inventada (difícil)$ej$, 'PSEUDOPALABRAS', 2, $ej${"exercise_id": "PS_cvc_N2", "tipo": "pseudopalabras", "subtipo": "lectura_pseudopalabras", "perfil_objetivo": ["fonologico", "mixto"], "nivel": 2, "grados": ["2", "3"], "titulo": "Lee esta palabra inventada (difícil)", "instruccion": "Esta palabra inventada es más larga. Léela despacio.", "modalidad": "stt", "usa_tts": false, "usa_stt": true, "items": [{"target": "nomino", "fuente": "TEDE_EE17"}, {"target": "rechido", "fuente": "TEDE_EE17"}, {"target": "plime"}, {"target": "dubre"}, {"target": "tribo"}, {"target": "dubopi", "fuente": "TEDE_EE18"}, {"target": "pebade", "fuente": "TEDE_EE18"}, {"target": "milato"}, {"target": "fasulo"}, {"target": "tronibo"}]}$ej$::jsonb, FALSE, TRUE, 'PS_cvc_N2', $ej$lectura_pseudopalabras$ej$, $ej$Esta palabra inventada es más larga. Léela despacio.$ej$, ARRAY['fonologico']::TEXT[]
FROM intervention.learning_paths lp WHERE lp.target_subtype = 'PHONOLOGICAL'
ON CONFLICT (exercise_code) WHERE exercise_code IS NOT NULL
DO UPDATE SET content=EXCLUDED.content, title=EXCLUDED.title, has_tts=EXCLUDED.has_tts,
    has_stt=EXCLUDED.has_stt, skill_target=EXCLUDED.skill_target, difficulty=EXCLUDED.difficulty;

INSERT INTO intervention.exercises
    (learning_path_id, title, exercise_type, difficulty, content, has_tts, has_stt, exercise_code, skill_target, objective, source_tags)
SELECT lp.id, $ej$Escribe lo que escuchas$ej$, 'DICTADO', 1, $ej${"exercise_id": "DIC_palabras_simples_N1", "tipo": "dictado", "subtipo": "dictado_palabras", "perfil_objetivo": ["fonologico", "visual", "mixto"], "nivel": 1, "grados": ["1", "2"], "titulo": "Escribe lo que escuchas", "instruccion": "Escucha la palabra y escríbela.", "modalidad": "teclado_tts", "usa_tts": true, "usa_stt": false, "items": [{"target": "casa"}, {"target": "mesa"}, {"target": "pato"}, {"target": "libro"}, {"target": "boca", "riesgo_ROT": "b/d"}, {"target": "dedo", "riesgo_ROT": "d/b"}, {"target": "palo", "riesgo_ROT": "p/b"}, {"target": "luna"}, {"target": "sol"}, {"target": "perro"}]}$ej$::jsonb, TRUE, FALSE, 'DIC_palabras_simples_N1', $ej$dictado_palabras$ej$, $ej$Escucha la palabra y escríbela.$ej$, ARRAY['fonologico']::TEXT[]
FROM intervention.learning_paths lp WHERE lp.target_subtype = 'PHONOLOGICAL'
ON CONFLICT (exercise_code) WHERE exercise_code IS NOT NULL
DO UPDATE SET content=EXCLUDED.content, title=EXCLUDED.title, has_tts=EXCLUDED.has_tts,
    has_stt=EXCLUDED.has_stt, skill_target=EXCLUDED.skill_target, difficulty=EXCLUDED.difficulty;

INSERT INTO intervention.exercises
    (learning_path_id, title, exercise_type, difficulty, content, has_tts, has_stt, exercise_code, skill_target, objective, source_tags)
SELECT lp.id, $ej$Escribe la frase$ej$, 'DICTADO', 2, $ej${"exercise_id": "DIC_frases_cortas_N1", "tipo": "dictado", "subtipo": "dictado_frases", "perfil_objetivo": ["fonologico", "mixto"], "nivel": 2, "grados": ["2", "3"], "titulo": "Escribe la frase", "instruccion": "Escucha la frase completa y escríbela.", "modalidad": "teclado_tts", "usa_tts": true, "usa_stt": false, "items": [{"target": "El gato bebe leche."}, {"target": "La paloma vuela alto."}, {"target": "Mi bicicleta es roja."}, {"target": "El perro ladra fuerte."}, {"target": "La mariposa tiene alas."}]}$ej$::jsonb, TRUE, FALSE, 'DIC_frases_cortas_N1', $ej$dictado_frases$ej$, $ej$Escucha la frase completa y escríbela.$ej$, ARRAY['fonologico']::TEXT[]
FROM intervention.learning_paths lp WHERE lp.target_subtype = 'PHONOLOGICAL'
ON CONFLICT (exercise_code) WHERE exercise_code IS NOT NULL
DO UPDATE SET content=EXCLUDED.content, title=EXCLUDED.title, has_tts=EXCLUDED.has_tts,
    has_stt=EXCLUDED.has_stt, skill_target=EXCLUDED.skill_target, difficulty=EXCLUDED.difficulty;

INSERT INTO intervention.exercises
    (learning_path_id, title, exercise_type, difficulty, content, has_tts, has_stt, exercise_code, skill_target, objective, source_tags)
SELECT lp.id, $ej$¿Es b o es d?$ej$, 'VISUAL', 1, $ej${"exercise_id": "VIS_discriminacion_bd_N1", "tipo": "visual", "subtipo": "discriminacion_letras", "perfil_objetivo": ["visual", "mixto"], "nivel": 1, "grados": ["1", "2", "3"], "titulo": "¿Es b o es d?", "instruccion": "Toca la letra correcta que ves en pantalla.", "modalidad": "tactil", "usa_tts": false, "usa_stt": false, "items": [{"estimulo": "b", "opciones": ["b", "d"], "correcta": "b"}, {"estimulo": "d", "opciones": ["b", "d"], "correcta": "d"}, {"estimulo": "b", "opciones": ["b", "d"], "correcta": "b"}, {"estimulo": "d", "opciones": ["d", "b"], "correcta": "d"}, {"estimulo": "b", "opciones": ["d", "b"], "correcta": "b"}, {"estimulo": "d", "opciones": ["b", "d"], "correcta": "d"}, {"estimulo": "b", "opciones": ["b", "d"], "correcta": "b"}, {"estimulo": "d", "opciones": ["d", "b"], "correcta": "d"}, {"estimulo": "b", "opciones": ["b", "d"], "correcta": "b"}, {"estimulo": "d", "opciones": ["b", "d"], "correcta": "d"}]}$ej$::jsonb, FALSE, FALSE, 'VIS_discriminacion_bd_N1', $ej$discriminacion_letras$ej$, $ej$Toca la letra correcta que ves en pantalla.$ej$, ARRAY['visual']::TEXT[]
FROM intervention.learning_paths lp WHERE lp.target_subtype = 'VISUAL_SURFACE'
ON CONFLICT (exercise_code) WHERE exercise_code IS NOT NULL
DO UPDATE SET content=EXCLUDED.content, title=EXCLUDED.title, has_tts=EXCLUDED.has_tts,
    has_stt=EXCLUDED.has_stt, skill_target=EXCLUDED.skill_target, difficulty=EXCLUDED.difficulty;

INSERT INTO intervention.exercises
    (learning_path_id, title, exercise_type, difficulty, content, has_tts, has_stt, exercise_code, skill_target, objective, source_tags)
SELECT lp.id, $ej$¿Es p o es q?$ej$, 'VISUAL', 1, $ej${"exercise_id": "VIS_discriminacion_pq_N1", "tipo": "visual", "subtipo": "discriminacion_letras", "perfil_objetivo": ["visual", "mixto"], "nivel": 1, "grados": ["1", "2", "3"], "titulo": "¿Es p o es q?", "instruccion": "Toca la letra correcta que ves en pantalla.", "modalidad": "tactil", "usa_tts": false, "usa_stt": false, "items": [{"estimulo": "p", "opciones": ["p", "q"], "correcta": "p"}, {"estimulo": "q", "opciones": ["p", "q"], "correcta": "q"}, {"estimulo": "p", "opciones": ["q", "p"], "correcta": "p"}, {"estimulo": "q", "opciones": ["q", "p"], "correcta": "q"}, {"estimulo": "p", "opciones": ["p", "q"], "correcta": "p"}, {"estimulo": "q", "opciones": ["p", "q"], "correcta": "q"}, {"estimulo": "p", "opciones": ["q", "p"], "correcta": "p"}, {"estimulo": "q", "opciones": ["p", "q"], "correcta": "q"}, {"estimulo": "p", "opciones": ["p", "q"], "correcta": "p"}, {"estimulo": "q", "opciones": ["q", "p"], "correcta": "q"}]}$ej$::jsonb, FALSE, FALSE, 'VIS_discriminacion_pq_N1', $ej$discriminacion_letras$ej$, $ej$Toca la letra correcta que ves en pantalla.$ej$, ARRAY['visual']::TEXT[]
FROM intervention.learning_paths lp WHERE lp.target_subtype = 'VISUAL_SURFACE'
ON CONFLICT (exercise_code) WHERE exercise_code IS NOT NULL
DO UPDATE SET content=EXCLUDED.content, title=EXCLUDED.title, has_tts=EXCLUDED.has_tts,
    has_stt=EXCLUDED.has_stt, skill_target=EXCLUDED.skill_target, difficulty=EXCLUDED.difficulty;

INSERT INTO intervention.exercises
    (learning_path_id, title, exercise_type, difficulty, content, has_tts, has_stt, exercise_code, skill_target, objective, source_tags)
SELECT lp.id, $ej$¿Qué palabra viste?$ej$, 'VISUAL', 1, $ej${"exercise_id": "VIS_memoria_palabras_N1", "tipo": "visual", "subtipo": "memoria_visual_palabras", "perfil_objetivo": ["visual"], "nivel": 1, "grados": ["1", "2", "3"], "titulo": "¿Qué palabra viste?", "instruccion": "Mira la palabra por 3 segundos. Luego toca cuál era.", "modalidad": "tactil", "usa_tts": false, "usa_stt": false, "tiempo_exposicion_ms": 3000, "items": [{"palabra": "boca", "distractor_1": "doca", "distractor_2": "poca"}, {"palabra": "palo", "distractor_1": "balo", "distractor_2": "dalo"}, {"palabra": "dedo", "distractor_1": "bebo", "distractor_2": "pelo"}, {"palabra": "queso", "distractor_1": "gueso", "distractor_2": "cueso"}, {"palabra": "bebe", "distractor_1": "debe", "distractor_2": "pebe"}]}$ej$::jsonb, FALSE, FALSE, 'VIS_memoria_palabras_N1', $ej$memoria_visual_palabras$ej$, $ej$Mira la palabra por 3 segundos. Luego toca cuál era.$ej$, ARRAY['visual']::TEXT[]
FROM intervention.learning_paths lp WHERE lp.target_subtype = 'VISUAL_SURFACE'
ON CONFLICT (exercise_code) WHERE exercise_code IS NOT NULL
DO UPDATE SET content=EXCLUDED.content, title=EXCLUDED.title, has_tts=EXCLUDED.has_tts,
    has_stt=EXCLUDED.has_stt, skill_target=EXCLUDED.skill_target, difficulty=EXCLUDED.difficulty;

INSERT INTO intervention.exercises
    (learning_path_id, title, exercise_type, difficulty, content, has_tts, has_stt, exercise_code, skill_target, objective, source_tags)
SELECT lp.id, $ej$¿Son iguales o diferentes?$ej$, 'VISUAL', 2, $ej${"exercise_id": "VIS_parejas_palabras_N1", "tipo": "visual", "subtipo": "detective_errores", "perfil_objetivo": ["visual"], "nivel": 2, "grados": ["2", "3", "4"], "titulo": "¿Son iguales o diferentes?", "instruccion": "Mira las dos palabras. ¿Son iguales o diferentes?", "modalidad": "tactil", "usa_tts": false, "usa_stt": false, "items": [{"par": ["boca", "doca"], "son_iguales": false}, {"par": ["mesa", "mesa"], "son_iguales": true}, {"par": ["pato", "bato"], "son_iguales": false}, {"par": ["casa", "casa"], "son_iguales": true}, {"par": ["queso", "gueso"], "son_iguales": false}, {"par": ["libro", "libro"], "son_iguales": true}, {"par": ["dedo", "bebo"], "son_iguales": false}, {"par": ["paloma", "paloma"], "son_iguales": true}]}$ej$::jsonb, FALSE, FALSE, 'VIS_parejas_palabras_N1', $ej$detective_errores$ej$, $ej$Mira las dos palabras. ¿Son iguales o diferentes?$ej$, ARRAY['visual']::TEXT[]
FROM intervention.learning_paths lp WHERE lp.target_subtype = 'VISUAL_SURFACE'
ON CONFLICT (exercise_code) WHERE exercise_code IS NOT NULL
DO UPDATE SET content=EXCLUDED.content, title=EXCLUDED.title, has_tts=EXCLUDED.has_tts,
    has_stt=EXCLUDED.has_stt, skill_target=EXCLUDED.skill_target, difficulty=EXCLUDED.difficulty;

INSERT INTO intervention.exercises
    (learning_path_id, title, exercise_type, difficulty, content, has_tts, has_stt, exercise_code, skill_target, objective, source_tags)
SELECT lp.id, $ej$Traza la letra$ej$, 'VISUAL', 1, $ej${"exercise_id": "VIS_trazado_letras_N1", "tipo": "visual", "subtipo": "trazado_cinestesico", "perfil_objetivo": ["visual", "mixto"], "nivel": 1, "grados": ["1", "2"], "titulo": "Traza la letra", "instruccion": "Sigue la línea punteada para trazar la letra con el dedo.", "modalidad": "tactil_canvas", "usa_tts": true, "usa_stt": false, "nota": "Requiere pantalla táctil. Flutter Canvas + GestureDetector.", "items": [{"letra": "b", "descripcion_trazo": "Línea recta hacia abajo, luego círculo a la derecha"}, {"letra": "d", "descripcion_trazo": "Círculo primero, luego línea recta hacia arriba"}, {"letra": "p", "descripcion_trazo": "Línea recta hacia abajo, círculo a la derecha en la mitad"}, {"letra": "q", "descripcion_trazo": "Círculo, luego línea recta hacia abajo a la derecha"}]}$ej$::jsonb, TRUE, FALSE, 'VIS_trazado_letras_N1', $ej$trazado_cinestesico$ej$, $ej$Sigue la línea punteada para trazar la letra con el dedo.$ej$, ARRAY['visual']::TEXT[]
FROM intervention.learning_paths lp WHERE lp.target_subtype = 'VISUAL_SURFACE'
ON CONFLICT (exercise_code) WHERE exercise_code IS NOT NULL
DO UPDATE SET content=EXCLUDED.content, title=EXCLUDED.title, has_tts=EXCLUDED.has_tts,
    has_stt=EXCLUDED.has_stt, skill_target=EXCLUDED.skill_target, difficulty=EXCLUDED.difficulty;

INSERT INTO intervention.exercises
    (learning_path_id, title, exercise_type, difficulty, content, has_tts, has_stt, exercise_code, skill_target, objective, source_tags)
SELECT lp.id, $ej$Lee con el puntero$ej$, 'LECTURA', 1, $ej${"exercise_id": "LEC_guiada_N1", "tipo": "lectura", "subtipo": "lectura_guiada_visual", "perfil_objetivo": ["visual"], "nivel": 1, "grados": ["1", "2"], "titulo": "Lee con el puntero", "instruccion": "Lee siguiendo el puntero que va avanzando palabra por palabra.", "modalidad": "lectura_punteada", "usa_tts": true, "usa_stt": true, "texto": "El sol sale en la mañana. Los pájaros cantan en el árbol. Los niños van a la escuela.", "velocidad_palabras_por_minuto": 40}$ej$::jsonb, TRUE, TRUE, 'LEC_guiada_N1', $ej$lectura_guiada_visual$ej$, $ej$Lee siguiendo el puntero que va avanzando palabra por palabra.$ej$, ARRAY['visual']::TEXT[]
FROM intervention.learning_paths lp WHERE lp.target_subtype = 'VISUAL_SURFACE'
ON CONFLICT (exercise_code) WHERE exercise_code IS NOT NULL
DO UPDATE SET content=EXCLUDED.content, title=EXCLUDED.title, has_tts=EXCLUDED.has_tts,
    has_stt=EXCLUDED.has_stt, skill_target=EXCLUDED.skill_target, difficulty=EXCLUDED.difficulty;

INSERT INTO intervention.exercises
    (learning_path_id, title, exercise_type, difficulty, content, has_tts, has_stt, exercise_code, skill_target, objective, source_tags)
SELECT lp.id, $ej$Lee el mismo texto 3 veces$ej$, 'LECTURA', 1, $ej${"exercise_id": "LEC_repetida_N1", "tipo": "lectura", "subtipo": "lectura_repetida", "perfil_objetivo": ["fluidez"], "nivel": 1, "grados": ["1", "2", "3"], "titulo": "Lee el mismo texto 3 veces", "instruccion": "Lee este texto en voz alta. Lo leerás 3 veces para practicar la fluidez.", "modalidad": "stt", "usa_tts": false, "usa_stt": true, "repeticiones": 3, "texto": "María tiene una perrita llamada Luna. Luna es café con manchas blancas. Todos los días María la saca a pasear al parque."}$ej$::jsonb, FALSE, TRUE, 'LEC_repetida_N1', $ej$lectura_repetida$ej$, $ej$Lee este texto en voz alta. Lo leerás 3 veces para practicar la fluidez.$ej$, ARRAY['fluidez']::TEXT[]
FROM intervention.learning_paths lp WHERE lp.target_subtype = 'FLUENCY'
ON CONFLICT (exercise_code) WHERE exercise_code IS NOT NULL
DO UPDATE SET content=EXCLUDED.content, title=EXCLUDED.title, has_tts=EXCLUDED.has_tts,
    has_stt=EXCLUDED.has_stt, skill_target=EXCLUDED.skill_target, difficulty=EXCLUDED.difficulty;

INSERT INTO intervention.exercises
    (learning_path_id, title, exercise_type, difficulty, content, has_tts, has_stt, exercise_code, skill_target, objective, source_tags)
SELECT lp.id, $ej$Lee el texto con apoyo$ej$, 'LECTURA', 1, $ej${"exercise_id": "LEC_repetida_N1_refuerzo", "tipo": "lectura", "subtipo": "lectura_repetida", "perfil_objetivo": ["fluidez"], "nivel": 1, "grados": ["1", "2"], "titulo": "Lee el texto con apoyo", "instruccion": "Escucha primero cómo se lee, luego léelo tú 3 veces.", "modalidad": "stt_tts", "usa_tts": true, "usa_stt": true, "repeticiones": 3, "texto": "El río corre por el campo. Los peces nadan en el agua fría. Un niño pesca desde la orilla."}$ej$::jsonb, TRUE, TRUE, 'LEC_repetida_N1_refuerzo', $ej$lectura_repetida$ej$, $ej$Escucha primero cómo se lee, luego léelo tú 3 veces.$ej$, ARRAY['fluidez']::TEXT[]
FROM intervention.learning_paths lp WHERE lp.target_subtype = 'FLUENCY'
ON CONFLICT (exercise_code) WHERE exercise_code IS NOT NULL
DO UPDATE SET content=EXCLUDED.content, title=EXCLUDED.title, has_tts=EXCLUDED.has_tts,
    has_stt=EXCLUDED.has_stt, skill_target=EXCLUDED.skill_target, difficulty=EXCLUDED.difficulty;

INSERT INTO intervention.exercises
    (learning_path_id, title, exercise_type, difficulty, content, has_tts, has_stt, exercise_code, skill_target, objective, source_tags)
SELECT lp.id, $ej$Lee el texto más largo (3 veces)$ej$, 'LECTURA', 2, $ej${"exercise_id": "LEC_repetida_N2", "tipo": "lectura", "subtipo": "lectura_repetida", "perfil_objetivo": ["fluidez"], "nivel": 2, "grados": ["3", "4", "5"], "titulo": "Lee el texto más largo (3 veces)", "instruccion": "Lee este texto en voz alta 3 veces. Intenta leer más rápido en cada lectura.", "modalidad": "stt", "usa_tts": false, "usa_stt": true, "repeticiones": 3, "texto": "La selva tropical es uno de los ecosistemas más ricos del planeta. En ella viven miles de especies de plantas y animales. Los monos saltan de árbol en árbol buscando frutas. Las serpientes se deslizan entre las hojas del suelo. Cada ser vivo tiene un papel importante en este ecosistema."}$ej$::jsonb, FALSE, TRUE, 'LEC_repetida_N2', $ej$lectura_repetida$ej$, $ej$Lee este texto en voz alta 3 veces. Intenta leer más rápido en cada lectura.$ej$, ARRAY['fluidez']::TEXT[]
FROM intervention.learning_paths lp WHERE lp.target_subtype = 'FLUENCY'
ON CONFLICT (exercise_code) WHERE exercise_code IS NOT NULL
DO UPDATE SET content=EXCLUDED.content, title=EXCLUDED.title, has_tts=EXCLUDED.has_tts,
    has_stt=EXCLUDED.has_stt, skill_target=EXCLUDED.skill_target, difficulty=EXCLUDED.difficulty;

INSERT INTO intervention.exercises
    (learning_path_id, title, exercise_type, difficulty, content, has_tts, has_stt, exercise_code, skill_target, objective, source_tags)
SELECT lp.id, $ej$Lee a tu ritmo (con temporizador amable)$ej$, 'LECTURA', 1, $ej${"exercise_id": "LEC_temporizador_N1", "tipo": "lectura", "subtipo": "lectura_con_tiempo", "perfil_objetivo": ["fluidez"], "nivel": 1, "grados": ["1", "2", "3"], "titulo": "Lee a tu ritmo (con temporizador amable)", "instruccion": "Lee el texto en voz alta. No hay prisa — el temporizador te muestra cuánto tardas.", "modalidad": "stt", "usa_tts": false, "usa_stt": true, "meta_palabras_por_minuto": 40, "texto": "Carlos tiene siete años. Le gusta jugar fútbol con sus amigos. Su equipo favorito es el de su escuela. Cuando anota un gol, todos lo felicitan."}$ej$::jsonb, FALSE, TRUE, 'LEC_temporizador_N1', $ej$lectura_con_tiempo$ej$, $ej$Lee el texto en voz alta. No hay prisa — el temporizador te muestra cuánto tardas.$ej$, ARRAY['fluidez']::TEXT[]
FROM intervention.learning_paths lp WHERE lp.target_subtype = 'FLUENCY'
ON CONFLICT (exercise_code) WHERE exercise_code IS NOT NULL
DO UPDATE SET content=EXCLUDED.content, title=EXCLUDED.title, has_tts=EXCLUDED.has_tts,
    has_stt=EXCLUDED.has_stt, skill_target=EXCLUDED.skill_target, difficulty=EXCLUDED.difficulty;

INSERT INTO intervention.exercises
    (learning_path_id, title, exercise_type, difficulty, content, has_tts, has_stt, exercise_code, skill_target, objective, source_tags)
SELECT lp.id, $ej$Lee rápido (temporizador)$ej$, 'LECTURA', 2, $ej${"exercise_id": "LEC_temporizador_N2", "tipo": "lectura", "subtipo": "lectura_con_tiempo", "perfil_objetivo": ["fluidez"], "nivel": 2, "grados": ["3", "4", "5"], "titulo": "Lee rápido (temporizador)", "instruccion": "Lee el texto lo más rápido que puedas sin perder la comprensión.", "modalidad": "stt", "usa_tts": false, "usa_stt": true, "meta_palabras_por_minuto": 70, "texto": "El volcán entró en erupción hace miles de años y cubrió toda la ciudad de lava. Los arqueólogos encontraron monedas, herramientas y restos de casas perfectamente conservados bajo la ceniza. Este hallazgo nos enseña cómo vivían las personas hace mucho tiempo."}$ej$::jsonb, FALSE, TRUE, 'LEC_temporizador_N2', $ej$lectura_con_tiempo$ej$, $ej$Lee el texto lo más rápido que puedas sin perder la comprensión.$ej$, ARRAY['fluidez']::TEXT[]
FROM intervention.learning_paths lp WHERE lp.target_subtype = 'FLUENCY'
ON CONFLICT (exercise_code) WHERE exercise_code IS NOT NULL
DO UPDATE SET content=EXCLUDED.content, title=EXCLUDED.title, has_tts=EXCLUDED.has_tts,
    has_stt=EXCLUDED.has_stt, skill_target=EXCLUDED.skill_target, difficulty=EXCLUDED.difficulty;

INSERT INTO intervention.exercises
    (learning_path_id, title, exercise_type, difficulty, content, has_tts, has_stt, exercise_code, skill_target, objective, source_tags)
SELECT lp.id, $ej$Nombra las letras rápido$ej$, 'DENOMINACION_RAPIDA', 1, $ej${"exercise_id": "DEN_rapid_letras_N1", "tipo": "denominacion_rapida", "subtipo": "letras", "perfil_objetivo": ["visual", "fluidez"], "nivel": 1, "grados": ["1", "2", "3"], "titulo": "Nombra las letras rápido", "instruccion": "Nombra cada letra lo más rápido que puedas.", "modalidad": "stt", "usa_tts": false, "usa_stt": true, "referencia_banco": "DEN_LETRAS_N1"}$ej$::jsonb, FALSE, TRUE, 'DEN_rapid_letras_N1', $ej$letras$ej$, $ej$Nombra cada letra lo más rápido que puedas.$ej$, ARRAY['visual']::TEXT[]
FROM intervention.learning_paths lp WHERE lp.target_subtype = 'VISUAL_SURFACE'
ON CONFLICT (exercise_code) WHERE exercise_code IS NOT NULL
DO UPDATE SET content=EXCLUDED.content, title=EXCLUDED.title, has_tts=EXCLUDED.has_tts,
    has_stt=EXCLUDED.has_stt, skill_target=EXCLUDED.skill_target, difficulty=EXCLUDED.difficulty;

INSERT INTO intervention.exercises
    (learning_path_id, title, exercise_type, difficulty, content, has_tts, has_stt, exercise_code, skill_target, objective, source_tags)
SELECT lp.id, $ej$Nombra los colores rápido$ej$, 'DENOMINACION_RAPIDA', 1, $ej${"exercise_id": "DEN_rapid_colores_N1", "tipo": "denominacion_rapida", "subtipo": "colores", "perfil_objetivo": ["fluidez"], "nivel": 1, "grados": ["1", "2", "3"], "titulo": "Nombra los colores rápido", "instruccion": "Nombra el color de cada círculo lo más rápido que puedas.", "modalidad": "stt", "usa_tts": false, "usa_stt": true, "referencia_banco": "DEN_COLORES_N1"}$ej$::jsonb, FALSE, TRUE, 'DEN_rapid_colores_N1', $ej$colores$ej$, $ej$Nombra el color de cada círculo lo más rápido que puedas.$ej$, ARRAY['fluidez']::TEXT[]
FROM intervention.learning_paths lp WHERE lp.target_subtype = 'FLUENCY'
ON CONFLICT (exercise_code) WHERE exercise_code IS NOT NULL
DO UPDATE SET content=EXCLUDED.content, title=EXCLUDED.title, has_tts=EXCLUDED.has_tts,
    has_stt=EXCLUDED.has_stt, skill_target=EXCLUDED.skill_target, difficulty=EXCLUDED.difficulty;

INSERT INTO intervention.exercises
    (learning_path_id, title, exercise_type, difficulty, content, has_tts, has_stt, exercise_code, skill_target, objective, source_tags)
SELECT lp.id, $ej$Nombra los dibujos rápido$ej$, 'DENOMINACION_RAPIDA', 1, $ej${"exercise_id": "DEN_rapid_objetos_N1", "tipo": "denominacion_rapida", "subtipo": "objetos", "perfil_objetivo": ["fluidez", "visual"], "nivel": 1, "grados": ["1", "2", "3"], "titulo": "Nombra los dibujos rápido", "instruccion": "Nombra cada dibujo lo más rápido que puedas.", "modalidad": "stt", "usa_tts": false, "usa_stt": true, "referencia_banco": "DEN_OBJETOS_N1"}$ej$::jsonb, FALSE, TRUE, 'DEN_rapid_objetos_N1', $ej$objetos$ej$, $ej$Nombra cada dibujo lo más rápido que puedas.$ej$, ARRAY['fluidez']::TEXT[]
FROM intervention.learning_paths lp WHERE lp.target_subtype = 'FLUENCY'
ON CONFLICT (exercise_code) WHERE exercise_code IS NOT NULL
DO UPDATE SET content=EXCLUDED.content, title=EXCLUDED.title, has_tts=EXCLUDED.has_tts,
    has_stt=EXCLUDED.has_stt, skill_target=EXCLUDED.skill_target, difficulty=EXCLUDED.difficulty;

INSERT INTO intervention.exercises
    (learning_path_id, title, exercise_type, difficulty, content, has_tts, has_stt, exercise_code, skill_target, objective, source_tags)
SELECT lp.id, $ej$Lee con apoyo de voz$ej$, 'LECTURA', 1, $ej${"exercise_id": "TTS_lectura_guiada_N1", "tipo": "lectura", "subtipo": "tts_apoyo_lectura", "perfil_objetivo": ["fonologico", "mixto", "fluidez"], "nivel": 1, "grados": ["1", "2", "3"], "titulo": "Lee con apoyo de voz", "instruccion": "El sistema leerá cada frase primero. Luego la lees tú.", "modalidad": "stt_tts", "usa_tts": true, "usa_stt": true, "textos": ["Mi mamá me mima.", "El sol sale por las mañanas.", "Los patos nadan en el lago.", "Ana come una manzana roja.", "El perro juega con la pelota."]}$ej$::jsonb, TRUE, TRUE, 'TTS_lectura_guiada_N1', $ej$tts_apoyo_lectura$ej$, $ej$El sistema leerá cada frase primero. Luego la lees tú.$ej$, ARRAY['fonologico']::TEXT[]
FROM intervention.learning_paths lp WHERE lp.target_subtype = 'PHONOLOGICAL'
ON CONFLICT (exercise_code) WHERE exercise_code IS NOT NULL
DO UPDATE SET content=EXCLUDED.content, title=EXCLUDED.title, has_tts=EXCLUDED.has_tts,
    has_stt=EXCLUDED.has_stt, skill_target=EXCLUDED.skill_target, difficulty=EXCLUDED.difficulty;

INSERT INTO intervention.exercises
    (learning_path_id, title, exercise_type, difficulty, content, has_tts, has_stt, exercise_code, skill_target, objective, source_tags)
SELECT lp.id, $ej$Sílabas de colores$ej$, 'MULTIMODAL', 1, $ej${"exercise_id": "MULTI_silabas_cromaticas_N1", "tipo": "multimodal", "subtipo": "silabas_con_color", "perfil_objetivo": ["mixto", "fonologico"], "nivel": 1, "grados": ["1", "2", "3"], "titulo": "Sílabas de colores", "instruccion": "Cada sílaba tiene un color diferente. Lee la palabra siguiendo los colores.", "modalidad": "tactil_tts", "usa_tts": true, "usa_stt": true, "nota": "En Flutter: cada sílaba se muestra en RichText con color distinto. El alumno toca cada sílaba para escucharla.", "items": [{"palabra": "ma-ri-po-sa", "silabas_colores": ["#E53935", "#1E88E5", "#43A047", "#FB8C00"]}, {"palabra": "bi-ci-cle-ta", "silabas_colores": ["#E53935", "#1E88E5", "#43A047", "#FB8C00"]}, {"palabra": "es-cue-la", "silabas_colores": ["#E53935", "#1E88E5", "#43A047"]}, {"palabra": "ca-ba-llo", "silabas_colores": ["#E53935", "#1E88E5", "#43A047"]}, {"palabra": "gui-ta-rra", "silabas_colores": ["#E53935", "#1E88E5", "#43A047"]}]}$ej$::jsonb, TRUE, TRUE, 'MULTI_silabas_cromaticas_N1', $ej$silabas_con_color$ej$, $ej$Cada sílaba tiene un color diferente. Lee la palabra siguiendo los colores.$ej$, ARRAY['mixto']::TEXT[]
FROM intervention.learning_paths lp WHERE lp.target_subtype = 'MIXED'
ON CONFLICT (exercise_code) WHERE exercise_code IS NOT NULL
DO UPDATE SET content=EXCLUDED.content, title=EXCLUDED.title, has_tts=EXCLUDED.has_tts,
    has_stt=EXCLUDED.has_stt, skill_target=EXCLUDED.skill_target, difficulty=EXCLUDED.difficulty;

INSERT INTO intervention.exercises
    (learning_path_id, title, exercise_type, difficulty, content, has_tts, has_stt, exercise_code, skill_target, objective, source_tags)
SELECT lp.id, $ej$Lee mientras escuchas$ej$, 'MULTIMODAL', 1, $ej${"exercise_id": "MULTI_lectura_auditiva_N1", "tipo": "multimodal", "subtipo": "lectura_audio_simultanea", "perfil_objetivo": ["mixto", "fonologico"], "nivel": 1, "grados": ["1", "2", "3"], "titulo": "Lee mientras escuchas", "instruccion": "Escucha y lee al mismo tiempo. El texto se ilumina conforme avanza el audio.", "modalidad": "tts_karaoke", "usa_tts": true, "usa_stt": true, "nota": "Efecto karaoke: cada palabra se resalta en amarillo conforme el TTS la lee.", "texto": "El río baja de la montaña. Cruza el campo y llega al pueblo. Los niños juegan en su orilla en verano.", "velocidad_tts": "lenta"}$ej$::jsonb, TRUE, TRUE, 'MULTI_lectura_auditiva_N1', $ej$lectura_audio_simultanea$ej$, $ej$Escucha y lee al mismo tiempo. El texto se ilumina conforme avanza el audio.$ej$, ARRAY['mixto']::TEXT[]
FROM intervention.learning_paths lp WHERE lp.target_subtype = 'MIXED'
ON CONFLICT (exercise_code) WHERE exercise_code IS NOT NULL
DO UPDATE SET content=EXCLUDED.content, title=EXCLUDED.title, has_tts=EXCLUDED.has_tts,
    has_stt=EXCLUDED.has_stt, skill_target=EXCLUDED.skill_target, difficulty=EXCLUDED.difficulty;

INSERT INTO intervention.exercises
    (learning_path_id, title, exercise_type, difficulty, content, has_tts, has_stt, exercise_code, skill_target, objective, source_tags)
SELECT lp.id, $ej$Lee mientras escuchas (refuerzo)$ej$, 'MULTIMODAL', 1, $ej${"exercise_id": "MULTI_lectura_auditiva_N1_refuerzo", "tipo": "multimodal", "subtipo": "lectura_audio_simultanea", "perfil_objetivo": ["mixto", "fonologico"], "nivel": 1, "grados": ["1", "2"], "titulo": "Lee mientras escuchas (refuerzo)", "instruccion": "El sistema lee cada frase muy despacio. Síguelas con el dedo.", "modalidad": "tts_karaoke", "usa_tts": true, "usa_stt": false, "texto": "La vaca come pasto verde. El toro descansa bajo el árbol. El granjero los cuida todos los días.", "velocidad_tts": "muy_lenta"}$ej$::jsonb, TRUE, FALSE, 'MULTI_lectura_auditiva_N1_refuerzo', $ej$lectura_audio_simultanea$ej$, $ej$El sistema lee cada frase muy despacio. Síguelas con el dedo.$ej$, ARRAY['mixto']::TEXT[]
FROM intervention.learning_paths lp WHERE lp.target_subtype = 'MIXED'
ON CONFLICT (exercise_code) WHERE exercise_code IS NOT NULL
DO UPDATE SET content=EXCLUDED.content, title=EXCLUDED.title, has_tts=EXCLUDED.has_tts,
    has_stt=EXCLUDED.has_stt, skill_target=EXCLUDED.skill_target, difficulty=EXCLUDED.difficulty;

INSERT INTO intervention.exercises
    (learning_path_id, title, exercise_type, difficulty, content, has_tts, has_stt, exercise_code, skill_target, objective, source_tags)
SELECT lp.id, $ej$Lee y responde$ej$, 'COMPRENSION', 1, $ej${"exercise_id": "COMP_textos_cortos_N1", "tipo": "comprension", "subtipo": "comprension_lectora", "perfil_objetivo": ["mixto"], "nivel": 1, "grados": ["2", "3", "4"], "titulo": "Lee y responde", "instruccion": "Lee el texto y luego toca la respuesta correcta.", "modalidad": "tactil_tts", "usa_tts": true, "usa_stt": false, "referencia_banco": "comprension_lectora_CogniFit", "nivel_banco": 1}$ej$::jsonb, TRUE, FALSE, 'COMP_textos_cortos_N1', $ej$comprension_lectora$ej$, $ej$Lee el texto y luego toca la respuesta correcta.$ej$, ARRAY['mixto']::TEXT[]
FROM intervention.learning_paths lp WHERE lp.target_subtype = 'MIXED'
ON CONFLICT (exercise_code) WHERE exercise_code IS NOT NULL
DO UPDATE SET content=EXCLUDED.content, title=EXCLUDED.title, has_tts=EXCLUDED.has_tts,
    has_stt=EXCLUDED.has_stt, skill_target=EXCLUDED.skill_target, difficulty=EXCLUDED.difficulty;

