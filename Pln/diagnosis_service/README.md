# CogniFit — Diagnosis Service

Microservicio FastAPI que expone el pipeline **PLN + ML** para la detección de riesgo
de dislexia. Recibe las respuestas crudas de un test y devuelve el diagnóstico
probabilístico (subtipo, severidad, riesgo).

## Estructura

```
diagnosis_service/
├── app/
│   ├── main.py              ← FastAPI: endpoints /health, /model/info, /diagnose
│   ├── pipeline.py          ← orquestador: encadena PLN + ML
│   ├── pln/
│   │   ├── preprocessor.py  ← limpieza, STT, manejo de timeouts
│   │   ├── error_detector.py← detección de errores (Levenshtein + reglas)
│   │   ├── phonetics.py     ← Metaphone + n-gramas
│   │   └── features.py      ← feature vector de 28 dimensiones
│   ├── ml/
│   │   └── predictor.py     ← carga los .pkl y predice
│   ├── models/              ← subtype_model_latest.pkl, severity_model_latest.pkl
│   └── tede_scoring.py      ← lookup de percentiles TEDE
├── data/
│   └── lexico_es_2000.json  ← léxico para detección de lexicalización
├── tests/
│   └── test_api.py          ← 7 tests (pytest)
├── requirements.txt
├── Dockerfile
└── README.md
```

## Cómo correrlo localmente

```bash
cd diagnosis_service
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8001
```

La API queda en `http://localhost:8001`.
Documentación interactiva automática en `http://localhost:8001/docs` (Swagger UI).

## Cómo correrlo con Docker

```bash
docker build -t cognifit-diagnosis .
docker run -p 8001:8001 cognifit-diagnosis
```

## Endpoints

### `GET /health`
Estado del servicio. Lo consulta el panel admin para el monitoreo (HU-BK-12).
```json
{"status": "ok", "service": "diagnosis", "models_loaded": true}
```

### `GET /model/info`
Versión y métricas de los modelos activos (HU-BK-13).

### `POST /diagnose`
Recibe una sesión completa y devuelve el diagnóstico.

**Request:**
```json
{
  "student_id": 21,
  "grade": 2,
  "teacher_score": 72.0,
  "session_number": 1,
  "items": [
    {"target": "plime", "response": "pime", "module": "pseudopalabras",
     "response_time_ms": 6500, "input_method": "stt"},
    {"target": "casa", "response": "casa", "module": "palabras_reales",
     "response_time_ms": 2100, "input_method": "stt"}
  ]
}
```

**Response:**
```json
{
  "subtype": "fonologico",
  "subtype_confidence": 0.662,
  "severity": "moderado",
  "severity_confidence": 0.58,
  "risk_probability": 0.994,
  "risk_level": "alto",
  "model_version": "20260618_0309",
  "main_error_codes": ["OMI", "INV"],
  "error_breakdown": {"OMI": 4, "INV": 2},
  "items_processed": 6,
  "items_timeout": 0,
  "feature_vector": [...]
}
```

## Integración con el resto del sistema

```
Flutter app → API Gateway (valida JWT) → Test Service
                                              │
                                              │ POST /diagnose
                                              ▼
                                       Diagnosis Service  (este servicio)
                                              │
                                              │ { subtype, severity, risk... }
                                              ▼
                                       Recommendation Service
                                              │ usa subtype + severity
                                              ▼  para elegir la ruta de ejercicios
```

El `teacher_score` viene del cuestionario PRODISLEX (ver `prodislex_cognifit_unificado.json`).
Los módulos válidos son: `pseudopalabras`, `palabras_reales`, `dictado`,
`lectura_voz_alta`, `copia_controlada`.

## Tests

```bash
pytest tests/ -v
```

## Re-entrenar los modelos

Los `.pkl` en `app/models/` se generan con el notebook
`CogniFit_Entrenamiento_Clasificador.ipynb`. Cuando tengas datos reales:

1. Re-entrena en el notebook → genera nuevos `subtype_model_latest.pkl` y `severity_model_latest.pkl`
2. Cópialos a `app/models/`
3. Reinicia el servicio (o llama a un futuro endpoint `/model/reload`)

El servicio **no necesita reentrenarse**; solo carga los `.pkl` que el notebook produce.

---

*CogniFit Escolar — El sistema no emite diagnósticos clínicos. Detecta indicadores de
riesgo y orienta al docente.*
