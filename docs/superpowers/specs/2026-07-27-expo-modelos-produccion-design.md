# Expo "Modelos en producción" + Asistente RAG — Diseño

**Fecha:** 2026-07-27
**Estado:** aprobado, pendiente de plan de implementación

## 1. Objetivo

Preparar una exposición de 15–20 minutos sobre modelos en producción —inferencia,
despliegue, RAG e integración con backend y frontend— usando CogniFit como caso
real, e implementar el bloque de RAG de verdad en el repositorio para que la
exposición demuestre código que existe y no un diagrama aspiracional.

Dos entregables acoplados:

1. **Material de exposición**: slides HTML publicables + guion del expositor.
2. **Asistente RAG funcional**: microservicio nuevo, migración de base de datos,
   ruta en el API gateway y pantalla Flutter mínima.

## 2. Alcance

### Dentro

- Slides navegables en HTML autocontenido, publicables como artifact.
- Guion por diapositiva con tiempos y respuestas a preguntas probables.
- Microservicio `rag_service` con ingesta, recuperación y generación.
- Migración pgvector y cambio de imagen de PostgreSQL.
- Ruta autenticada en el API gateway que expone el asistente.
- Pantalla Flutter que consume esa ruta.

### Fuera

- Reentrenamiento o modificación de los modelos `subtype`/`severity` existentes.
- Ingesta de los cuadernillos PDF de `docs/pdfs/` (decisión C: se pospone).
- Evaluación cuantitativa del RAG (recall@k, ragas). Se menciona en las slides
  como trabajo siguiente, no se implementa.
- Cualquier cambio a los flujos de pago, screening o intervención existentes.

## 3. Contexto del repositorio

CogniFit ya tiene modelos en producción. La exposición documenta lo que existe y
añade la pieza que falta:

| Componente | Estado | Puerto |
|---|---|---|
| `api/` — gateway FastAPI (clean architecture) | existe | 8000 |
| `Pln/diagnosis_service` — pipeline PLN 28D + 2 modelos sklearn `.pkl` | existe | 8001 |
| `Pln/recommendation_service` — ruta adaptativa desde bancos JSON | existe | 8002 |
| PostgreSQL 16 + Redis 7 | existe | 5432 / 6379 |
| `app/cognifit_mobile` — Flutter, clean architecture por feature | existe | — |
| `Pln/rag_service` — asistente documental | **nuevo** | 8003 |

Patrones a respetar, ya establecidos en el repositorio:

- Los microservicios PLN son FastAPI con `lifespan` que carga artefactos una sola
  vez, endpoints `/health` y `/model/info`, y `Dockerfile` con `BIND_HOST`
  configurable (`::` por defecto para Railway, `0.0.0.0` fijado en
  `docker-compose.yml` para la red IPv4 de Compose).
- El gateway habla con los servicios PLN mediante clientes en
  `api/infrastructure/pln/`, con `AsyncClient` reutilizable, reintentos y
  `PlnServiceError`.
- Los routers viven en `api/api/v1/<dominio>/` y se registran en
  `api/api/main.py` con `prefix=settings.api_v1_prefix`.
- Las migraciones SQL son archivos numerados en `database/`, montados en
  `docker-entrypoint-initdb.d` por `docker-compose.yml`.
- Las features Flutter siguen `features/<nombre>/{data,domain,presentation}`.

## 4. Diseño del asistente RAG

### 4.1 Caso de uso

El docente o especialista pregunta en lenguaje natural qué actividades aplicar a
un alumno con un perfil determinado. El asistente responde fundamentando la
respuesta en el material digitalizado y citando la fuente de cada afirmación.

Esto complementa a los modelos existentes: `diagnosis_service` dice *qué tiene el
alumno*; el asistente dice *qué hago al respecto y de dónde lo saco*.

### 4.2 Estructura del servicio

```
Pln/rag_service/
├── app/
│   ├── __init__.py
│   ├── main.py           # FastAPI: /health, /ingest, /consultar
│   ├── config.py         # lectura de variables de entorno
│   ├── embeddings.py     # modelo local de embeddings, 384 dimensiones
│   ├── retriever.py      # búsqueda por similitud coseno en pgvector
│   ├── generator.py      # generación con Claude
│   └── prompts.py        # system prompt y plantilla de contexto
├── ingest/
│   ├── __init__.py
│   ├── chunker.py        # markdown y JSON -> chunks con metadatos
│   └── run_ingest.py     # script ejecutable de ingesta
├── tests/
│   └── test_api.py
├── Dockerfile
├── requirements.txt
└── README.md
```

### 4.3 Embeddings

`fastembed` con `intfloat/multilingual-e5-small` (384 dimensiones, runtime ONNX).

Se elige sobre `sentence-transformers` porque este último arrastra PyTorch, que
añade aproximadamente 2 GB a la imagen Docker. El corpus es de cientos de chunks
y la calidad multilingüe de e5-small es suficiente para el caso de uso. El modelo
se descarga la primera vez y queda cacheado en la imagen.

Los embeddings se calculan en el propio servicio, no se envía texto a un
proveedor externo para vectorizar. Solo la pregunta y el contexto recuperado
viajan al LLM en el momento de generar.

### 4.4 Almacén vectorial

Migración `database/029_rag_pgvector.sql`:

- `CREATE EXTENSION IF NOT EXISTS vector;`
- Schema `rag`.
- Tabla `rag.documentos`:

  | Columna | Tipo | Notas |
  |---|---|---|
  | `id` | `bigserial` PK | |
  | `fuente` | `text NOT NULL` | ruta del archivo de origen |
  | `titulo` | `text NOT NULL` | encabezado o nombre del ejercicio |
  | `chunk` | `text NOT NULL` | fragmento indexado |
  | `metadata` | `jsonb NOT NULL DEFAULT '{}'` | código de ejercicio, nivel, módulo |
  | `embedding` | `vector(384) NOT NULL` | |
  | `creado_en` | `timestamptz NOT NULL DEFAULT now()` | |

- Índice `ivfflat` sobre `embedding` con `vector_cosine_ops`.
- Índice GIN sobre `metadata`.

**Cambio en `docker-compose.yml`:** la imagen de PostgreSQL pasa de
`postgres:16-alpine` a `pgvector/pgvector:pg16`. Es la misma versión mayor de
PostgreSQL con la extensión precompilada; el esquema y los volúmenes existentes
no cambian. La migración `029` se añade a la lista de archivos montados en
`docker-entrypoint-initdb.d`.

### 4.5 Ingesta

Script `ingest/run_ingest.py`, ejecutable dentro del contenedor. Corpus de la v1:

- `docs/recursos_dislexia.md` — troceado por encabezado de sección.
- `Pln/recommendation_service/data/banco_ejercicios_intervencion.json` — un chunk
  por ejercicio.
- `Pln/recommendation_service/data/banco_comprension_universal.json` — un chunk
  por ítem.

Chunking objetivo de aproximadamente 400 tokens con solape de 50. Cada chunk
conserva su título de sección para que la cita sea legible.

La ingesta es idempotente: borra por `fuente` y reinserta, de modo que volver a
ejecutarla no duplica filas.

### 4.6 Generación

SDK oficial `anthropic`, modelo `claude-opus-5`.

- `output_config={"effort": "low"}` — la tarea es sintetizar un contexto ya
  recuperado, no razonar en profundidad; el efecto en la latencia importa para la
  demostración en vivo.
- Sin configurar `thinking`: en Claude Opus 5 el pensamiento adaptativo está
  activo por omisión y desactivarlo introduce fallos conocidos.
- `max_tokens=4096`.
- La clave se lee de `ANTHROPIC_API_KEY` en el entorno. Nunca se escribe en el
  repositorio; se documenta en `api/.env.docker.example` y en el README del
  servicio.

Reglas del system prompt, en español de México:

1. Responder únicamente con el contexto recuperado.
2. Si el contexto no cubre la pregunta, decirlo explícitamente en vez de inventar.
3. Citar el título de la fuente de cada afirmación.
4. Dirigirse a un docente o especialista, no a un investigador.

### 4.7 Contrato HTTP

```
GET  /health
  -> {"status": "ok", "service": "rag", "documentos_indexados": 342}

POST /ingest
  -> {"insertados": 342, "fuentes": ["docs/recursos_dislexia.md", ...]}

POST /consultar
  {"pregunta": "¿Qué actividades uso para b/d en nivel 1?", "top_k": 5}
  -> {
       "respuesta": "...",
       "fuentes": [
         {"titulo": "...", "fuente": "...", "fragmento": "...", "score": 0.83}
       ],
       "modelo": "claude-opus-5"
     }
```

Errores: 503 mientras el modelo de embeddings carga, 502 si el LLM falla, 500 con
detalle en caso contrario. Se sigue el patrón de reintentos ya usado en
`DiagnosisServiceClient`.

## 5. Integración con el backend

- Cliente `api/infrastructure/pln/rag_client.py`, hermano de
  `diagnosis_client.py`: `AsyncClient` reutilizable, reintentos configurables,
  `PlnServiceError` al agotarlos.
- Router `api/api/v1/asistente/` con `POST /asistente/consultar`, registrado en
  `api/api/main.py` con el prefijo de la v1.
- Autenticación JWT ya existente, restringida a los roles `DOCENTE`,
  `ESPECIALISTA` y `ADMIN`.
- Variables nuevas en `api/.env.docker`, `.env.docker.example` y
  `.env.production`: `RAG_SERVICE_URL` y `ANTHROPIC_API_KEY`. Los tiempos de
  espera y reintentos reutilizan `PLN_TIMEOUT_SECONDS` y `PLN_RETRIES`.
- Servicio `rag_service` en `docker-compose.yml` con healthcheck y
  `depends_on: service_healthy` desde `api`, igual que los otros dos servicios
  PLN.

El gateway sigue siendo la única puerta pública: el puerto 8003 no se expone
hacia afuera en producción, solo dentro de la red de Compose.

## 6. Integración con el frontend

Feature nueva `app/cognifit_mobile/lib/features/asistente/`, siguiendo la
estructura por capas del resto de la aplicación:

```
features/asistente/
├── data/
│   ├── datasources/asistente_remote_datasource.dart
│   ├── models/consulta_model.dart
│   └── repositories/asistente_repository_impl.dart
├── domain/
│   ├── entities/respuesta_asistente.dart
│   └── repositories/asistente_repository.dart
└── presentation/
    └── screens/asistente_screen.dart
```

La pantalla es deliberadamente mínima: campo de pregunta, estado de carga,
respuesta y una lista de tarjetas de fuentes con título y fragmento citado.
Reutiliza el cliente HTTP y el manejo de tokens que ya existen en `core/network`.

## 7. Material de exposición

### 7.1 Archivos

- `docs/expo_modelos_produccion/index.html` — slides autocontenidas, sin recursos
  externos, con soporte de tema claro y oscuro, navegables por teclado.
- `docs/expo_modelos_produccion/guion.md` — guion por diapositiva.

### 7.2 Estructura de las 15 diapositivas

| # | Contenido | Minutos |
|---|---|---|
| 1 | Portada y tesis: entrenar es la parte fácil | 0:30 |
| 2 | Qué es CogniFit y las seis fases del flujo | 1:00 |
| 3 | Arquitectura: cinco servicios, un diagrama | 1:30 |
| 4 | Inferencia: del audio del alumno al vector de 28 dimensiones | 1:30 |
| 5 | Inferencia: dos modelos sklearn, subtipo y severidad | 1:30 |
| 6 | Inferencia: contrato de la API, `/model/info`, versionado | 1:00 |
| 7 | Despliegue: Docker multiservicio y healthchecks | 1:30 |
| 8 | Despliegue: qué se rompió en Railway y por qué | 1:30 |
| 9 | RAG: por qué un modelo predictivo no basta | 1:30 |
| 10 | RAG: ingesta, embeddings, pgvector, generación | 1:30 |
| 11 | RAG: anatomía de una respuesta con citas | 1:30 |
| 12 | Integración: el gateway como única puerta, JWT y roles | 1:30 |
| 13 | Integración: contrato Flutter y FastAPI | 1:30 |
| 14 | Aprendizajes: IPv6, arranque en frío, deriva del modelo | 1:30 |
| 15 | Cierre y preguntas | — |

Tres diapositivas de respaldo para preguntas: costo por consulta al LLM, criterio
de troceado, y qué se haría distinto.

### 7.3 Guion

Por diapositiva: qué se dice, cuánto dura y qué no se dice. Incluye una sección
final con respuestas preparadas a las preguntas más probables:

- ¿Por qué scikit-learn y no una red neuronal?
- ¿Cómo saben que el modelo sigue siendo válido?
- ¿El RAG puede inventarse una recomendación clínica?
- ¿Qué pasa con los datos de menores que se envían al LLM?
- ¿Cuánto cuesta operar esto?

## 8. Riesgos y decisiones tomadas

| Riesgo | Decisión |
|---|---|
| Cambiar la imagen de PostgreSQL puede romper el arranque existente | Se usa `pgvector/pgvector:pg16`, misma versión mayor; se verifica con `verify_db_integration.py` antes de dar por buena la migración |
| La imagen del servicio RAG puede crecer demasiado | `fastembed` con ONNX en lugar de PyTorch |
| El LLM puede inventar recomendaciones clínicas | Regla explícita en el system prompt, citas obligatorias, y se declara la limitación en la diapositiva 11 |
| Fuga de la clave de API | Solo por variable de entorno; el `.gitignore` ya cubre `.env.docker` |
| Datos de menores hacia un proveedor externo | El asistente consulta material didáctico, no expedientes; no se envían datos de alumnos en la consulta. Se explicita en el guion |

## 9. Criterios de aceptación

1. `docker compose up` levanta seis servicios y todos reportan sano.
2. `POST /ingest` en el servicio RAG indexa el corpus y devuelve un conteo mayor
   que cero.
3. `POST /api/v1/asistente/consultar` con un token de docente devuelve una
   respuesta con al menos una fuente citada.
4. La misma ruta sin token devuelve 401, y con un rol no autorizado devuelve 403.
5. Una pregunta fuera del corpus produce una respuesta que admite no saber, en
   lugar de inventar.
6. La pantalla Flutter muestra respuesta y fuentes contra el gateway local.
7. `docs/expo_modelos_produccion/index.html` se renderiza sin recursos externos y
   contiene las 15 diapositivas más las tres de respaldo.
8. Los tests existentes siguen pasando.
