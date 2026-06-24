# CogniFit Escolar - análisis DB + integración completa

## Diagnóstico del schema actual

La base ya tiene una arquitectura sana: schemas por dominio (`auth`, `academic`, `assessment`, `diagnosis`, `intervention`, `tracking`, `reporting`, `audit`), JWT/Argon2, consentimiento, cifrado PII, RLS inicial, microservicios implícitos y tablas para tests, respuestas, diagnósticos, rutas, ejercicios, tracking, reportes y auditoría.

Los huecos principales para integrar el flujo completo son:

- `assessment.test_type` solo cubría léxico-visual, pseudopalabras y dictado; faltaban PRODISLEX docente, conciencia fonológica, letras/sílabas, palabras reales, copia, RAN y comprensión.
- No existía catálogo de módulos de batería; la app Flutter necesita saber qué módulos activar en modo rápido o completo.
- PRODISLEX estaba reducido a una idea, sin preguntas compactas ni banco completo por ciclo.
- TEDE no estaba modelado como banco de ítems queryable.
- `student_responses` guardaba texto bruto, pero no STT, normalización, distancia de edición, Metaphone, n-gramas, lexicalización ni breakdown por error.
- `diagnosis.diagnoses` no guardaba el vector de 28 dimensiones ni los códigos dominantes de error.
- No había tabla de eventos de error por respuesta, necesaria para auditar OMI/SUS/INV/ROT/FON/etc.
- `ml_model_versions` no impedía promover modelos sin métricas mínimas.
- `learning_paths` dependía solo del enum clínico y no cubría perfiles operativos como fluidez/comprensión.
- `tracking` seguía ejercicios, pero no sesiones diagnósticas acumuladas como serie temporal.

## Qué agrega la migración

- 9 módulos de batería: cuestionario docente, conciencia fonológica, letras/sílabas, palabras reales, pseudopalabras, dictado, copia, denominación rápida y comprensión.
- Reglas de activación: score PRODISLEX < 50 activa módulos 2, 4 y 8; score >= 50 activa batería completa.
- 8 preguntas docentes ponderadas 0-100 con escala `Nunca/A veces/Frecuente`.
- Banco completo PRODISLEX por ciclo, normalizado desde los PDFs.
- Banco TEDE con letras, sílabas, pseudopalabras, inversiones y errores específicos.
- Catálogo de instrumentos fuente y notas de licencia/uso.
- Códigos PLN: OMI, SUS, INV, ROT, LEX, SEG, UNI, FON, ADD, LEN, COM, ACC.
- Feature vector de 28 dimensiones, incluyendo los dos huecos propuestos para completar posiciones 24-25.
- Eventos de error por respuesta para trazabilidad y debugging del pipeline.
- Pipeline runs para guardar salida de cada ejecución PLN/ML.
- Rutas de intervención adaptativa y ejercicios semilla.
- Tracking longitudinal de sesiones diagnósticas y alertas con urgencia/acción sugerida.
- Vistas `assessment.v_battery_catalog` y `diagnosis.v_latest_student_risk`.

## Archivos generados

- `cognifit_integration_migration.sql`: migración incremental sobre tu DB actual.
- `cognifit_schema_v2_full.sql`: schema v1 original + migración v2 en un solo archivo.
- `cognifit_db_table_mapping.json`: mapa app/servicio/tabla para integrar Flutter, FastAPI y ML.

## Orden recomendado de implementación

1. Ejecutar `cognifit_schema.sql` original si la DB está vacía.
2. Ejecutar `cognifit_integration_migration.sql` en autocommit.
3. En Flutter, leer `assessment.v_battery_catalog` para construir la batería.
4. En Test Service, crear `test_assignments` y `test_sessions` por módulo activo.
5. Guardar respuestas en `assessment.student_responses`.
6. Diagnosis Service procesa respuestas, llena `diagnosis.response_error_events`, `diagnosis.pipeline_runs` y `diagnosis.diagnoses`.
7. Recommendation Service usa `intervention.route_templates` para asignar `student_paths`.
8. Tracking & Alerts Service escribe `tracking.diagnosis_ml_sessions`, snapshots y alertas.

## Nota legal/metodológica

El schema queda listo para implementación académica/MVP. PROLEXIA, PROLEC-3, DST-J, LEE y TALE deben tratarse como referencia metodológica salvo licencia explícita. La app debe comunicar “riesgo/probabilidad y ruta educativa”, no diagnóstico clínico definitivo.
