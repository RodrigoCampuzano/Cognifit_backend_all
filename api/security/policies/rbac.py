from __future__ import annotations

from enum import StrEnum


class Role(StrEnum):
    ADMIN = "ADMIN"
    SPECIALIST = "SPECIALIST"
    TEACHER = "TEACHER"
    PARENT = "PARENT"
    STUDENT = "STUDENT"


ROLE_HIERARCHY = {
    Role.ADMIN: {Role.ADMIN, Role.SPECIALIST, Role.TEACHER, Role.PARENT, Role.STUDENT},
    Role.SPECIALIST: {Role.SPECIALIST, Role.TEACHER, Role.PARENT, Role.STUDENT},
    Role.TEACHER: {Role.TEACHER, Role.STUDENT},
    Role.PARENT: {Role.PARENT, Role.STUDENT},
    Role.STUDENT: {Role.STUDENT},
}


def has_role(role: str, allowed: set[str]) -> bool:
    try:
        current = Role(role)
    except ValueError:
        return False
    return any(Role(item) in ROLE_HIERARCHY[current] for item in allowed)
