# Expo "Modelos en producción" — Diseño

**Fecha:** 2026-07-27
**Estado:** aprobado, pendiente de plan de implementación
**Revisión:** reemplaza la versión anterior, que incluía implementar un asistente RAG.

## 1. Objetivo

Preparar una exposición de 15–20 minutos sobre modelos en producción —inferencia,
despliegue, RAG e integración con backend y frontend— usando CogniFit como caso
real.

**Regla que gobierna todo el material: la exposición solo afirma lo que el
proyecto ya tiene.** Todo lo que no está construido se presenta explícitamente
como idea futura, marcado como tal en la diapositiva. El RAG entra en esa
categoría: se explica el problema que resolvería y cómo se construiría, sin
presentarlo como algo que exista.

## 2. Alcance

### Dentro

- `docs/expo_modelos_produccion/index.html` — slides autocontenidas y publicables.
- `docs/expo_modelos_produccion/guion.md` — guion por diapositiva con tiempos y
  respuestas preparadas para el jurado.

### Fuera

**No se escribe código de aplicación.** En particular quedan fuera, y pasan a ser
material de la diapositiva de trabajo futuro:

- El microservicio `rag_service`.
- La migración pgvector y el cambio de imagen de PostgreSQL.
- La ruta `/asistente/consultar` en el API gateway.
- La pantalla Flutter del asistente.
- Cualquier cambio a los servicios, modelos o flujos existentes.

## 3. Lo que el proyecto sí tiene (base factual de la expo)

Todo lo afirmado en las diapositivas debe poder señalarse en un archivo del
repositorio. Inventario verificado:

| Pieza | Dónde | Puerto |
|---|---|---|
| Gateway FastAPI, arquitectura limpia, 13 routers | `api/` | 8000 |
| Pipeline PLN: preprocesado, detección de errores, fonética, vector 28D | `Pln/diagnosis_service/app/pln/` | 8001 |
| Dos clasificadores sklearn entrenados (`subtype`, `severity`), versión `20260618_0309` | `Pln/diagnosis_service/app/models/*.pkl` | 8001 |
| Motor de ruta adaptativa desde bancos JSON | `Pln/recommendation_service/` | 8002 |
| PostgreSQL 16 con schemas por dominio + Redis 7 | `docker-compose.yml`, `database/` | 5432 / 6379 |
| App Flutter, arquitectura limpia por feature, TTS/STT, cola offline | `app/cognifit_mobile/` | — |
| Versionado de modelos con umbrales en BD | `diagnosis.ml_model_versions`, `ck_model_production_thresholds` | — |
| Degradación elegante: `PLN_FALLBACK_ENABLED`, trazada como `pln_source` | `api/.env.docker`, `docs/DESPLIEGUE_RAILWAY.md` | — |
| Incidente de despliegue documentado con causa raíz | `docs/DESPLIEGUE_RAILWAY.md` | — |

### Lo que el proyecto no tiene (se dice en voz alta)

Sin CI/CD · sin observabilidad (ni Prometheus, ni Grafana, ni OpenTelemetry, ni
Sentry) · rate limiting en memoria que se pierde al reiniciar · sin reentrenamiento
en runtime ni endpoint `/model/reload` · sin detección de deriva · caché semántico
escrito pero no conectado a ningún router · 6º grado con 0 ejercicios en el banco ·
sin RAG.

## 4. Estructura de la exposición

15 diapositivas, más 3 de respaldo para preguntas.

| # | Diapositiva | Contenido | Min |
|---|---|---|---|
| 1 | Portada | Tesis: entrenar el modelo fue la parte fácil | 0:30 |
| 2 | CogniFit | Qué detecta, para quién, las seis fases | 1:00 |
| 3 | Arquitectura | Los cinco servicios que existen hoy, un diagrama | 1:30 |
| 4 | **Inferencia I** | Del audio del alumno al vector de 28 dimensiones: Levenshtein, Metaphone, n-gramas | 1:30 |
| 5 | **Inferencia II** | Dos clasificadores sklearn: subtipo y severidad. Por qué `.pkl` y no una red neuronal | 1:30 |
| 6 | **Inferencia III** | El contrato: `/diagnose`, `/model/info`, y por qué la BD bloquea promover un modelo sin métricas | 1:30 |
| 7 | **Despliegue I** | Docker multiservicio, healthchecks, `depends_on: service_healthy` | 1:30 |
| 8 | **Despliegue II** | El incidente de Railway: el comando de inicio personalizado, el diagnóstico equivocado de IPv6, y la lección de leer los logs antes de teorizar | 2:00 |
| 9 | **Despliegue III** | Degradación elegante: `PLN_FALLBACK_ENABLED`, el pipeline local que siempre responde, y `pln_source='local_fallback'` como rastro auditable | 1:30 |
| 10 | **Integración I** | El gateway como única puerta: JWT, RBAC, y por qué los puertos 8001/8002 no se exponen | 1:30 |
| 11 | **Integración II** | Los clientes PLN: `AsyncClient` reutilizable, reintentos, `PlnServiceError` | 1:00 |
| 12 | **Integración III** | Flutter: contrato con el gateway, refresh de token en 401, cola offline con sqflite | 1:30 |
| 13 | **RAG — idea futura I** | El hueco: el clasificador dice qué tiene el alumno, nadie dice qué hacer ni con qué fundamento | 1:30 |
| 14 | **RAG — idea futura II** | Cómo se construiría, y el resto del trabajo pendiente | 1:30 |
| 15 | Cierre | Qué se llevan y preguntas | — |

**Marcado visual obligatorio:** las diapositivas 13 y 14 llevan un distintivo
inequívoco (etiqueta "propuesta, no implementado") para que nadie salga de la sala
creyendo que el asistente existe.

### Diapositivas de respaldo

1. Inventario completo de huecos del proyecto, por si preguntan por el estado real.
2. Costo y latencia estimados del RAG propuesto.
3. Por qué scikit-learn y no aprendizaje profundo.

## 5. Contenido de las diapositivas de RAG

Se presentan como diseño, no como implementación.

**Diapositiva 13 — el problema.** `diagnosis_service` clasifica subtipo y
severidad. `recommendation_service` entrega una ruta de ejercicios desde bancos
JSON etiquetados a mano. Entre ambos queda un hueco: el docente no tiene forma de
preguntar en lenguaje natural, y el material digitalizado
(`docs/recursos_dislexia.md`, los dos bancos, los cuadernillos en PDF) no es
consultable. Un dato concreto del propio repositorio ancla el argumento: 6º grado
tiene 0 ejercicios en el banco, y el servicio lo señala con
`grade_appropriate: false` sin poder resolverlo.

**Diapositiva 14 — cómo se construiría.** Cuatro pasos, sin código:

1. Ingesta y troceado del material existente, con metadatos de origen.
2. Embeddings locales (384 dimensiones) — el material no sale del sistema para
   vectorizarse.
3. Almacenamiento vectorial en el PostgreSQL que ya existe, con pgvector.
4. Generación con un LLM sobre el contexto recuperado, con dos reglas duras:
   citar la fuente de cada afirmación y admitir cuando el material no cubre la
   pregunta.

Más el resto del trabajo futuro, en una línea cada uno: CI/CD, observabilidad,
reentrenamiento con detección de deriva, y completar el banco de 4º a 6º.

Y una advertencia que conviene decir en voz alta: un RAG sobre material clínico
puede sonar convincente y estar equivocado, así que la citación obligatoria no es
un adorno sino el requisito que lo hace utilizable por un docente.

## 6. Guion

`guion.md` con, por diapositiva: qué se dice, cuánto dura, y qué no se dice.

Sección final con respuestas preparadas:

- ¿Por qué scikit-learn y no una red neuronal?
- ¿Cómo saben que el modelo sigue siendo válido? *(Respuesta honesta: hay
  versionado y umbrales, no hay detección de deriva.)*
- ¿Está esto en producción de verdad? *(Referencia al incidente de Railway y al
  fallback local.)*
- ¿Qué pasa con los datos de menores?
- ¿Por qué no implementaron el RAG?
- ¿Cuánto costaría operarlo?

## 7. Estilo de las slides

- HTML autocontenido: sin CDN, sin fuentes remotas, sin imágenes externas. Los
  diagramas se hacen con HTML y CSS, o con bloques mermaid si el renderizador los
  soporta.
- Navegación por teclado y responsiva.
- Tema claro y oscuro.
- Densidad baja: la diapositiva apoya al expositor, no lo sustituye. El detalle
  vive en el guion.

## 8. Criterios de aceptación

1. `index.html` contiene las 15 diapositivas más las 3 de respaldo y se renderiza
   sin ninguna petición de red externa.
2. Toda afirmación sobre el estado del proyecto puede señalarse en un archivo del
   repositorio.
3. Las diapositivas 13 y 14 están marcadas visualmente como propuesta.
4. La sección "lo que no tenemos" aparece en el material y no se omite.
5. `guion.md` cubre las 15 diapositivas con tiempos que suman entre 15 y 20
   minutos.
6. **No hay cambios en `api/`, `Pln/`, `database/`, `app/` ni
   `docker-compose.yml`.**
