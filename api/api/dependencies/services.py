from __future__ import annotations

from functools import lru_cache

from application.services.risk_calculator import RiskCalculator
from application.services.screening_service import ScreeningService
from config.settings import get_settings
from infrastructure.conekta.conekta_payment_adapter import ConektaPaymentAdapter
from infrastructure.email.smtp_email_service import SmtpEmailService
from infrastructure.nlp.spacy_nlp_service import SpacyNlpService
from infrastructure.pln.diagnosis_client import DiagnosisServiceClient
from infrastructure.pln.health_registry import HealthRegistry
from infrastructure.pln.recommendation_client import RecommendationServiceClient


def get_screening_service() -> ScreeningService:
    return ScreeningService()


def get_nlp_service() -> SpacyNlpService:
    return SpacyNlpService()


def get_risk_calculator() -> RiskCalculator:
    return RiskCalculator()


@lru_cache
def get_diagnosis_client() -> DiagnosisServiceClient:
    settings = get_settings()
    return DiagnosisServiceClient(
        settings.diagnosis_service_url,
        timeout=settings.pln_timeout_seconds,
        retries=settings.pln_retries,
    )


@lru_cache
def get_recommendation_client() -> RecommendationServiceClient:
    settings = get_settings()
    return RecommendationServiceClient(
        settings.recommendation_service_url,
        timeout=settings.pln_timeout_seconds,
    )


@lru_cache
def get_health_registry() -> HealthRegistry:
    return HealthRegistry()


@lru_cache
def get_email_service() -> SmtpEmailService:
    return SmtpEmailService()


@lru_cache
def get_payment_gateway() -> ConektaPaymentAdapter:
    return ConektaPaymentAdapter()
