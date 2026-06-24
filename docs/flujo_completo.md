# CogniFit Escolar - extracción ordenada por flujo completo

> Uso recomendado: sembrar contenido en backend/Flutter, generar módulos, definir feature vectors y reportes. No presenta diagnóstico clínico; entrega estimación de riesgo y ruta educativa adaptativa.

## Fase 1 - Docente: PRODISLEX digitalizado

Fuente: `Protocolo-Dislexia-Primaria-1ciclo.pdf`, `2ciclo`, `3ciclo`.

Escala MVP: `Nunca=0`, `A veces=0.5`, `Frecuente=1`. Score final: suma ponderada 0-100.

| ID | Pregunta docente | Peso | Tags PLN |
| --- | --- | ---: | --- |
| `q01_confunde_letras_espejo` | Confunde letras simétricas o en espejo, como b/d, p/q, u/n o m/w. | 14 | ROT, visual_superficial |
| `q02_invierte_orden` | Cambia el orden de letras o sílabas dentro de las palabras. | 13 | INV, fonologico_mixto |
| `q03_omite_agrega` | Omite o añade letras, sílabas o palabras al leer o escribir. | 13 | OMI, ADD, fonologico |
| `q04_sustituye_letras` | Cambia unas letras por otras al leer o escribir. | 12 | SUS, ROT, FON |
| `q05_lectura_lenta` | Lee con lentitud o con baja precisión para su grado escolar. | 12 | LEN, fluidez |
| `q06_evitar_leer_voz_alta` | Evita leer en voz alta o muestra malestar ante la lectura. | 10 | avoidance, risk_flag |
| `q07_dictado_copiado` | Presenta dificultades en dictados, copiados o al tomar apuntes. | 13 | FON, VIS, writing |
| `q08_comprension` | Tiene baja comprensión lectora o se inventa palabras al leer. | 13 | COM, LEX |

Regla de activación: score menor a 50 activa screening rápido con módulos 2, 4 y 8; score mayor o igual a 50 activa batería completa.

Contenido PRODISLEX completo: el JSON normalizado conserva todos los ítems por ciclo con áreas: historia clínica, discrepancias, comprensión/expresión oral, lectura/escritura, matemáticas/tiempo, cognición/atención, salud, personalidad/organización y coordinación psicomotriz.

## Fase 2 - Alumno: batería Flutter de 9 módulos

| # | Módulo | Fuente | Duración | Captura principal |
| ---: | --- | --- | --- | --- |
| 1 | Cuestionario docente PRODISLEX digitalizado | Protocolo-Dislexia-Primaria-1ciclo.pdf, Protocolo-Dislexia-Primaria-2ciclo.pdf, Protocolo-Dislexia-Primaria-3ciclo.pdf | 2-3 min | teacher_score_0_100, risk_flags, grade, cycle |
| 2 | Conciencia fonológica | PROLEXIA_evaluacion_COP.pdf, referencia DST-J del contexto | 4-5 min | accuracy, error_code, response_time_ms, audio_uri |
| 3 | Letras y sílabas | TEDE Parte 1, edtv_6.pdf fichas | 3-4 min | expected, produced, accuracy, response_time_ms, OMI/SUS/INV/ROT |
| 4 | Palabras reales | TEDE, PROLEC-3 como referencia metodológica | 3-4 min | precision, words_per_minute, autocorrections, word_error_rate |
| 5 | Pseudopalabras | TEDE Parte 2, PROLEXIA lectura/deletreo/dictado de pseudopalabras, PROLEC-3 como referencia metodológica | 3-4 min | pseudo_error_rate, lexicalization_flag, phonetic_similarity, ngram_overlap |
| 6 | Dictado inteligente | TEDE, LEE como referencia metodológica | 4-5 min | expected_text, produced_text, edit_distance, metaphone_similarity, phonological_vs_orthographic_error |
| 7 | Copia controlada | TALE/LEE como referencia metodológica, PRODISLEX copiados | 2-3 min | copy_error_rate, dictation_copy_gap, visual_error_flags, graphomotor_notes |
| 8 | Denominación rápida | PROLEXIA RAN colores/objetos, DST-J | 2-3 min | total_time_sec, ran_errors, LEN_rate, automation_score |
| 9 | Comprensión lectora | PROLEC-3/DST-J como referencia metodológica, PRODISLEX comprensión lectora | 4-5 min | literal_accuracy, inferential_accuracy, COM_errors, read_time_ms |

Detalle implementable por módulo:

### Módulo 2 - Conciencia fonológica

Implementar tareas tipo PROLEXIA: señalar palabra diferente por sonido final, contar sílabas, repetir pseudopalabras, omitir sílaba, sustituir fonema e invertir sílaba. Capturar acierto, tiempo, respuesta oral y error.

### Módulo 3 - Letras y sílabas TEDE

Usar el banco `tede_item_bank.nivel_lector`: nombre de letra, sonido de letra, sílabas directas, sílabas con u muda, indirectas, complejas, diptongos y fonogramas.

### Módulo 4 - Palabras reales

Usar palabras reales de TEDE: `la`, `sol`, `se`, `las`, `nos`, `los`, `al`, `es`, `son`, `le`, `sal`, y listas de inversión dentro de palabra/sílaba (`palta`, `sobra`, `trota`, `plumón`, `loma`, `saco`, etc.). Capturar precisión, autocorrecciones y palabras por minuto.

### Módulo 5 - Pseudopalabras

Módulo crítico: usar pseudopalabras TEDE (`nomino`, `ohnado`, `deste`, `alledo`, `rechido`, `chaquillo`, `laqueta`, `sagueso`, `quiguifi`, `ifjuti`, `voyate`, `quellimi`, `bado`, `dipo`, etc.) y generar variantes propias graduadas. Peso recomendado en riesgo: 25%.

### Módulos 6 y 7 - Dictado inteligente y copia controlada

Dictado: reproducir palabra/frase con TTS, alumno escribe, pipeline compara esperado vs producido. Copia: mostrar estímulo y comparar si el error aparece con apoyo visual. La diferencia dictado-copia ayuda a separar error fonológico vs visual/ortográfico.

### Módulo 8 - Denominación rápida

Inspirado en RAN colores/objetos de PROLEXIA: grilla de 36 estímulos, tiempo total, errores, autocorrecciones y fluidez.

### Módulo 9 - Comprensión lectora

Textos propios por grado, preguntas literales e inferenciales. Captura `COM_errors`, tiempo de lectura y precisión. Este es el noveno módulo que complementa el diagrama donde solo se veían 8 cajas principales.

## Fase 3 - Pipeline PLN/ML

Stack: spaCy `es_core_news_md`, python-Levenshtein, Metaphone/Soundex español, n-gramas de caracteres, TF-IDF, Random Forest/SVM, FastAPI/Pydantic, joblib, PostgreSQL JSONB y Redis.

| Código | Tipo | Ejemplo | Perfil indicado |
| --- | --- | --- | --- |
| `OMI` | Omisión | perro -> pero | fonológico |
| `SUS` | Sustitución | dado -> bado | visual o fonológico |
| `INV` | Inversión | plato -> palto | fonológico/mixto |
| `ROT` | Rotación visual | b<->d, p<->q | visual/superficial |
| `LEX` | Lexicalización | pseudopalabra leída como palabra real cercana | visual/compensación |
| `SEG` | Segmentación | conmigo -> con migo | fonológico |
| `UNI` | Unión | la casa -> lacasa | fonológico |
| `FON` | Error fonológico | guitarra -> gitarra | fonológico |
| `ADD` | Adición | cocina -> cocicina | mixto |
| `LEN` | Lentitud | respuesta correcta pero tardía | fluidez/automatización |
| `COM` | Comprensión | respuesta literal/inferencial incorrecta | comprensión |
| `ACC` | Acento | rápido -> rapido | ortográfico informativo; no suma al score |

`ACC` no suma al score de riesgo; es informativo/ortográfico.

Vector de 28 dimensiones:

```json
[
  "OMI_rate",
  "SUS_rate",
  "INV_rate",
  "ROT_rate",
  "LEX_rate",
  "SEG_rate",
  "UNI_rate",
  "FON_rate",
  "ADD_rate",
  "LEN_rate",
  "accuracy",
  "error_rate",
  "pseudo_vs_word_gap",
  "pseudo_error_rate",
  "word_error_rate",
  "avg_time_norm",
  "std_time_norm",
  "slow_response_rate",
  "avg_phonetic_sim",
  "avg_ngram_overlap",
  "rot_sus_ratio",
  "lex_flag",
  "seg_uni_rate",
  "inv_omi_ratio",
  "module_completion_rate_suggested",
  "dominant_error_concentration_suggested",
  "grade_norm",
  "teacher_score_norm"
]
```

Nota: el PDF de contexto declara 28 dimensiones pero omite las posiciones 24-25; aquí se proponen `module_completion_rate_suggested` y `dominant_error_concentration_suggested` para mantener el vector estable.

## Fases 4 y 5 - Perfil y ruta adaptativa

| Perfil | Patrón | Ruta inicial |
| --- | --- | --- |
| fonologico | falla pseudopalabras mucho más que palabras reales; muchos OMI/INV/FON | CF_silabas_N1 -> CF_fonema_inicial_N1 -> PS_cv_N1 -> DIC_palabras_simples_N1 |
| visual_superficial | muchos ROT b/d/p/q y LEX frecuente | VIS_discriminacion_bd_N1 -> VIS_memoria_palabras_N1 -> DEN_rapid_letras_N1 |
| mixto | falla generalizada; combina FON y ROT | MULTI_silabas_cromaticas_N1 -> MULTI_lectura_auditiva_N1 -> CF_silabas_N1 -> PS_cv_N1 |
| fluidez | pocos errores pero respuesta lenta | DEN_rapid_colores_N1 -> LEC_repetida_N1 -> LEC_temporizador_N1 |
| comprension | lee palabras bien pero falla comprensión | COMP_textos_cortos_N1 -> apoyo_auditivo -> vocabulario_N1 |

Reglas base: `pseudo_vs_word_gap > 0.20` sugiere fonológico; gap bajo con ROT/LEX alto sugiere visual/superficial; ambos altos sugieren mixto.

## Fase 6 - Seguimiento y recalibración

- Sube nivel: accuracy > 90% en las últimas 3 sesiones del nivel actual.
- Estancamiento: sin mejora en 5 sesiones consecutivas genera alerta docente.
- Regresión: pendiente positiva en curva de error baja nivel y activa TTS de apoyo.
- PostgreSQL guarda series temporales por sesión, feature vector JSONB, breakdown de errores y versión del modelo.

SQL base:

```sql
CREATE TABLE diagnosis_ml_sessions (
  id UUID PRIMARY KEY,
  student_id INT NOT NULL,
  session_date TIMESTAMPTZ NOT NULL,
  session_number INT NOT NULL,
  grade SMALLINT NOT NULL,
  accuracy NUMERIC(5,4),
  error_rate NUMERIC(5,4),
  avg_response_ms INT,
  feature_vector JSONB,
  error_breakdown JSONB,
  subtype VARCHAR(20),
  severity VARCHAR(10),
  risk_probability NUMERIC(5,4),
  risk_level VARCHAR(10),
  model_version VARCHAR(30),
  exercise_route JSONB,
  exercise_level INT
);

CREATE TABLE tracking_alerts (
  id UUID PRIMARY KEY,
  student_id INT NOT NULL,
  alert_type VARCHAR(30),
  message TEXT,
  suggested_action TEXT,
  urgency VARCHAR(10),
  is_read BOOLEAN DEFAULT FALSE,
  teacher_id INT
);
```

## Separación por PDF

### 1. Contexto_chat 1.pdf

Documento de contexto del proyecto. No tiene capa de texto, así que se recuperó por revisión visual de páginas renderizadas. Aporta: propósito académico, stack completo, microservicios, referencias de tests, batería de 9 módulos, códigos PLN, vector de características, rutas, seguimiento, dataset sintético y esquema PostgreSQL.

### 2. MVP — CogniFit Escolar.pdf

Define el MVP: roles Docente/Alumno/Admin, Flutter con Riverpod/go_router/Dio/FLAG_SECURE/TTS-STT, backend SOA con FastAPI/microservicios, seguridad OWASP MASVS, OCTAVE ALLEGRO, reportes PDF y modelo de monetización.

### 3. PROLEXIA_evaluacion_COP.pdf

Usar como soporte metodológico para conciencia fonológica, pseudopalabras, RAN y puntuación de riesgo. Contiene dos baterías: detección temprana 4-6 años con 6 tareas/112 ítems y diagnóstica 7-70 años con 12 tareas/196 ítems. Riesgo PR: muy bajo 0-35, bajo 36-57, moderado 58-72, alto 73-110, muy alto >=111.

### 4. Test Exploratorio de Dislexia Específica TEDE editable

Base directa para letras/sílabas, pseudopalabras e inversiones. Administración individual, respuesta oral, margen máximo de 5 segundos. Nivel lector: aciertos hasta 100; errores específicos: 71 menos errores.

### 5. edtv_6.pdf

Manual TEDE completo con normas, ejemplos, fichas y taxonomía: confusiones visuales, auditivas, inversiones, agregados, omisiones, contaminaciones, disociaciones y distorsiones. Útil para mapear a OMI/SUS/INV/ROT/ADD/SEG/UNI/FON.

### 6. Protocolo-Dislexia-Primaria-3ciclo.pdf

PRODISLEX para tercer ciclo. Enfatiza velocidad/precisión lectora, lectura pública, dictado/copiado, apuntes, lenguas extranjeras, comprensión, técnicas de estudio, apoyos visuales/auditivos y herramientas compensatorias.

### 7. Protocolo-Dislexia-Primaria-2ciclo.pdf

PRODISLEX para segundo ciclo. Enfatiza lectura/escritura, segmentación/unión de sonidos, puntuación, morfosintaxis, baja comprensión, dictado, copiado, organización y apoyo con lectura silábica, colores, rimas, trabalenguas y audio.

### 8. Protocolo-Dislexia-Primaria-1ciclo.pdf

PRODISLEX para primer ciclo. Enfatiza adquisición inicial de lectura/escritura, multisílabas, aversión, inversión, omisión/adición, rotación, sustitución, segmentación/unión de sonidos, abecedario, grafismo y actividades multisensoriales.

### 9. pdf-test-tede_compress.pdf

Resumen tipo presentación de TEDE: ficha técnica, objetivos, subtests, materiales, instrucciones al examinador y reglas de evaluación. Sirve como versión compacta para pantallas internas de administración.

## Restricción importante

PROLEXIA/PROLEC/DST-J/LEE/TALE pueden requerir licencia profesional. Para un MVP académico, implementa constructos, tipos de tarea y bancos propios o autorizados; evita presentar el sistema como diagnóstico clínico.
