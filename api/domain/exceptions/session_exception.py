from domain.exceptions.domain_exception import DomainException


class SessionNotFound(DomainException):
    status_code = 404
    code = "SESSION_NOT_FOUND"
