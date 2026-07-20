from __future__ import annotations

import json
from pathlib import Path
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from config.settings import get_settings


SEED_DIR = Path(__file__).resolve().parents[1] / "seeds"


class PgSessionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.settings = get_settings()

    async def get_battery_catalog(self) -> list[dict]:
        try:
            result = await self.session.execute(text("SELECT * FROM assessment.v_battery_catalog ORDER BY module_number"))
            return [dict(row) for row in result.mappings().all()]
        except Exception:
            data = json.loads((SEED_DIR / "cognifit_app_content_pack.json").read_text(encoding="utf-8"))
            return data["modules"]

    async def get_teacher_items(self) -> list[dict]:
        try:
            result = await self.session.execute(
                text(
                    '''
                    SELECT item_code, prompt, weight::float AS weight, tags, source_note, scale
                    FROM assessment.teacher_screening_items
                    WHERE is_active = TRUE
                    ORDER BY item_code
                    '''
                )
            )
            rows = [dict(row) for row in result.mappings().all()]
            if rows:
                return rows
        except Exception:
            pass
        data = json.loads((SEED_DIR / "cognifit_app_content_pack.json").read_text(encoding="utf-8"))
        return [
            {
                "item_code": item["id"],
                "prompt": item["prompt"],
                "weight": item["weight"],
                "tags": item["tags"],
                "source_note": item["source"],
                "scale": data["teacher_screening"]["scale"],
            }
            for item in data["teacher_screening"]["questions"]
        ]

    async def save_teacher_result(self, *, student_id: UUID, teacher_id: UUID, score_payload: dict, answers: list[dict]) -> dict:
        result = await self.session.execute(
            text(
                '''
                INSERT INTO assessment.teacher_screening_results
                    (student_id, teacher_id, score, battery_mode, answers, risk_flags)
                VALUES
                    (:student_id, :teacher_id, :score, :battery_mode, CAST(:answers AS jsonb), CAST(:risk_flags AS jsonb))
                RETURNING id, student_id, teacher_id, score::float AS score, battery_mode, answers, risk_flags, completed_at
                '''
            ),
            {
                "student_id": str(student_id),
                "teacher_id": str(teacher_id),
                "score": score_payload["score"],
                "battery_mode": score_payload["battery_mode"],
                "answers": json.dumps(answers),
                "risk_flags": json.dumps(score_payload["risk_flags"]),
            },
        )
        saved = dict(result.mappings().one())
        saved["enabled_module_codes"] = score_payload["enabled_module_codes"]
        return saved

    async def create_assignments(self, *, student_id: UUID, module_codes: list[str], teacher_id: UUID, teacher_score: float | None, risk_flags: list[dict]) -> list[dict]:
        created: list[dict] = []
        for module_code in module_codes:
            result = await self.session.execute(
                text(
                    '''
                    INSERT INTO assessment.test_assignments
                        (student_id, test_id, assigned_by, status, teacher_screening_score, teacher_screening_flags)
                    SELECT :student_id, t.id, :teacher_id, 'PENDING', :teacher_score, CAST(:risk_flags AS jsonb)
                    FROM assessment.tests t
                    JOIN assessment.battery_modules bm ON bm.id = t.module_id
                    WHERE bm.module_code = :module_code
                      AND NOT EXISTS (
                        SELECT 1 FROM assessment.test_assignments ex
                        WHERE ex.student_id = :student_id
                          AND ex.test_id = t.id
                          AND ex.status IN ('PENDING', 'IN_PROGRESS')
                      )
                    ORDER BY t.created_at DESC
                    LIMIT 1
                    RETURNING id, student_id, test_id, status, assigned_at
                    '''
                ),
                {
                    "student_id": str(student_id),
                    "teacher_id": str(teacher_id),
                    "teacher_score": teacher_score,
                    "risk_flags": json.dumps(risk_flags),
                    "module_code": module_code,
                },
            )
            row = result.mappings().first()
            if row:
                item = dict(row)
                item["module_code"] = module_code
                created.append(item)
        return created

    async def get_teacher_assignments(
        self, *, teacher_id: UUID, is_admin: bool, institution_id: UUID, statuses: list[str], limit: int = 20
    ) -> list[dict]:
        """Asignaciones de los alumnos del docente filtradas por status,
        siempre acotadas a la institución del solicitante."""
        result = await self.session.execute(
            text(
                """
                SELECT
                    ta.id, ta.status, ta.assigned_at,
                    s.id           AS student_id,
                    pgp_sym_decrypt(s.full_name, :key)::text AS student_name,
                    bm.module_code,
                    bm.title       AS module_name,
                    MAX(ts.completed_at) AS completed_at
                FROM assessment.test_assignments ta
                JOIN academic.students    s  ON s.id  = ta.student_id
                JOIN academic.groups      g  ON g.id  = s.group_id
                JOIN assessment.tests     t  ON t.id  = ta.test_id
                JOIN assessment.battery_modules bm ON bm.id = t.module_id
                LEFT JOIN assessment.test_sessions ts
                       ON ts.assignment_id = ta.id AND ts.session_status = 'COMPLETED'
                WHERE g.school_id = :institution_id
                  AND (:is_admin OR ta.assigned_by = :teacher_id)
                  AND ta.status = ANY(:statuses)
                GROUP BY ta.id, ta.status, ta.assigned_at, s.id, s.full_name, bm.module_code, bm.title
                ORDER BY ta.assigned_at DESC
                LIMIT :limit
                """
            ),
            {
                "teacher_id": str(teacher_id),
                "is_admin": is_admin,
                "institution_id": str(institution_id),
                "statuses": statuses,
                "limit": limit,
                "key": self.settings.db_encryption_key,
            },
        )
        rows = result.mappings().all()
        return [
            {
                "id": str(row["id"]),
                "status": row["status"],
                "assigned_at": str(row["assigned_at"]),
                "student_id": str(row["student_id"]),
                "student_name": row["student_name"],
                "module_code": row["module_code"],
                "module_name": row["module_name"],
                "completed_at": str(row["completed_at"]) if row["completed_at"] else None,
            }
            for row in rows
        ]

    async def start_session(self, *, assignment_id: UUID, module_code: str, device_id: str | None, app_version: str | None, raw_client_payload: dict | None = None) -> dict:
        result = await self.session.execute(
            text(
                '''
                INSERT INTO assessment.test_sessions
                    (assignment_id, module_id, device_id, app_version, raw_client_payload)
                SELECT :assignment_id, bm.id, :device_id, :app_version, CAST(:payload AS jsonb)
                FROM assessment.battery_modules bm
                WHERE bm.module_code = :module_code
                ON CONFLICT (assignment_id, module_id)
                DO UPDATE SET session_status='IN_PROGRESS', device_id=EXCLUDED.device_id, app_version=EXCLUDED.app_version
                RETURNING id, assignment_id, module_id, session_status, started_at, device_id, app_version
                '''
            ),
            {
                "assignment_id": str(assignment_id),
                "module_code": module_code,
                "device_id": device_id,
                "app_version": app_version,
                "payload": json.dumps(raw_client_payload or {}),
            },
        )
        return dict(result.mappings().one())

    async def get_calendario_tamizaje(
        self,
        *,
        institution_id: UUID | str,
        teacher_id: UUID | str,
        is_privileged: bool,
        solo_vencidos: bool = True,
    ) -> list[dict]:
        """Alumnos a los que les toca una aplicación, con el nombre descifrado.

        Acotado a la institución del solicitante y, si no es privilegiado,
        también a sus grupos: sin eso un docente vería el calendario de
        alumnos de otras escuelas.
        """
        clausulas = ["g.school_id = :institution_id"]
        if not is_privileged:
            clausulas.append("g.teacher_id = :teacher_id")
        if solo_vencidos:
            clausulas.append("cal.que_toca <> \'AL_DIA\'")

        result = await self.session.execute(
            text(
                f"""
                SELECT cal.student_id,
                       pgp_sym_decrypt(s.full_name, :key)::text AS student_name,
                       g.grade,
                       cal.que_toca,
                       cal.ult_monitoreo,
                       cal.ult_bateria,
                       cal.sin_linea_base
                FROM assessment.v_calendario_tamizaje cal
                JOIN academic.students s ON s.id = cal.student_id
                JOIN academic.groups g ON g.id = s.group_id
                WHERE {" AND ".join(clausulas)}
                ORDER BY
                    -- Primero quien nunca fue evaluado: sin línea base no hay
                    -- con qué comparar nada de lo que venga después.
                    CASE cal.que_toca
                        WHEN \'BATERIA_INICIAL\' THEN 0
                        WHEN \'BATERIA\'         THEN 1
                        WHEN \'MONITOREO\'       THEN 2
                        ELSE 3
                    END,
                    cal.ult_cualquiera ASC NULLS FIRST
                """
            ),
            {
                "institution_id": str(institution_id),
                "teacher_id": str(teacher_id),
                "key": self.settings.db_encryption_key,
            },
        )
        return [dict(row) for row in result.mappings().all()]

    async def get_session_items(self, session_id: UUID) -> list[dict]:
        """Ítems que la app debe presentar en una sesión.

        Tres reglas conviven acá, y ninguna es opcional:

        1. **Muestreo estratificado por dificultad.** Cuando el test declara
           `items_per_session`, no se entrega el banco entero sino una muestra
           que conserva la proporción de cada nivel. Es lo único que evita que
           el alumno memorice las *respuestas* al repetir el tamizaje: barajar
           el orden solo evita que memorice la *secuencia*, porque recordar
           "a esa palabra respondí X" funciona igual en cualquier posición.

           Conservar la proporción es lo que mantiene comparables dos
           aplicaciones. Con muestreo aleatorio simple, una mejora entre marzo
           y junio podría ser solo que la segunda muestra salió más fácil.

        2. **Progresión de fácil a difícil.** El banco está construido así, y
           saltearla cambia lo que se mide: un alumno con dificultad que se
           topa con lo más difícil al sexto ítem se frustra y abandona.

        3. **Orden distinto en cada sesión**, determinista sobre el id de la
           sesión: si la app vuelve a pedir los ítems, recibe el mismo orden.

        La denominación rápida queda fuera de 1 y 3 a propósito: su medida es
        el tiempo total de nombrar una lámina fija, así que cambiar los ítems o
        su orden invalida la comparación entre alumnos y entre aplicaciones.
        """
        result = await self.session.execute(
            text(
                '''
                WITH items AS (
                    SELECT ti.id, ti.item_order, ti.item_code, ti.stimulus_text,
                           ti.stimulus_audio_url, ti.expected_response,
                           COALESCE(ti.item_kind, t.test_type::text) AS item_kind,
                           ti.difficulty, ti.tags, ti.is_practice,
                           bm.module_code, bm.title AS module_title, bm.input_modes,
                           t.items_per_session,
                           (t.test_type::text = 'RAPID_NAMING') AS orden_fijo,
                           -- Posición dentro de su nivel de dificultad, con el
                           -- barajado propio de la sesión.
                           ROW_NUMBER() OVER (
                               PARTITION BY ti.difficulty
                               ORDER BY MD5(ti.id::text || :session_id)
                           ) AS pos_en_nivel,
                           COUNT(*) OVER (PARTITION BY ti.difficulty) AS total_nivel,
                           COUNT(*) OVER () AS total_banco
                    FROM assessment.test_sessions ts
                    JOIN assessment.test_items ti ON ti.module_id = ts.module_id
                    JOIN assessment.tests t ON t.id = ti.test_id
                    JOIN assessment.battery_modules bm ON bm.id = ts.module_id
                    WHERE ts.id = :session_id
                )
                SELECT id AS item_id, item_order, item_code, stimulus_text,
                       stimulus_audio_url, expected_response, item_kind,
                       difficulty, tags, is_practice,
                       module_code, module_title, input_modes
                FROM items
                WHERE is_practice          -- la práctica se presenta siempre
                   OR items_per_session IS NULL   -- sin muestreo: banco entero
                   OR orden_fijo                  -- denominación rápida: lámina completa
                   -- Cuota de cada nivel, proporcional a su peso en el banco.
                   -- CEIL evita que un nivel poco numeroso quede sin
                   -- representación por redondeo.
                   OR pos_en_nivel <= CEIL(
                          items_per_session::numeric * total_nivel / total_banco
                      )
                ORDER BY is_practice DESC,
                         CASE WHEN orden_fijo THEN item_order ELSE difficulty END ASC,
                         CASE WHEN orden_fijo THEN '' ELSE MD5(id::text || :session_id) END ASC
                '''
            ),
            {"session_id": str(session_id)},
        )
        return [dict(row) for row in result.mappings().all()]

    async def get_session_context(self, session_id: UUID) -> dict | None:
        result = await self.session.execute(
            text(
                '''
                SELECT
                    ts.id AS session_id, ts.assignment_id, ta.student_id, ta.teacher_screening_score::float AS teacher_score,
                    bm.module_code, bm.test_type::text AS module_test_type,
                    COALESCE(s.birth_year, 2017) AS birth_year,
                    COALESCE(g.grade, 3) AS grade
                FROM assessment.test_sessions ts
                JOIN assessment.test_assignments ta ON ta.id = ts.assignment_id
                JOIN assessment.battery_modules bm ON bm.id = ts.module_id
                JOIN academic.students s ON s.id = ta.student_id
                JOIN academic.groups g ON g.id = s.group_id
                WHERE ts.id=:session_id
                '''
            ),
            {"session_id": str(session_id)},
        )
        row = result.mappings().first()
        return dict(row) if row else None

    async def get_session_responses(self, session_id: UUID) -> list[dict]:
        result = await self.session.execute(
            text(
                '''
                SELECT
                    sr.id, sr.item_id, sr.raw_response, sr.normalized_response, sr.response_time_ms,
                    sr.expected_text, sr.error_breakdown, sr.is_correct, sr.edit_distance,
                    sr.phonetic_similarity, sr.ngram_overlap, sr.lexicalization_flag,
                    COALESCE(ti.item_kind, t.test_type::text) AS item_kind
                FROM assessment.student_responses sr
                JOIN assessment.test_items ti ON ti.id = sr.item_id
                JOIN assessment.tests t ON t.id = ti.test_id
                WHERE sr.session_id=:session_id
                ORDER BY sr.responded_at ASC
                '''
            ),
            {"session_id": str(session_id)},
        )
        return [dict(row) for row in result.mappings().all()]

    async def get_assignment_responses(self, assignment_id: UUID) -> list[dict]:
        """Todas las respuestas crudas del assignment (todas sus sesiones/módulos),
        listas para construir el request /diagnose del Diagnosis Service."""
        result = await self.session.execute(
            text(
                '''
                SELECT
                    sr.id, sr.item_id, sr.raw_response, sr.normalized_response, sr.expected_text,
                    sr.response_time_ms, sr.capture_modality, sr.is_correct, sr.error_breakdown,
                    sr.timing_detail,
                    ti.difficulty,
                    bm.module_code
                FROM assessment.student_responses sr
                JOIN assessment.battery_modules bm ON bm.id = sr.module_id
                LEFT JOIN assessment.test_items ti ON ti.id = sr.item_id
                WHERE sr.assignment_id = :assignment_id
                ORDER BY sr.responded_at ASC
                '''
            ),
            {"assignment_id": str(assignment_id)},
        )
        return [dict(row) for row in result.mappings().all()]

    async def complete_assignment_sessions(self, assignment_id: UUID) -> None:
        await self.session.execute(
            text(
                "UPDATE assessment.test_sessions SET session_status='COMPLETED', completed_at=now() "
                "WHERE assignment_id=:assignment_id AND session_status <> 'COMPLETED'"
            ),
            {"assignment_id": str(assignment_id)},
        )
        # La asignación en sí también se cierra. Antes solo se completaban las
        # sesiones y `test_assignments.status` se quedaba en 'PENDING' de por
        # vida (no había un solo UPDATE sobre esa columna en todo el backend),
        # así que la lista del docente mostraba como pendientes alumnos que ya
        # habían terminado la batería y hasta tenían diagnóstico.
        await self.session.execute(
            text(
                "UPDATE assessment.test_assignments SET status='COMPLETED' "
                "WHERE id=:assignment_id AND status <> 'COMPLETED'"
            ),
            {"assignment_id": str(assignment_id)},
        )

    async def get_item_expected(self, item_id: UUID) -> dict:
        result = await self.session.execute(
            text(
                '''
                SELECT ti.expected_response, ti.stimulus_text, COALESCE(ti.item_kind, t.test_type::text) AS item_kind
                FROM assessment.test_items ti
                JOIN assessment.tests t ON t.id = ti.test_id
                WHERE ti.id=:item_id
                '''
            ),
            {"item_id": str(item_id)},
        )
        row = result.mappings().one()
        return dict(row)

    async def save_response(self, *, session_id: UUID, assignment_id: UUID, module_code: str, item_id: UUID, raw_response: str | None, response_time_ms: int | None, capture_modality: str | None, response_audio_url: str | None, stt_confidence: float | None, analysis: dict, timing_detail: dict | None = None) -> dict:
        result = await self.session.execute(
            text(
                '''
                INSERT INTO assessment.student_responses
                    (assignment_id, session_id, module_id, item_id, raw_response, normalized_response, expected_text,
                     response_time_ms, capture_modality, response_audio_url, stt_confidence, is_correct, error_tags,
                     edit_distance, phonetic_similarity, ngram_overlap, lexicalization_flag, error_breakdown,
                     timing_detail)
                SELECT
                    :assignment_id, :session_id, bm.id, :item_id, :raw_response, :normalized_response, :expected_text,
                    :response_time_ms, :capture_modality, :response_audio_url, :stt_confidence, :is_correct, :error_tags,
                    :edit_distance, :phonetic_similarity, :ngram_overlap, :lexicalization_flag, CAST(:error_breakdown AS jsonb),
                    CAST(:timing_detail AS jsonb)
                FROM assessment.battery_modules bm
                WHERE bm.module_code=:module_code
                ON CONFLICT (session_id, item_id) WHERE session_id IS NOT NULL
                DO UPDATE SET
                    raw_response        = EXCLUDED.raw_response,
                    normalized_response = EXCLUDED.normalized_response,
                    expected_text       = EXCLUDED.expected_text,
                    response_time_ms    = EXCLUDED.response_time_ms,
                    capture_modality    = EXCLUDED.capture_modality,
                    response_audio_url  = EXCLUDED.response_audio_url,
                    stt_confidence      = EXCLUDED.stt_confidence,
                    is_correct          = EXCLUDED.is_correct,
                    error_tags          = EXCLUDED.error_tags,
                    edit_distance       = EXCLUDED.edit_distance,
                    phonetic_similarity = EXCLUDED.phonetic_similarity,
                    ngram_overlap       = EXCLUDED.ngram_overlap,
                    lexicalization_flag = EXCLUDED.lexicalization_flag,
                    error_breakdown     = EXCLUDED.error_breakdown,
                    timing_detail       = EXCLUDED.timing_detail
                RETURNING id, item_id, raw_response, normalized_response, is_correct, error_tags, edit_distance, phonetic_similarity, ngram_overlap, lexicalization_flag, error_breakdown
                '''
            ),
            {
                "assignment_id": str(assignment_id),
                "session_id": str(session_id),
                "module_code": module_code,
                "item_id": str(item_id),
                "raw_response": raw_response,
                "normalized_response": analysis["normalized_response"],
                "expected_text": analysis["expected_text"],
                "response_time_ms": response_time_ms,
                "capture_modality": capture_modality,
                "response_audio_url": response_audio_url,
                "stt_confidence": stt_confidence,
                "timing_detail": json.dumps(timing_detail or {}),
                "is_correct": analysis["is_correct"],
                "error_tags": analysis["error_tags"],
                "edit_distance": analysis["edit_distance"],
                "phonetic_similarity": analysis["phonetic_similarity"],
                "ngram_overlap": analysis["ngram_overlap"],
                "lexicalization_flag": analysis["lexicalization_flag"],
                "error_breakdown": json.dumps(analysis["error_breakdown"]),
            },
        )
        return dict(result.mappings().one())

    async def complete_session(self, session_id: UUID) -> None:
        await self.session.execute(
            text("UPDATE assessment.test_sessions SET session_status='COMPLETED', completed_at=now() WHERE id=:session_id"),
            {"session_id": str(session_id)},
        )
