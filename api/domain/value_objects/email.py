from __future__ import annotations

from dataclasses import dataclass
from email.utils import parseaddr


@dataclass(frozen=True, slots=True)
class Email:
    value: str

    def __post_init__(self) -> None:
        parsed = parseaddr(self.value)[1]
        if "@" not in parsed or parsed != self.value:
            raise ValueError("Invalid email")
