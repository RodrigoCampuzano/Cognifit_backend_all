# Ejemplos de uso del Diagnosis Service con curl
# Levanta primero el servicio:  uvicorn app.main:app --port 8001

# ─── 1. Health check ─────────────────────────────────────────────────────────
curl http://localhost:8001/health

# ─── 2. Info de modelos ──────────────────────────────────────────────────────
curl http://localhost:8001/model/info

# ─── 3. Diagnóstico — alumno fonológico ──────────────────────────────────────
curl -X POST http://localhost:8001/diagnose \
  -H "Content-Type: application/json" \
  -d '{
    "student_id": 21,
    "grade": 2,
    "teacher_score": 72.0,
    "session_number": 1,
    "items": [
      {"target": "plime", "response": "pime", "module": "pseudopalabras", "response_time_ms": 6500},
      {"target": "dubre", "response": "dube", "module": "pseudopalabras", "response_time_ms": 7200},
      {"target": "casa", "response": "casa", "module": "palabras_reales", "response_time_ms": 2100},
      {"target": "perro", "response": "pero", "module": "dictado", "response_time_ms": 3200}
    ]
  }'

# ─── 4. Diagnóstico — alumno visual (rotaciones b/d) ─────────────────────────
curl -X POST http://localhost:8001/diagnose \
  -H "Content-Type: application/json" \
  -d '{
    "student_id": 1,
    "grade": 3,
    "teacher_score": 60.0,
    "items": [
      {"target": "dado", "response": "bado", "module": "pseudopalabras", "response_time_ms": 3000},
      {"target": "pollo", "response": "qollo", "module": "pseudopalabras", "response_time_ms": 3200},
      {"target": "bota", "response": "dota", "module": "palabras_reales", "response_time_ms": 2800}
    ]
  }'
