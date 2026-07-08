from __future__ import annotations

import json
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies.auth import CurrentUser, require_roles
from api.dependencies.database import get_db
from api.dependencies.services import get_diagnosis_client, get_nlp_service, get_recommendation_client, get_risk_calculator, get_screening_service
from config.settings import get_settings
from infrastructure.cache.cache_decorator import cached_endpoint
from infrastructure.pln.diagnosis_client import DiagnosisServiceClient
from infrastructure.pln.recommendation_client import RecommendationServiceClient
from api.v1.screening.schemas import CreateAssignmentsRequest, LabelDiagnosisRequest, StartSessionRequest, SubmitResponsesRequest, TeacherScreeningRequest, TeacherScreeningResponse
from application.services.risk_calculator import RiskCalculator
from application.services.screening_service import ScreeningService
from application.use_cases.screening.get_result import GetResultUseCase
from application.use_cases.screening.submit_answers import SubmitAnswersUseCase
from infrastructure.database.repositories.pg_result_repository import PgResultRepository
from infrastructure.database.repositories.pg_session_repository import PgSessionRepository
from infrastructure.nlp.spacy_nlp_service import SpacyNlpService
from security.audit.audit_decorator import audited
from security.audit.audit_events import AuditEvent

router = APIRouter(prefix="/screening", tags=["screening"])
SEED_DIR = Path(__file__).resolve().parents[3] / "infrastructure" / "database" / "seeds"


@router.get("/catalog")
@cached_endpoint("screening_catalog")
async def battery_catalog(db: AsyncSession = Depends(get_db), _: CurrentUser = Depends(require_roles("ADMIN", "SPECIALIST", "TEACHER"))):
    return await PgSessionRepository(db).get_battery_catalog()


@router.get("/teacher-items")
@cached_endpoint("screening_teacher_items")
async def teacher_items(db: AsyncSession = Depends(get_db), _: CurrentUser = Depends(require_roles("ADMIN", "SPECIALIST", "TEACHER"))):
    return await PgSessionRepository(db).get_teacher_items()


@router.get("/item-bank/tede")
@cached_endpoint("screening_tede_item_bank")
async def tede_item_bank(_: CurrentUser = Depends(require_roles("ADMIN", "SPECIALIST", "TEACHER"))):
    return json.loads((SEED_DIR / "tede_item_bank.json").read_text(encoding="utf-8"))


@router.get("/assignments")
async def list_teacher_assignments(
    status: str = "PENDING,IN_PROGRESS",
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_roles("ADMIN", "SPECIALIST", "TEACHER")),
):
    """Asignaciones del docente filtradas por status (comma-separated).
    Ej: ?status=PENDING,IN_PROGRESS  o  ?status=COMPLETED"""
    statuses = [s.strip() for s in status.split(",") if s.strip()]
    return await PgSessionRepository(db).get_teacher_assignments(
        teacher_id=user.id,
        is_admin=user.role == "ADMIN",
        statuses=statuses,
        limit=min(limit, 50),
    )


@router.get("/diagnoses/pending-review")
async def pending_diagnoses_review(
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(require_roles("ADMIN", "SPECIALIST")),
):
    """Diagnósticos sin etiqueta de especialista, listos para revisión clínica.
    Devuelve máx. 50 registros ordenados por más recientes."""
    return await PgResultRepository(db).get_pending_diagnoses(limit=min(limit, 100))


@router.post("/diagnoses/{diagnosis_id}/label", status_code=201)
@audited(
    AuditEvent.DIAGNOSIS_LABELED,
    target_table="diagnosis.training_labels",
    metadata_fn=lambda result, kw: {
        "diagnosis_id": str(kw["diagnosis_id"]),
        "confirmed_subtype": kw["payload"].confirmed_subtype,
        "confirmed_risk_level": kw["payload"].confirmed_risk_level,
    },
)
async def label_diagnosis(
    diagnosis_id: UUID,
    payload: LabelDiagnosisRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_roles("ADMIN", "SPECIALIST")),
):
    """El especialista confirma o corrige el diagnóstico automático.
    Registra en diagnosis.training_labels para reentrenamiento del modelo ML."""
    try:
        return await PgResultRepository(db).label_diagnosis(
            diagnosis_id=diagnosis_id,
            specialist_id=user.id,
            confirmed_subtype=payload.confirmed_subtype,
            confirmed_severity=payload.confirmed_severity,
            confirmed_risk_level=payload.confirmed_risk_level,
            notes=payload.notes,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/teacher-results", response_model=TeacherScreeningResponse, status_code=201)
@audited(AuditEvent.TEACHER_SCREENING_COMPLETED, target_table="assessment.teacher_screening_results")
async def submit_teacher_screening(
    payload: TeacherScreeningRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_roles("ADMIN", "SPECIALIST", "TEACHER")),
    service: ScreeningService = Depends(get_screening_service),
):
    repo = PgSessionRepository(db)
    items = await repo.get_teacher_items()
    score = service.calculate_teacher_score(items, [item.model_dump() for item in payload.answers])
    return await repo.save_teacher_result(student_id=payload.student_id, teacher_id=user.id, score_payload=score, answers=[item.model_dump() for item in payload.answers])


@router.post("/assignments", status_code=201)
async def create_assignments(
    payload: CreateAssignmentsRequest,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_roles("ADMIN", "SPECIALIST", "TEACHER")),
    service: ScreeningService = Depends(get_screening_service),
):
    module_codes = service.enabled_modules(payload.teacher_score)
    assignments = await PgSessionRepository(db).create_assignments(
        student_id=payload.student_id,
        module_codes=module_codes,
        teacher_id=user.id,
        teacher_score=payload.teacher_score,
        risk_flags=payload.risk_flags,
    )
    return {"enabled_module_codes": module_codes, "assignments": assignments}


@router.post("/sessions", status_code=201)
async def start_session(
    payload: StartSessionRequest,
    db: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(require_roles("ADMIN", "SPECIALIST", "TEACHER", "STUDENT")),
):
    return await PgSessionRepository(db).start_session(
        assignment_id=payload.assignment_id,
        module_code=payload.module_code,
        device_id=payload.device_id,
        app_version=payload.app_version,
        raw_client_payload=payload.raw_client_payload,
    )


@router.get("/sessions/{session_id}/items")
async def session_items(
    session_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(require_roles("ADMIN", "SPECIALIST", "TEACHER", "STUDENT")),
):
    """Ítems a presentar en la app para esta sesión (con su item_id para enviar respuestas)."""
    repo = PgSessionRepository(db)
    if not await repo.get_session_context(session_id):
        raise HTTPException(status_code=404, detail="Session not found")
    items = await repo.get_session_items(session_id)
    return {"session_id": session_id, "total_items": len(items), "items": items}


@router.post("/sessions/{session_id}/responses", status_code=201)
@audited(
    AuditEvent.RESPONSE_SUBMITTED,
    target_table="assessment.test_sessions",
    target_id_arg="session_id",
    metadata_fn=lambda result, kw: {"response_count": len(result["responses"])},
)
async def submit_responses(
    session_id: UUID,
    payload: SubmitResponsesRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_roles("ADMIN", "SPECIALIST", "TEACHER", "STUDENT")),
    nlp: SpacyNlpService = Depends(get_nlp_service),
):
    use_case = SubmitAnswersUseCase(PgSessionRepository(db), nlp)
    try:
        saved = await use_case.execute(session_id=session_id, responses=[item.model_dump() for item in payload.responses])
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"session_id": session_id, "responses": saved}


@router.post("/sessions/{session_id}/diagnose")
@audited(AuditEvent.DIAGNOSIS_CREATED, target_table="diagnosis.diagnoses")
async def diagnose_session(
    session_id: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_roles("ADMIN", "SPECIALIST", "TEACHER")),
    nlp: SpacyNlpService = Depends(get_nlp_service),
    risk: RiskCalculator = Depends(get_risk_calculator),
    diagnosis_client: DiagnosisServiceClient = Depends(get_diagnosis_client),
    recommendation_client: RecommendationServiceClient = Depends(get_recommendation_client),
):
    settings = get_settings()
    use_case = GetResultUseCase(
        PgSessionRepository(db),
        PgResultRepository(db),
        nlp,
        risk,
        diagnosis_client=diagnosis_client,
        recommendation_client=recommendation_client,
        fallback_enabled=settings.pln_fallback_enabled,
    )
    try:
        return await use_case.diagnose_session(session_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/students/{student_id}/latest-risk")
async def latest_student_risk(
    student_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(require_roles("ADMIN", "SPECIALIST", "TEACHER", "PARENT")),
):
    result = await PgResultRepository(db).get_latest_risk(student_id)
    if not result:
        raise HTTPException(status_code=404, detail="No diagnosis found")
    return result


@router.get("/students/{student_id}/assignments")
async def get_student_assignments(
    student_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(require_roles("ADMIN", "SPECIALIST", "TEACHER")),
):
    """Asignaciones PENDING o IN_PROGRESS del alumno (módulos aún no completados)."""
    from sqlalchemy import text
    result = await db.execute(
        text("""
            SELECT ta.id, bm.module_code, bm.title AS module_name,
                   ta.status, ta.assigned_at
            FROM assessment.test_assignments ta
            JOIN assessment.tests t ON t.id = ta.test_id
            JOIN assessment.battery_modules bm ON bm.id = t.module_id
            WHERE ta.student_id = :student_id
              AND ta.status IN ('PENDING', 'IN_PROGRESS')
            ORDER BY bm.module_number ASC
        """),
        {"student_id": str(student_id)},
    )
    rows = result.mappings().all()
    return [
        {
            "id": str(row["id"]),
            "module_code": row["module_code"],
            "module_name": row["module_name"],
            "status": row["status"],
            "assigned_at": str(row["assigned_at"]),
        }
        for row in rows
    ]
