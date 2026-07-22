from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies.auth import CurrentUser, require_roles
from api.dependencies.database import get_db
from api.dependencies.services import get_payment_gateway
from api.v1.payments.schemas import (
    CardCheckoutRequest,
    CashCheckoutRequest,
    PaymentResponse,
    PlanResponse,
)
from application.use_cases.payments.create_card_payment import CreateCardPaymentUseCase
from application.use_cases.payments.create_cash_payment import CreateCashPaymentUseCase
from application.use_cases.payments.get_payment import GetPaymentUseCase
from application.use_cases.payments.list_payments import ListPaymentsUseCase
from application.use_cases.payments.list_plans import ListPlansUseCase
from domain.ports.payment_port import PaymentGatewayPort
from infrastructure.database.repositories.pg_payment_repository import PgPaymentRepository
from security.audit.audit_decorator import audited
from security.audit.audit_events import AuditEvent

router = APIRouter(prefix="/payments", tags=["payments"])


def _require_institution(user: CurrentUser) -> UUID:
    if user.institution_id is None:
        raise HTTPException(status_code=400, detail="Tu cuenta no está asociada a una institución")
    return user.institution_id


@router.get("/plans", response_model=list[PlanResponse])
async def list_plans(db: AsyncSession = Depends(get_db)):
    return await ListPlansUseCase(PgPaymentRepository(db)).execute()


@router.post("/checkout/card", response_model=PaymentResponse, status_code=201)
@audited(AuditEvent.PAYMENT_CHECKOUT_CARD, target_table="billing.payments")
async def checkout_with_card(
    payload: CardCheckoutRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_roles("ADMIN")),
    gateway: PaymentGatewayPort = Depends(get_payment_gateway),
):
    school_id = _require_institution(user)
    use_case = CreateCardPaymentUseCase(PgPaymentRepository(db), gateway)
    return await use_case.execute(
        school_id=school_id,
        plan_id=payload.plan_id,
        created_by_user_id=user.id,
        admin_email=user.email,
        # auth.users no guarda un nombre de pila; el correo es el único dato
        # legible que tenemos para el customer de Conekta.
        admin_name=user.email,
        token_id=payload.token_id,
    )


@router.post("/checkout/cash", response_model=PaymentResponse, status_code=201)
@audited(AuditEvent.PAYMENT_CHECKOUT_CASH, target_table="billing.payments")
async def checkout_with_cash(
    payload: CashCheckoutRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_roles("ADMIN")),
    gateway: PaymentGatewayPort = Depends(get_payment_gateway),
):
    school_id = _require_institution(user)
    use_case = CreateCashPaymentUseCase(PgPaymentRepository(db), gateway)
    return await use_case.execute(
        school_id=school_id,
        plan_id=payload.plan_id,
        created_by_user_id=user.id,
        admin_email=user.email,
        admin_name=user.email,
    )


@router.get("", response_model=list[PaymentResponse])
async def list_payments(
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_roles("ADMIN")),
):
    school_id = _require_institution(user)
    return await ListPaymentsUseCase(PgPaymentRepository(db)).execute(school_id=school_id)


@router.get("/{payment_id}", response_model=PaymentResponse)
async def get_payment(
    payment_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_roles("ADMIN")),
):
    school_id = _require_institution(user)
    return await GetPaymentUseCase(PgPaymentRepository(db)).execute(payment_id, school_id=school_id)
