# Contexto_chat 1.pdf - extracción visual

El PDF no contiene capa de texto seleccionable. Se renderizaron sus 10 páginas y se recuperó el contenido por revisión visual.

## Página 1

Documento de contexto del proyecto CogniFit Escolar para un nuevo chat. Propósito: reunir lo investigado, documentos generados y estado del trabajo sobre PLN/ML y tests de dislexia.

Datos del proyecto: estudiante Rodrigo Emilio Campuzano Culebro, matrícula 233283, grupo 9-D, Universidad Politécnica de Chiapas, Ingeniería en Software. Compañeros recurrentes: Carlos Daniel Solís Aguilar y Alicia Montserrat Valenti Ruiz.

Proyecto: CogniFit Escolar. Plataforma móvil para detección temprana de riesgo de dislexia en primaria en México, 1o a 5o grado, 6 a 10 años, con foco en estados de alta marginación como Chiapas. Problema: se cita 7% de población con dislexia en México y falta de diagnóstico oportuno. Aclaración: no emite diagnóstico clínico; detecta indicadores tempranos y orienta al docente para derivación.

Stack: Flutter/Dart con Clean Architecture, MVVM y Riverpod; go_router; Dio con JWT; FLAG_SECURE, flutter_secure_storage y EncryptedSharedPreferences.

## Página 2

Stack adicional: TTS/STT para dictado y retroalimentación; FastAPI en backend con arquitectura SOA y Docker; JWT + Argon2; PostgreSQL con JSONB para vectores ML y Redis para caché; spaCy es_core_news_md + python-Levenshtein + metaphone para PLN; scikit-learn Random Forest/SVM para ML; ReportLab para reportes; Firebase FCM con remote wipe.

Microservicios: Auth Service, User & Groups Service, Test Service, Diagnosis Service, Recommendation Service, Exercise Service, Tracking & Alerts Service y Report Service.

## Página 3

Tests gratuitos/descargables referenciados: PRODISLEX 1er, 2o y 3er ciclo; PRODISLEX digital; TEDE manual completo UMCE; TEDE servidor mexicano; TEDE protocolo editable; PROLEXIA PDF COP.

Tests comerciales/metodológicos: PROLEC-3 para procesos lectores, palabras, pseudopalabras y comprensión; DST-J para screening 6-11 años y denominación rápida; LEE para lectura/escritura, fluidez, comprensión y errores.

## Página 4

Batería diagnóstica de CogniFit: 9 módulos. Flujo de activación: docente completa PRODISLEX; score mayor o igual a 50 activa batería completa; score menor a 50 activa screening rápido con módulos 2, 4 y 8.

Módulos visibles:

- 1. Cuestionario docente, PRODISLEX, 2-3 min: score 0-100 y risk_flags.
- 2. Conciencia fonológica, PROLEXIA/DST-J, 4-5 min: sonido inicial/final, sílabas, rimas, supresión.
- 3. Letras y sílabas, TEDE Parte 1 ítems 1-40, 3-4 min: confusiones b/d/p/q, omisiones en trabadas.
- 4. Palabras reales, PROLEC-3/TEDE, 3-4 min: precisión, velocidad, autocorrecciones.
- 5. Pseudopalabras, PROLEC-3/TEDE Parte 2, 3-4 min: principal discriminador fonológico vs visual, 25% del score.
- 6. Dictado inteligente, TEDE/LEE, 4-5 min: texto producido vs esperado y errores PLN.
- 7. Copia controlada, TALE/LEE, 2-3 min: copia vs dictado para diferenciar error fonológico/visual.

## Página 5

Módulos restantes:

- 8. Denominación rápida, DST-J/PROLEXIA, 2-3 min: tiempo total y automatización lectora.
- 9. Comprensión lectora, PROLEC-3/DST-J, 4-5 min: diferencia entre leer sin comprender y no leer bien.

Códigos PLN:

- OMI: omisión, ejemplo perro -> pero, perfil fonológico.
- SUS: sustitución, ejemplo dado -> bado, perfil visual o fonológico.
- INV: inversión, ejemplo plato -> palto, perfil fonológico/mixto.
- ROT: rotación visual, b/d o p/q, perfil visual/superficial.
- LEX: lexicalización, pseudopalabra convertida en palabra real cercana, perfil visual/compensación.
- SEG: segmentación, conmigo -> con migo, perfil fonológico.
- UNI: unión, la casa -> lacasa, perfil fonológico.
- FON: error fonológico, guitarra -> gitarra, perfil fonológico.
- ADD: adición, cocina -> cocicina, perfil mixto.
- LEN: lentitud, correcto pero tardado, fluidez/automatización.
- COM: comprensión, respuesta literal incorrecta, comprensión.
- ACC: acento, rápido -> rapido, ortográfico no diagnóstico. No suma al score de dislexia.

## Página 6

Stack del Diagnosis Service: spaCy para tokenización/lematización; python-Levenshtein para editops delete/insert/replace; metaphone para similitud fonética en español; TfidfVectorizer para vectorizar patrones de error; RandomForest/SVM con predict_proba; pandas + scipy.stats para series temporales y estancamiento; FastAPI + Pydantic para API REST; joblib para serialización; PostgreSQL JSONB para feature vectors y breakdowns; Redis para caché.

Vector de características declarado como 28 dimensiones:

- 0-9: OMI_rate, SUS_rate, INV_rate, ROT_rate, LEX_rate, SEG_rate, UNI_rate, FON_rate, ADD_rate, LEN_rate.
- 10-12: accuracy, error_rate, pseudo_vs_word_gap.
- 13-14: pseudo_error_rate, word_error_rate.
- 15-17: avg_time_norm, std_time_norm, slow_response_rate.
- 18-19: avg_phonetic_sim, avg_ngram_overlap.
- 20-21: rot_sus_ratio, lex_flag.
- 22-23: seg_uni_rate, inv_omi_ratio.
- 26-27: grade_norm, teacher_score_norm.

Nota: en la página no aparecen explícitamente las posiciones 24-25.

## Página 7

Feature más importante: pseudo_vs_word_gap = pseudo_error_rate - word_error_rate.

Interpretación:

- Alto, mayor a 0.20: dislexia fonológica, falla mucho más en pseudopalabras que en palabras reales.
- Bajo, menor a 0.10, con muchos ROT/LEX: dislexia visual/superficial.
- Ambos altos: dislexia mixta.

Salida del clasificador JSON: subtype, severity, risk_probability, risk_level, main_error_codes, feature_vector.

Perfiles y rutas:

- Fonológico: falla pseudopalabras mucho más que palabras reales, muchos OMI/INV. Ruta: CF_silabas_N1 -> CF_fonema_inicial_N1 -> PS_cv_N1 -> DIC_palabras_simples_N1.
- Visual/superficial: muchos ROT b/d/p/q y LEX frecuente. Ruta: VIS_discriminacion_bd_N1 -> VIS_memoria_palabras_N1 -> DEN_rapid_letras_N1.
- Mixto: falla en todo, combina FON y ROT. Ruta: MULTI_silabas_cromaticas_N1 -> MULTI_lectura_auditiva_N1 -> CF_silabas_N1 -> PS_cv_N1.
- Fluidez: pocos errores pero muy lento. Ruta: DEN_rapid_colores_N1 -> LEC_repetida_N1 -> LEC_temporizador_N1.
- Comprensión: lee palabras bien, falla comprensión. Ruta: COMP_textos_cortos_N1 -> apoyo_auditivo -> vocabulario_N1.

## Página 8

Recalibración automática:

- Sube nivel si accuracy > 90% en las últimas 3 sesiones del nivel actual.
- Alerta de estancamiento si no mejora en 5 sesiones consecutivas.
- Regresión: pendiente positiva en curva de error baja nivel y activa TTS de apoyo.

Métricas mínimas para producción:

- F1-macro subtipo >= 0.80.
- F1-macro severidad >= 0.75.
- Balanced accuracy >= 0.75.
- Sensibilidad en alto riesgo >= 0.85.
- Muestras por clase >= 50.

Dataset sintético: como no se pueden usar datos reales de menores en MVP, se propone inyectar ruido disléxico sobre vocabulario frecuente de primaria mexicana. Funciones: inject_omission, inject_rotation, inject_inversion, inject_lexicalization. Cada muestra se etiqueta con perfil y severidad, versionada con pandas y trazabilidad.

## Página 9

Esquema PostgreSQL relevante:

- diagnosis_ml_sessions: id, student_id, session_date, session_number, grade, accuracy, error_rate, avg_response_ms, feature_vector JSONB, error_breakdown JSONB, subtype, severity, risk_probability, risk_level, model_version, exercise_route JSONB, exercise_level.
- tracking.alerts: id, student_id, alert_type, message, suggested_action, urgency, is_read, teacher_id.

Documentos generados en la conversación:

- CogniFit_Bateria_Diagnostica_Unificada.docx: Word profesional con 9 módulos, tablas de errores, escala de riesgo, perfiles y rutas.
- CogniFit_PLN_ML_Diseño_Implementacion.md: documento técnico con código Python completo, preprocesamiento, detección de errores, feature engineering, clasificador ML, motor de recomendación, seguimiento con series temporales, dataset sintético, API FastAPI, esquema BD y validación.

## Página 10

Pendientes / próximos pasos:

- Implementar widget Flutter del módulo de pseudopalabras con UI y STT.
- Codificar generador de dataset sintético completo en Python.
- Implementar Diagnosis Service como microservicio FastAPI real.
- Conectar Test Service en Flutter con Diagnosis Service.
- Diseñar dashboard docente con curva de aprendizaje y alertas.
- Implementar Report Service con ReportLab para PDF de padres/especialistas.

Frases clave:

- CogniFit Escolar implementa una batería digital de detección temprana de riesgo de dislexia basada en conciencia fonológica, lectura de palabras, pseudopalabras, dictado inteligente, copia controlada, denominación rápida y comprensión lectora. Cada actividad registra precisión, tiempo de respuesta y tipo de error para alimentar un modelo PLN/ML que estima riesgo, perfil y ruta adaptativa. El sistema no reemplaza al especialista.
- El sistema utiliza los mismos constructos evaluados por TEDE, PROLEC-3, PROLEXIA y DST-J, automatizando mediante PLN la corrección que antes hacía un especialista a mano.
