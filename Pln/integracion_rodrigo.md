# CogniFit Escolar — Documentación de Integración
## Servicios Python (Carlos) → Backend Go (Rodrigo)

> Este documento describe exactamente cómo llamar a los dos microservicios
> Python desde el backend Go. No es necesario leer el código fuente.

---

## Servicios disponibles

| Servicio | Puerto | Responsabilidad |
|---|---|---|
| Diagnosis Service | `8001` | PLN + ML → produce el diagnóstico del alumno |
| Recommendation Service | `8002` | Devuelve la ruta de ejercicios según el diagnóstico |

Ambos servicios deben estar corriendo antes de que el Test Service los llame.
Para verificar que están vivos:

```
GET http://localhost:8001/health
GET http://localhost:8002/health
```

Ambos responden `{"status": "ok"}` si están listos.

---

## Flujo de integración

```
[Flutter — alumno termina test]
         │
         ▼
[Test Service Go]
   guarda respuestas crudas en BD
         │
         │ 1. POST /diagnose ──────────────────────────▶ [Diagnosis Service :8001]
         │ ◀─────────────────── { subtype, severity, risk_probability, ... } ───
         │
   guarda diagnóstico en BD (tabla diagnosticos)
         │
         │ 2. POST /recommend ─────────────────────────▶ [Recommendation Service :8002]
         │ ◀─────────────────── { exercises: [ ... ] } ──────────────────────────
         │
   guarda ruta en BD (tabla rutas_aprendizaje)
         │
         ▼
[Exercise Service Go — entrega ejercicios al alumno]
         │
         │ 3. POST /next-exercise (después de cada sesión)
         │ ──────────────────────────────────────────────▶ [Recommendation Service :8002]
         │ ◀─────────── { exercise_id, action: "level_up"|"continue"|... } ──────
```

---

## 1. Diagnosis Service — `POST /diagnose`

### Cuándo llamarlo
Inmediatamente después de que el alumno termina el test y las respuestas
están guardadas en BD.

### Request

```
POST http://localhost:8001/diagnose
Content-Type: application/json
```

```json
{
  "student_id": 21,
  "grade": 2,
  "teacher_score": 72.0,
  "session_number": 1,
  "items": [
    {
      "target": "plime",
      "response": "pime",
      "module": "pseudopalabras",
      "response_time_ms": 6500,
      "difficulty_level": 2,
      "input_method": "stt"
    },
    {
      "target": "casa",
      "response": "casa",
      "module": "palabras_reales",
      "response_time_ms": 2100,
      "difficulty_level": 1,
      "input_method": "stt"
    }
  ]
}
```

### Campos del request

| Campo | Tipo | Requerido | Descripción |
|---|---|---|---|
| `student_id` | int | ✅ | ID del alumno en tu BD |
| `grade` | int (1-6) | ✅ | Grado escolar del alumno |
| `teacher_score` | float (0-100) | ✅ | Score del cuestionario PRODISLEX. Si no se aplicó, manda `0.0` |
| `session_number` | int | No | Número de sesión del alumno (default 1) |
| `items` | array | ✅ | Lista de ítems del test (mínimo 1) |

### Campos de cada ítem

| Campo | Tipo | Requerido | Descripción |
|---|---|---|---|
| `target` | string | ✅ | Texto/palabra que debía producir el alumno |
| `response` | string | ✅ | Texto que produjo el alumno. Manda `""` si no respondió (timeout) |
| `module` | string | ✅ | Ver tabla de módulos abajo |
| `response_time_ms` | int | ✅ | Tiempo de respuesta en milisegundos |
| `difficulty_level` | int | No | Nivel de dificultad del ítem (default 1) |
| `input_method` | string | No | `"stt"`, `"teclado"` o `"tactil"` (default `"stt"`) |

### Valores válidos para `module`

| Valor | Descripción |
|---|---|
| `pseudopalabras` | Lectura de pseudopalabras (discriminador fonológico vs visual) |
| `palabras_reales` | Lectura de palabras reales |
| `dictado` | Dictado inteligente |
| `lectura_voz_alta` | Lectura en voz alta |
| `copia_controlada` | Copia controlada (no aplica corrección STT) |
| `conciencia_fonologica` | Tareas de conciencia fonológica |
| `denominacion_rapida` | Denominación rápida (RAN) |
| `comprension_lectora` | Comprensión lectora |

> **Nota sobre timeouts:** Si el alumno no respondió un ítem, manda
> `"response": ""` y `response_time_ms` mayor a 15000. El servicio lo
> detecta automáticamente como timeout y lo cuenta como omisión total.

### Response exitosa `200`

```json
{
  "subtype": "fonologico",
  "subtype_confidence": 0.68,
  "severity": "leve",
  "severity_confidence": 0.48,
  "risk_probability": 0.994,
  "risk_level": "alto",
  "model_version": "20260618_0309",
  "main_error_codes": ["OMI", "INV"],
  "error_breakdown": {
    "OMI": 4,
    "INV": 2,
    "ROT": 1
  },
  "items_processed": 10,
  "items_timeout": 0,
  "feature_vector": [0.4, 0.0, 0.2, ...]
}
```

### Campos de la response que debes guardar en BD

| Campo | Guardar en BD | Descripción |
|---|---|---|
| `subtype` | ✅ Sí | Subtipo de dislexia detectado |
| `severity` | ✅ Sí | Severidad detectada |
| `risk_probability` | ✅ Sí | Probabilidad de riesgo (0.0–1.0) |
| `risk_level` | ✅ Sí | `"bajo"`, `"medio"` o `"alto"` |
| `main_error_codes` | ✅ Sí | Lista de errores predominantes |
| `error_breakdown` | ✅ Sí | Conteo de cada tipo de error (guardar como JSONB) |
| `model_version` | ✅ Sí | Versión del modelo que generó el diagnóstico |
| `subtype_confidence` | Opcional | Confianza del modelo en el subtipo |
| `feature_vector` | Opcional | Vector de 28 dimensiones (guardar como JSONB si quieres) |

### Valores posibles de `subtype`

| Valor | Significado |
|---|---|
| `fonologico` | Dislexia fonológica — falla en pseudopalabras |
| `visual` | Dislexia visual/superficial — confusiones b/d/p/q |
| `mixto` | Combinación de ambos perfiles |
| `fluidez` | Lee bien pero muy lento |
| `sin_riesgo` | Sin indicadores de dislexia |

### Valores posibles de `severity`

| Valor | Significado |
|---|---|
| `leve` | Indicadores leves |
| `moderado` | Indicadores moderados |
| `severo` | Indicadores severos |
| `ninguna` | Solo aplica cuando subtype es `sin_riesgo` |

### Valores posibles de `main_error_codes`

| Código | Error |
|---|---|
| `OMI` | Omisión de letra o sílaba |
| `SUS` | Sustitución de letra |
| `INV` | Inversión de letras o sílabas |
| `ROT` | Rotación visual (b↔d, p↔q) |
| `LEX` | Lexicalización (pseudopalabra → palabra real) |
| `ADD` | Adición de letra |
| `FON` | Error fonológico |
| `SEG` | Segmentación incorrecta |
| `UNI` | Unión incorrecta de palabras |
| `LEN` | Respuesta correcta pero lenta |

### Errores posibles

| Código HTTP | Cuándo ocurre |
|---|---|
| `200` | Diagnóstico generado correctamente |
| `422` | Request inválido (campo faltante o tipo incorrecto) |
| `503` | Modelos no cargados (el servicio está arrancando) |
| `500` | Error interno del pipeline |

---

## 2. Recommendation Service — `POST /recommend`

### Cuándo llamarlo
Inmediatamente después de guardar el diagnóstico en BD.
Usa `subtype` y `severity` que devolvió el Diagnosis Service.

### Request

```
POST http://localhost:8002/recommend
Content-Type: application/json
```

```json
{
  "student_id": 21,
  "subtype": "fonologico",
  "severity": "leve",
  "risk_probability": 0.994,
  "grade": 2
}
```

### Campos del request

| Campo | Tipo | Requerido | Descripción |
|---|---|---|---|
| `student_id` | int | ✅ | ID del alumno |
| `subtype` | string | ✅ | Viene directo del Diagnosis Service |
| `severity` | string | ✅ | Viene directo del Diagnosis Service |
| `risk_probability` | float | No | Viene directo del Diagnosis Service |
| `grade` | int | No | Grado escolar |

### Response exitosa `200`

```json
{
  "student_id": 21,
  "subtype": "fonologico",
  "severity": "leve",
  "total_exercises": 5,
  "exercises": [
    {
      "exercise_id": "CF_silabas_N1",
      "order": 1,
      "tipo": "conciencia_fonologica",
      "titulo": "¿Cuántas sílabas tiene?",
      "usa_tts": true,
      "usa_stt": false,
      "nivel": 1
    },
    {
      "exercise_id": "CF_fonema_inicial_N1",
      "order": 2,
      "tipo": "conciencia_fonologica",
      "titulo": "¿Con qué sonido empieza?",
      "usa_tts": true,
      "usa_stt": true,
      "nivel": 1
    }
  ],
  "message": "Ruta adaptativa generada: 5 ejercicios para perfil fonologico/leve."
}
```

### Campos que debes guardar en BD

| Campo | Guardar en BD | Descripción |
|---|---|---|
| `exercises[].exercise_id` | ✅ Sí | IDs ordenados de la ruta (guardar como array o JSONB) |
| `total_exercises` | ✅ Sí | Total de ejercicios en la ruta |
| `exercises[].usa_tts` | ✅ Sí | El Exercise Service necesita saber si activar TTS |
| `exercises[].usa_stt` | ✅ Sí | El Exercise Service necesita saber si activar STT |

### Response para `sin_riesgo`

Cuando el subtipo es `sin_riesgo`, la ruta es vacía y no hay intervención:

```json
{
  "student_id": 3,
  "subtype": "sin_riesgo",
  "severity": "ninguna",
  "total_exercises": 0,
  "exercises": [],
  "message": "Sin riesgo detectado. Se activa monitoreo periódico sin intervención."
}
```

### Errores posibles

| Código HTTP | Cuándo ocurre |
|---|---|
| `200` | Ruta generada correctamente |
| `404` | Subtipo o severidad no reconocidos |
| `422` | Request inválido |

---

## 3. Recommendation Service — `POST /next-exercise`

### Cuándo llamarlo
Después de que el alumno completa una sesión de ejercicio.
El Exercise Service lo llama para saber qué ejercicio sigue.

### Request

```
POST http://localhost:8002/next-exercise
Content-Type: application/json
```

```json
{
  "student_id": 21,
  "current_route": [
    "CF_silabas_N1",
    "CF_fonema_inicial_N1",
    "PS_cv_N1"
  ],
  "session_history": [
    {"exercise_id": "CF_silabas_N1", "accuracy": 0.95},
    {"exercise_id": "CF_silabas_N1", "accuracy": 0.92},
    {"exercise_id": "CF_silabas_N1", "accuracy": 0.91}
  ]
}
```

### Campos del request

| Campo | Tipo | Descripción |
|---|---|---|
| `student_id` | int | ID del alumno |
| `current_route` | array de strings | Lista de exercise_ids de la ruta activa (en orden) |
| `session_history` | array de objetos | Historial de sesiones: `{exercise_id, accuracy}` donde accuracy va de 0.0 a 1.0 |

### Response

```json
{
  "student_id": 21,
  "exercise_id": "CF_fonema_inicial_N1",
  "action": "level_up",
  "trigger": "accuracy 93% en 3 sesiones",
  "support": null,
  "exercise_detail": {
    "exercise_id": "CF_fonema_inicial_N1",
    "tipo": "conciencia_fonologica",
    "titulo": "¿Con qué sonido empieza?",
    "usa_tts": true,
    "usa_stt": true,
    ...
  }
}
```

### Valores posibles de `action`

| Valor | Qué debe hacer el Exercise Service |
|---|---|
| `start` | Primera sesión — entregar el primer ejercicio de la ruta |
| `continue` | Accuracy normal — entregar el mismo ejercicio |
| `level_up` | Accuracy alta — entregar el siguiente ejercicio de la ruta |
| `add_support` | Accuracy baja — entregar el mismo ejercicio pero activar TTS |
| `route_completed` | El alumno completó toda la ruta — notificar al docente |
| `route_empty` | La ruta está vacía (sin_riesgo) |

---

## 4. Recommendation Service — `GET /exercises/{exercise_id}`

### Cuándo llamarlo
Cuando el Exercise Service necesita el contenido completo de un ejercicio
para entregárselo a Flutter.

### Request

```
GET http://localhost:8002/exercises/CF_silabas_N1
```

### Response

```json
{
  "exercise_id": "CF_silabas_N1",
  "tipo": "conciencia_fonologica",
  "subtipo": "segmentacion_silabica",
  "perfil_objetivo": ["fonologico", "mixto"],
  "nivel": 1,
  "grados": ["1", "2"],
  "titulo": "¿Cuántas sílabas tiene?",
  "instruccion": "Escucha la palabra y toca cuántas sílabas tiene.",
  "modalidad": "tactil_tts",
  "usa_tts": true,
  "usa_stt": false,
  "items": [
    {"palabra": "sol",      "silabas": 1},
    {"palabra": "casa",     "silabas": 2},
    {"palabra": "camino",   "silabas": 3},
    {"palabra": "mariposa", "silabas": 4}
  ]
}
```

---

## 5. Ejemplo completo en Go

```go
package main

import (
    "bytes"
    "encoding/json"
    "fmt"
    "net/http"
)

// ── Structs ──────────────────────────────────────────────────────────────────

type TestItem struct {
    Target          string `json:"target"`
    Response        string `json:"response"`
    Module          string `json:"module"`
    ResponseTimeMs  int    `json:"response_time_ms"`
    DifficultyLevel int    `json:"difficulty_level"`
    InputMethod     string `json:"input_method"`
}

type DiagnoseRequest struct {
    StudentID     int        `json:"student_id"`
    Grade         int        `json:"grade"`
    TeacherScore  float64    `json:"teacher_score"`
    SessionNumber int        `json:"session_number"`
    Items         []TestItem `json:"items"`
}

type DiagnoseResponse struct {
    Subtype            string         `json:"subtype"`
    SubtypeConfidence  float64        `json:"subtype_confidence"`
    Severity           string         `json:"severity"`
    RiskProbability    float64        `json:"risk_probability"`
    RiskLevel          string         `json:"risk_level"`
    ModelVersion       string         `json:"model_version"`
    MainErrorCodes     []string       `json:"main_error_codes"`
    ErrorBreakdown     map[string]int `json:"error_breakdown"`
    ItemsProcessed     int            `json:"items_processed"`
    ItemsTimeout       int            `json:"items_timeout"`
}

type RecommendRequest struct {
    StudentID       int     `json:"student_id"`
    Subtype         string  `json:"subtype"`
    Severity        string  `json:"severity"`
    RiskProbability float64 `json:"risk_probability"`
    Grade           int     `json:"grade"`
}

type ExerciseRef struct {
    ExerciseID string `json:"exercise_id"`
    Order      int    `json:"order"`
    Titulo     string `json:"titulo"`
    UsaTTS     bool   `json:"usa_tts"`
    UsaSTT     bool   `json:"usa_stt"`
    Nivel      int    `json:"nivel"`
}

type RecommendResponse struct {
    StudentID      int           `json:"student_id"`
    Subtype        string        `json:"subtype"`
    Severity       string        `json:"severity"`
    TotalExercises int           `json:"total_exercises"`
    Exercises      []ExerciseRef `json:"exercises"`
    Message        string        `json:"message"`
}

// ── Helpers ──────────────────────────────────────────────────────────────────

func postJSON(url string, body interface{}, result interface{}) error {
    data, err := json.Marshal(body)
    if err != nil {
        return err
    }
    resp, err := http.Post(url, "application/json", bytes.NewBuffer(data))
    if err != nil {
        return err
    }
    defer resp.Body.Close()
    return json.NewDecoder(resp.Body).Decode(result)
}

// ── Flujo principal ───────────────────────────────────────────────────────────

func DiagnoseAndRecommend(studentID, grade int, teacherScore float64, items []TestItem) error {

    // 1. Llamar al Diagnosis Service
    diagReq := DiagnoseRequest{
        StudentID:     studentID,
        Grade:         grade,
        TeacherScore:  teacherScore,
        SessionNumber: 1,
        Items:         items,
    }
    var diagResp DiagnoseResponse
    if err := postJSON("http://localhost:8001/diagnose", diagReq, &diagResp); err != nil {
        return fmt.Errorf("error llamando Diagnosis Service: %w", err)
    }

    fmt.Printf("Diagnóstico: %s / %s / riesgo %s (%.2f)\n",
        diagResp.Subtype, diagResp.Severity,
        diagResp.RiskLevel, diagResp.RiskProbability)

    // 2. Guardar diagnóstico en BD (tu lógica aquí)
    // db.SaveDiagnosis(studentID, diagResp)

    // 3. Llamar al Recommendation Service
    recReq := RecommendRequest{
        StudentID:       studentID,
        Subtype:         diagResp.Subtype,
        Severity:        diagResp.Severity,
        RiskProbability: diagResp.RiskProbability,
        Grade:           grade,
    }
    var recResp RecommendResponse
    if err := postJSON("http://localhost:8002/recommend", recReq, &recResp); err != nil {
        return fmt.Errorf("error llamando Recommendation Service: %w", err)
    }

    fmt.Printf("Ruta: %d ejercicios\n", recResp.TotalExercises)
    for _, ex := range recResp.Exercises {
        fmt.Printf("  %d. %s (%s)\n", ex.Order, ex.ExerciseID, ex.Titulo)
    }

    // 4. Guardar ruta en BD (tu lógica aquí)
    // db.SaveRoute(studentID, recResp.Exercises)

    return nil
}
```

---

## 6. Notas importantes

**Sobre el `teacher_score`:**
Es el score del cuestionario PRODISLEX (0–100). Si Rodrigo no implementa
ese cuestionario todavía, manda `0.0` — el modelo funciona igual, solo
pierde esa feature.

**Sobre el número de ítems:**
El diagnóstico es más confiable con más ítems. Con 2-3 ítems funciona
pero la confianza del modelo es baja. Con 10+ ítems la predicción es sólida.
En producción, una batería completa tiene entre 40 y 80 ítems en total.

**Sobre los módulos:**
El módulo más importante es `pseudopalabras` — es el principal discriminador
entre dislexia fonológica y visual. Si solo puedes mandar un tipo de ítem
al principio, que sean pseudopalabras.

**Sobre los puertos:**
En desarrollo local: `8001` (Diagnosis) y `8002` (Recommendation).
En Docker/producción: los puertos los configura el API Gateway de Rodrigo.

**Sobre errores del servicio:**
Si algún servicio devuelve `503`, significa que está arrancando todavía.
Espera 5 segundos y reintenta. Si devuelve `500`, revisa el log del servicio.
