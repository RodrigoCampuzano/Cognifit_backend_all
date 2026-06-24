from __future__ import annotations


class ConsentPolicy:
    current_version = "1.0"

    def requires_guardian_consent(self, birth_year: int | None) -> bool:
        return birth_year is not None and birth_year >= 2008
