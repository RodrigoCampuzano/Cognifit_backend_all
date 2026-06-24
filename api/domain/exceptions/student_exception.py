from domain.exceptions.domain_exception import DomainException


class StudentNotFound(DomainException):
    status_code = 404
    code = "STUDENT_NOT_FOUND"
