# CogniFit — Recommendation Service

Microservicio FastAPI que asigna rutas de aprendizaje adaptativas a partir del
diagnóstico producido por el Diagnosis Service.

## Estructura

```
recommendation_service/
├── app/
│   ├── main.py      ← FastAPI: /health, /recommend, /next-exercise, /exercises/{id}, /routes
│   └── routes.py    ← LEARNING_ROUTES + lógica de recalibración
├── data/
│   └── banco_ejercicios_intervencion.json  ← 29 exercise_ids con contenido
├── tests/
│   └── test_api.py  ← 13 tests (pytest)
├── requirements.txt
├── Dockerfile
└── README.md
```

## Cómo correrlo

```bash
pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 8002
```

Swagger en `http://localhost:8002/docs`

## Endpoints

### `GET /health`
```json
{"status": "ok", "service": "recommendation", "exercises_loaded": 29}
```

### `GET /routes`
Lista todas las rutas disponibles (15 combinaciones de subtipo × severidad).

### `POST /recommend`
Recibe el diagnóstico y devuelve la ruta completa.

**Request:**
```json
{
  "student_id": 21,
  "subtype": "fonologico",
  "severity": "leve",
  "risk_probability": 0.994,
  "grade": 2
}
```

**Response:**
```json
{
  "student_id": 21,
  "subtype": "fonologico",
  "severity": "leve",
  "total_exercises": 5,
  "exercises": [
    {"exercise_id": "CF_silabas_N1",        "order": 1, "titulo": "¿Cuántas sílabas tiene?", "tipo": "conciencia_fonologica", "usa_tts": true,  "nivel": 1},
    {"exercise_id": "CF_fonema_inicial_N1", "order": 2, "titulo": "¿Con qué sonido empieza?","tipo": "conciencia_fonologica", "usa_tts": true,  "nivel": 1},
    {"exercise_id": "CF_rima_N1",           "order": 3, "titulo": "¿Cuál rima?",             "tipo": "conciencia_fonologica", "usa_tts": true,  "nivel": 1},
    {"exercise_id": "PS_cv_N1",             "order": 4, "titulo": "Lee esta palabra inventada","tipo": "pseudopalabras",        "usa_stt": true, "nivel": 1},
    {"exercise_id": "DIC_palabras_simples_N1","order":5,"titulo": "Escribe lo que escuchas", "tipo": "dictado",               "usa_tts": true,  "nivel": 1}
  ],
  "message": "Ruta adaptativa generada: 5 ejercicios para perfil fonologico/leve."
}
```

### `POST /next-exercise`
Decide el próximo ejercicio basado en el historial de sesiones.

**Request:**
```json
{
  "student_id": 21,
  "current_route": ["CF_silabas_N1", "CF_fonema_inicial_N1", "PS_cv_N1"],
  "session_history": [
    {"exercise_id": "CF_silabas_N1", "accuracy": 0.95},
    {"exercise_id": "CF_silabas_N1", "accuracy": 0.92},
    {"exercise_id": "CF_silabas_N1", "accuracy": 0.91}
  ]
}
```

**Response:**
```json
{
  "student_id": 21,
  "exercise_id": "CF_fonema_inicial_N1",
  "action": "level_up",
  "trigger": "accuracy 93% en 3 sesiones",
  "exercise_detail": { ... }
}
```

**Valores posibles de `action`:**
| Valor | Significado |
|---|---|
| `start` | Primera sesión, empieza en el primer ejercicio |
| `continue` | Accuracy entre 40-90%, continúa en el mismo |
| `level_up` | Accuracy > 90%, sube al siguiente ejercicio |
| `add_support` | Accuracy < 40%, activa TTS de apoyo |
| `route_completed` | Completó todos los ejercicios de la ruta |

### `GET /exercises/{exercise_id}`
Detalle completo de un ejercicio con todos sus ítems.

## Flujo de integración

```
Diagnosis Service
      │ { subtype: "fonologico", severity: "leve", ... }
      │ POST /recommend
      ▼
Recommendation Service  (este servicio, puerto 8002)
      │ { exercises: [ CF_silabas_N1, CF_fonema_inicial_N1, ... ] }
      ▼
Exercise Service
      │ entrega ejercicios al alumno uno por uno
      │ después de cada sesión → POST /next-exercise
      ▼
Flutter (alumno practica)
```

## Tests

```bash
pytest tests/ -v
# 13 passed
```
