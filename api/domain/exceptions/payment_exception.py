from domain.exceptions.domain_exception import DomainException


class PlanNotFound(DomainException):
    status_code = 404
    code = "PLAN_NOT_FOUND"


class PaymentNotFound(DomainException):
    status_code = 404
    code = "PAYMENT_NOT_FOUND"


class ConektaApiError(DomainException):
    status_code = 502
    code = "CONEKTA_API_ERROR"


class PaymentGatewayNotConfigured(DomainException):
    status_code = 503
    code = "PAYMENT_GATEWAY_NOT_CONFIGURED"


class InvalidWebhookSignature(DomainException):
    status_code = 401
    code = "INVALID_WEBHOOK_SIGNATURE"
