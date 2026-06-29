# Diseño Visual de la API — CogniFit Backend (Entregable #2)

Diagramas de la implementación entregada del backend (FastAPI, arquitectura
hexagonal / por capas). Render con Mermaid.

## 1. Diagrama de componentes (contenedores y capas)

```mermaid
flowchart TB
    subgraph Cliente
        FL[App Flutter / Scalar]
    end

    subgraph API["API FastAPI (servicio api)"]
        direction TB
        subgraph Capa_API["Capa API (api/v1)"]
            RT[Routers: auth, students, screening,\nintervention, tracking, reports, admin, security, health]
            DEP[Dependencies / DI:\nget_db, get_current_user, require_roles,\nget_*_service, get_*_client]
            MW[Middleware: auth, rate-limit,\nsecurity headers, logging]
        end
        subgraph App["Capa Aplicación"]
            UC[Use Cases / Commands:\nSubmitAnswers, GetResult, GenerateReport...]
            SVC[Services: ScreeningService,\nRiskCalculator, SpacyNlpService]
        end
        subgraph Dom["Dominio"]
            PORTS[Ports / interfaces]
            ENT[Entities + Value Objects]
        end
        subgraph Infra["Infraestructura"]
            REPO[Repositorios PG\n+ Unit of Work]
            PLN[Clientes PLN\nDiagnosis/Recommendation]
            SEC[Seguridad:\nJWT, Argon2, Pipeline cifrado, Audit]
            CACHE[Redis cache]
        end
    end

    subgraph Externos
        DBN[(PostgreSQL / Neon)]
        DS[Diagnosis Service :8001]
        RS[Recommendation Service :8002]
        RD[(Redis)]
    end

    FL -->|HTTPS JWT| RT
    RT --> DEP --> UC --> SVC
    UC --> REPO
    SVC --> PLN
    REPO --> PORTS
    REPO --> DBN
    PLN --> DS
    PLN --> RS
    SEC -. cifra/descifra .-> REPO
    CACHE --> RD
```

## 2. Diagrama de clases — slice de Screening/Diagnóstico

```mermaid
classDiagram
    class ScreeningRouter {
        +submit_responses()
        +session_items()
        +diagnose_session()
    }
    class SubmitAnswersUseCase { +execute(session_id, responses) }
    class GetResultUseCase { +diagnose_session(session_id) }
    class PgSessionRepository {
        +get_session_items()
        +get_session_responses()
        +save_response()
    }
    class PgResultRepository {
        +save_diagnosis()
        +save_student_path()
        +get_latest_risk()
    }
    class SpacyNlpService { +analyze_response() +build_feature_vector() }
    class RiskCalculator { +classify() }
    class DiagnosisServiceClient { +diagnose() }
    class RecommendationServiceClient { +recommend() +next_exercise() }

    ScreeningRouter --> SubmitAnswersUseCase
    ScreeningRouter --> GetResultUseCase
    SubmitAnswersUseCase --> PgSessionRepository
    SubmitAnswersUseCase --> SpacyNlpService
    GetResultUseCase --> PgSessionRepository
    GetResultUseCase --> PgResultRepository
    GetResultUseCase --> DiagnosisServiceClient
    GetResultUseCase --> RecommendationServiceClient
    GetResultUseCase --> RiskCalculator
```

## 3. Diagrama de clases — Inyección de dependencias y seguridad

```mermaid
classDiagram
    class FastAPI_Depends
    class get_db { <<provider>> AsyncSession + UoW }
    class get_current_user { <<provider>> valida JWT + RLS }
    class require_roles { <<factory>> RBAC }
    class get_diagnosis_client { <<lru_cache singleton>> }
    class get_recommendation_client { <<lru_cache singleton>> }
    class PersistenceInterceptor { +prepare_for_write() +materialize_from_read() }

    FastAPI_Depends --> get_db
    FastAPI_Depends --> get_current_user
    get_current_user --> get_db
    require_roles --> get_current_user
    PersistenceInterceptor ..> get_db : usado por repos
```

## 4. Despliegue (Railway, 1 proyecto)

```mermaid
flowchart LR
    U[Cliente] -->|HTTPS| API[api FastAPI :public]
    API -->|railway.internal:8001| DS[diagnosis]
    API -->|railway.internal:8002| RS[recommendation]
    API --> RD[(Redis)]
    API -->|SSL| NEON[(Neon PostgreSQL)]
```

> Detalle de cada componente y sus patrones en
> [DOC_DISENO_BACKEND.md](DOC_DISENO_BACKEND.md). El módulo de cifrado tiene su
> propio diagrama de clases en [CIFRADO_DATOS_SENSIBLES.md](CIFRADO_DATOS_SENSIBLES.md).
