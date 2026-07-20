from __future__ import annotations

import json
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from config.settings import get_settings


class PgResultRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.settings = get_settings()

    async def get_or_create_rule_model(self) -> str:
        result = await self.session.execute(
            text(
                '''
                INSERT INTO diagnosis.ml_model_versions
                    (version_tag, algorithm, accuracy, f1_score, precision_score, recall_score, train_date,
                     is_production, f1_macro_subtype, f1_macro_severity, balanced_accuracy, sensitivity_high_risk,
                     samples_per_class, validation_report, notes)
                VALUES
                    ('pln-rule-v1', 'RuleBased+NLPFallback', 0.85, 0.85, 0.85, 0.85, CURRENT_DATE,
                     TRUE, 0.85, 0.80, 0.80, 0.88, '{"fallback": 50}'::jsonb,
                     '{"note": "Bootstrap model; replace with trained RF/SVM before clinical use."}'::jsonb,
                     'Deterministic bootstrap model for MVP integration')
                ON CONFLICT (version_tag)
                DO UPDATE SET is_production=EXCLUDED.is_production
                RETURNING id
                '''
            )
        )
        return str(result.scalar_one())

    async def register_model_version(self, version_tag: str | None, *, source: str) -> tuple[str, str]:
        """Registra/recupera la versión real del modelo PLN devuelta por el 8001.
        Devuelve (model_version_id, version_tag_efectivo). Si no hay versión
        (fallback local) usa el modelo rule-based."""
        if not version_tag or source != "service":
            return await self.get_or_create_rule_model(), "pln-rule-v1"
        # Se registra como NO producción: la promoción exige métricas validadas y es
        # una acción admin explícita (HU-BK-13 / HU-BD-10), no automática.
        result = await self.session.execute(
            text(
                '''
                INSERT INTO diagnosis.ml_model_versions
                    (version_tag, algorithm, train_date, is_production, notes)
                VALUES
                    (:version_tag, 'PLN+ML (Diagnosis Service)', CURRENT_DATE, FALSE,
                     'Versión registrada automáticamente desde el Diagnosis Service (8001). Promover vía /admin/model-versions/activate tras validar métricas.')
                ON CONFLICT (version_tag)
                DO UPDATE SET notes = diagnosis.ml_model_versions.notes
                RETURNING id
                '''
            ),
            {"version_tag": version_tag},
        )
        return str(result.scalar_one()), version_tag

    async def save_diagnosis(self, *, context: dict, result_payload: dict, feature_vector: list[float], error_breakdown: dict, module_metrics: dict) -> dict:
        pln_source = result_payload.get("pln_source", "service")
        model_id, model_version = await self.register_model_version(result_payload.get("model_version"), source=pln_source)
        diagnosis = await self.session.execute(
            text(
                '''
                INSERT INTO diagnosis.diagnoses
                    (student_id, assignment_id, model_version_id, subtype, severity, risk_probability,
                     feature_vector, class_probabilities, risk_level, main_error_codes, feature_vector_28,
                     recommendation_reason, pln_subtype, pln_severity, model_version, error_breakdown, pln_source,
                     tede_nivel_lector)
                VALUES
                    (:student_id, :assignment_id, :model_id, CAST(:subtype AS diagnosis.dyslexia_subtype),
                     CAST(:severity AS diagnosis.severity_level), :risk_probability,
                     CAST(:feature_vector AS jsonb), CAST(:class_probabilities AS jsonb), :risk_level,
                     :main_error_codes, :feature_vector_28, :recommendation_reason,
                     :pln_subtype, :pln_severity, :model_version, CAST(:error_breakdown AS jsonb), :pln_source,
                     CAST(:tede_nivel_lector AS jsonb))
                RETURNING id, student_id, assignment_id, subtype::text AS subtype, severity::text AS severity,
                          risk_probability::float AS risk_probability, risk_level, main_error_codes,
                          pln_subtype, pln_severity, model_version, pln_source, tede_nivel_lector, diagnosed_at
                '''
            ),
            {
                "student_id": str(context["student_id"]),
                "assignment_id": str(context["assignment_id"]),
                "model_id": model_id,
                "subtype": result_payload["subtype"],
                "severity": result_payload["severity"],
                "risk_probability": result_payload["risk_probability"],
                "feature_vector": json.dumps({"feature_vector_28": feature_vector, "module_metrics": module_metrics}),
                "class_probabilities": json.dumps({result_payload["subtype"]: result_payload["risk_probability"]}),
                "risk_level": result_payload["risk_level"],
                "main_error_codes": result_payload["main_error_codes"],
                "feature_vector_28": feature_vector,
                "recommendation_reason": result_payload["recommendation_reason"],
                "pln_subtype": result_payload.get("pln_subtype"),
                "pln_severity": result_payload.get("pln_severity"),
                "model_version": model_version,
                "error_breakdown": json.dumps(error_breakdown),
                "pln_source": pln_source,
                # None y no {}: el JSONB nulo distingue "no se pudo calcular"
                # de "se calculó y dio vacío", y esa diferencia importa al
                # leer la curva.
                "tede_nivel_lector": (
                    json.dumps(result_payload["tede_nivel_lector"])
                    if result_payload.get("tede_nivel_lector") else None
                ),
            },
        )
        saved = dict(diagnosis.mappings().one())

        await self.session.execute(
            text(
                '''
                INSERT INTO diagnosis.pipeline_runs
                    (assignment_id, test_session_id, model_version_id, feature_vector_28, error_breakdown,
                     module_metrics, subtype, severity, risk_probability, risk_level)
                VALUES
                    (:assignment_id, :session_id, :model_id, :feature_vector_28, CAST(:error_breakdown AS jsonb),
                     CAST(:module_metrics AS jsonb), CAST(:subtype AS diagnosis.dyslexia_subtype),
                     CAST(:severity AS diagnosis.severity_level), :risk_probability, :risk_level)
                '''
            ),
            {
                "assignment_id": str(context["assignment_id"]),
                "session_id": str(context["session_id"]),
                "model_id": model_id,
                "feature_vector_28": feature_vector,
                "error_breakdown": json.dumps(error_breakdown),
                "module_metrics": json.dumps(module_metrics),
                "subtype": result_payload["subtype"],
                "severity": result_payload["severity"],
                "risk_probability": result_payload["risk_probability"],
                "risk_level": result_payload["risk_level"],
            },
        )

        await self._save_tracking_session(context, saved, result_payload, feature_vector, error_breakdown, model_version)
        saved["recommended_route"] = result_payload["recommended_route"]
        saved["recommendation_reason"] = result_payload["recommendation_reason"]
        saved["feature_vector_28"] = feature_vector
        return saved

    async def _save_tracking_session(self, context: dict, diagnosis: dict, result_payload: dict, feature_vector: list[float], error_breakdown: dict, model_version: str) -> None:
        session_number = await self.session.execute(
            text("SELECT COALESCE(MAX(session_number), 0) + 1 FROM tracking.diagnosis_ml_sessions WHERE student_id=:student_id"),
            {"student_id": str(context["student_id"])},
        )
        await self.session.execute(
            text(
                '''
                INSERT INTO tracking.diagnosis_ml_sessions
                    (student_id, assignment_id, diagnosis_id, session_number, grade, accuracy, error_rate,
                     feature_vector, feature_vector_28, error_breakdown, subtype, severity, risk_probability,
                     risk_level, model_version, exercise_route)
                VALUES
                    (:student_id, :assignment_id, :diagnosis_id, :session_number, :grade, :accuracy, :error_rate,
                     CAST(:feature_vector AS jsonb), :feature_vector_28, CAST(:error_breakdown AS jsonb), :subtype,
                     :severity, :risk_probability, :risk_level, :model_version, CAST(:exercise_route AS jsonb))
                '''
            ),
            {
                "student_id": str(context["student_id"]),
                "assignment_id": str(context["assignment_id"]),
                "diagnosis_id": str(diagnosis["id"]),
                "session_number": session_number.scalar_one(),
                "grade": context.get("grade", 3),
                "accuracy": 1 - (feature_vector[11] if len(feature_vector) > 11 else 0.0),
                "error_rate": feature_vector[11] if len(feature_vector) > 11 else 0.0,
                "feature_vector": json.dumps({"feature_vector_28": feature_vector}),
                "feature_vector_28": feature_vector,
                "error_breakdown": json.dumps(error_breakdown),
                "subtype": result_payload.get("pln_subtype") or result_payload["subtype"],
                "severity": result_payload.get("pln_severity") or result_payload["severity"],
                "risk_probability": result_payload["risk_probability"],
                "risk_level": result_payload["risk_level"],
                "model_version": model_version,
                "exercise_route": json.dumps(result_payload["recommended_route"]),
            },
        )

    async def save_student_path(self, *, student_id, diagnosis_id, recommendation: dict, route_profile: str | None) -> dict | None:
        """Persiste en intervention.student_paths la ruta devuelta por el
        Recommendation Service (8002). Resuelve learning_path_id y route_template_id
        por el profile_code. Devuelve None si la ruta es vacía (sin_riesgo)."""
        exercises = recommendation.get("exercises", []) or []
        exercise_ids = [ex["exercise_id"] for ex in exercises]
        if not exercise_ids:
            return None

        # Desactivar rutas previas del alumno.
        await self.session.execute(
            text("UPDATE intervention.student_paths SET is_active=FALSE WHERE student_id=:student_id AND is_active"),
            {"student_id": str(student_id)},
        )

        # Resolver learning_path + route_template por el perfil RAW del PLN.
        path_row = await self.session.execute(
            text(
                '''
                SELECT lp.id AS learning_path_id, rt.id AS route_template_id, rt.route_code
                FROM intervention.route_templates rt
                LEFT JOIN intervention.learning_paths lp
                    ON lp.id = (
                        SELECT e.learning_path_id FROM intervention.exercises e
                        WHERE e.exercise_code = ANY(:exercise_ids) AND e.learning_path_id IS NOT NULL
                        LIMIT 1
                    )
                WHERE rt.profile_code = :profile_code AND rt.is_active
                LIMIT 1
                '''
            ),
            {"profile_code": route_profile or "", "exercise_ids": exercise_ids},
        )
        path = path_row.mappings().first()
        if not path or not path.get("learning_path_id"):
            # Sin learning_path mapeable: persistimos la ruta igual con el primer learning_path como ancla.
            fallback = await self.session.execute(
                text("SELECT id FROM intervention.learning_paths WHERE is_active ORDER BY created_at LIMIT 1")
            )
            learning_path_id = fallback.scalar_one()
            route_template_id = path.get("route_template_id") if path else None
        else:
            learning_path_id = path["learning_path_id"]
            route_template_id = path["route_template_id"]

        inserted = await self.session.execute(
            text(
                '''
                INSERT INTO intervention.student_paths
                    (student_id, learning_path_id, diagnosis_id, route_template_id, route_reason,
                     exercise_route, total_exercises, pln_profile, is_active)
                VALUES
                    (:student_id, :learning_path_id, :diagnosis_id, :route_template_id, :route_reason,
                     CAST(:exercise_route AS jsonb), :total_exercises, :pln_profile, TRUE)
                RETURNING id, total_exercises, route_template_id
                '''
            ),
            {
                "student_id": str(student_id),
                "learning_path_id": str(learning_path_id),
                "diagnosis_id": str(diagnosis_id),
                "route_template_id": str(route_template_id) if route_template_id else None,
                "route_reason": recommendation.get("message"),
                "exercise_route": json.dumps(exercise_ids),
                "total_exercises": recommendation.get("total_exercises", len(exercise_ids)),
                "pln_profile": route_profile,
            },
        )
        row = dict(inserted.mappings().one())
        row["exercise_route"] = exercise_ids
        return row

    async def get_pending_diagnoses(self, *, institution_id: UUID, limit: int = 50) -> list[dict]:
        """Diagnósticos sin etiqueta de especialista, ordenados por más recientes,
        acotados a la institución del especialista solicitante."""
        result = await self.session.execute(
            text(
                """
                SELECT
                    d.id,
                    d.subtype::text          AS auto_subtype,
                    d.severity::text         AS auto_severity,
                    d.risk_level             AS auto_risk_level,
                    d.risk_probability::float,
                    d.main_error_codes,
                    d.error_breakdown,
                    d.pln_source,
                    d.diagnosed_at,
                    pgp_sym_decrypt(s.full_name, :key)::text AS student_name,
                    g.grade
                FROM diagnosis.diagnoses d
                JOIN academic.students s ON s.id = d.student_id
                JOIN academic.groups g ON g.id = s.group_id
                LEFT JOIN diagnosis.training_labels tl ON tl.diagnosis_id = d.id
                WHERE tl.id IS NULL AND g.school_id = :institution_id
                ORDER BY d.diagnosed_at DESC
                LIMIT :limit
                """
            ),
            {"limit": limit, "institution_id": str(institution_id), "key": self.settings.db_encryption_key},
        )
        rows = result.mappings().all()
        return [
            {
                "id": str(r["id"]),
                "auto_subtype": r["auto_subtype"],
                "auto_severity": r["auto_severity"],
                "auto_risk_level": r["auto_risk_level"],
                "risk_probability": float(r["risk_probability"] or 0),
                "main_error_codes": list(r["main_error_codes"] or []),
                "error_breakdown": dict(r["error_breakdown"]) if r["error_breakdown"] else {},
                "pln_source": r["pln_source"],
                "tede_nivel_lector": dict(r["tede_nivel_lector"]) if r["tede_nivel_lector"] else None,
                "diagnosed_at": r["diagnosed_at"].isoformat() if r["diagnosed_at"] else None,
                "student_name": r["student_name"],
                "grade": r["grade"],
            }
            for r in rows
        ]

    async def label_diagnosis(
        self,
        *,
        diagnosis_id: UUID,
        specialist_id: UUID,
        confirmed_subtype: str,
        confirmed_severity: str,
        confirmed_risk_level: str,
        notes: str | None = None,
    ) -> dict:
        """Crea o actualiza la etiqueta clínica para un diagnóstico.
        Copia feature_vector_28 del diagnóstico para el dataset de entrenamiento."""
        row = await self.session.execute(
            text("SELECT feature_vector_28 FROM diagnosis.diagnoses WHERE id = :id"),
            {"id": str(diagnosis_id)},
        )
        diagnosis_row = row.mappings().first()
        if not diagnosis_row:
            raise ValueError(f"Diagnóstico {diagnosis_id} no encontrado")

        inserted = await self.session.execute(
            text(
                """
                INSERT INTO diagnosis.training_labels
                    (diagnosis_id, feature_vector_28, confirmed_subtype, confirmed_severity,
                     confirmed_risk_level, specialist_id, notes)
                VALUES
                    (:diagnosis_id, :fv28,
                     CAST(:confirmed_subtype AS diagnosis.dyslexia_subtype),
                     CAST(:confirmed_severity AS diagnosis.severity_level),
                     :confirmed_risk_level, :specialist_id, :notes)
                ON CONFLICT (diagnosis_id) DO UPDATE SET
                    confirmed_subtype    = CAST(EXCLUDED.confirmed_subtype AS diagnosis.dyslexia_subtype),
                    confirmed_severity   = CAST(EXCLUDED.confirmed_severity AS diagnosis.severity_level),
                    confirmed_risk_level = EXCLUDED.confirmed_risk_level,
                    notes                = EXCLUDED.notes,
                    specialist_id        = EXCLUDED.specialist_id,
                    labeled_at           = now()
                RETURNING id, diagnosis_id, confirmed_subtype::text, confirmed_severity::text,
                          confirmed_risk_level, labeled_at
                """
            ),
            {
                "diagnosis_id": str(diagnosis_id),
                "fv28": diagnosis_row["feature_vector_28"],
                "confirmed_subtype": confirmed_subtype,
                "confirmed_severity": confirmed_severity,
                "confirmed_risk_level": confirmed_risk_level,
                "specialist_id": str(specialist_id),
                "notes": notes,
            },
        )
        saved = dict(inserted.mappings().one())
        return {
            "id": str(saved["id"]),
            "diagnosis_id": str(saved["diagnosis_id"]),
            "confirmed_subtype": saved["confirmed_subtype"],
            "confirmed_severity": saved["confirmed_severity"],
            "confirmed_risk_level": saved["confirmed_risk_level"],
            "labeled_at": saved["labeled_at"].isoformat() if saved["labeled_at"] else None,
        }

    async def get_latest_risk(
        self, student_id: UUID, *, requester_id: UUID, is_privileged: bool, institution_id: UUID
    ) -> dict | None:
        """Verifica institución y, si no es privilegiado, propiedad (docente/padre)
        antes de devolver el diagnóstico — antes cualquier rol autorizado podía leer
        el riesgo de cualquier alumno del sistema con solo su UUID (IDOR)."""
        result = await self.session.execute(
            text(
                '''
                SELECT r.* FROM diagnosis.v_latest_student_risk r
                JOIN academic.students s ON s.id = r.student_id
                JOIN academic.groups g ON g.id = s.group_id
                WHERE r.student_id = :student_id AND g.school_id = :institution_id
                  AND (:is_privileged OR g.teacher_id = :requester_id OR s.parent_user_id = :requester_id)
                '''
            ),
            {
                "student_id": str(student_id),
                "institution_id": str(institution_id),
                "is_privileged": is_privileged,
                "requester_id": str(requester_id),
            },
        )
        row = result.mappings().first()
        return dict(row) if row else None
