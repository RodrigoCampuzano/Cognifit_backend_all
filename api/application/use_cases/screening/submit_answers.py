from __future__ import annotations

from uuid import UUID

from infrastructure.database.repositories.pg_session_repository import PgSessionRepository
from infrastructure.nlp.spacy_nlp_service import SpacyNlpService


class SubmitAnswersUseCase:
    def __init__(self, repository: PgSessionRepository, nlp: SpacyNlpService) -> None:
        self.repository = repository
        self.nlp = nlp

    async def execute(self, *, session_id: UUID, responses: list[dict]) -> list[dict]:
        context = await self.repository.get_session_context(session_id)
        if not context:
            raise ValueError("Session not found")
        saved = []
        for response in responses:
            item = await self.repository.get_item_expected(response["item_id"])
            expected = item["expected_response"] or item["stimulus_text"]
            analysis = self.nlp.analyze_response(
                expected,
                response.get("raw_response"),
                item.get("item_kind"),
                response.get("response_time_ms"),
            )
            saved.append(
                await self.repository.save_response(
                    session_id=session_id,
                    assignment_id=context["assignment_id"],
                    module_code=context["module_code"],
                    item_id=response["item_id"],
                    raw_response=response.get("raw_response"),
                    response_time_ms=response.get("response_time_ms"),
                    capture_modality=response.get("capture_modality"),
                    response_audio_url=response.get("response_audio_url"),
                    stt_confidence=response.get("stt_confidence"),
                    analysis=analysis,
                )
            )
        return saved
