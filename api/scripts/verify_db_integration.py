from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass

import psycopg


REQUIRED_SCHEMAS = ["auth", "academic", "assessment", "diagnosis", "intervention", "tracking", "reporting", "audit"]
REQUIRED_TABLES = [
    "auth.users",
    "auth.refresh_tokens",
    "academic.students",
    "assessment.battery_modules",
    "assessment.teacher_screening_items",
    "assessment.teacher_screening_results",
    "assessment.test_sessions",
    "assessment.student_responses",
    "diagnosis.error_codes",
    "diagnosis.feature_definitions",
    "diagnosis.pipeline_runs",
    "diagnosis.diagnoses",
    "intervention.route_templates",
    "tracking.diagnosis_ml_sessions",
    "tracking.alerts",
    "reporting.report_requests",
    "audit.audit_log",
]
REQUIRED_VIEWS = ["assessment.v_battery_catalog", "diagnosis.v_latest_student_risk"]
REQUIRED_COLUMNS = {
    "assessment.student_responses": ["session_id", "normalized_response", "expected_text", "edit_distance", "phonetic_similarity", "ngram_overlap", "error_breakdown"],
    "diagnosis.diagnoses": ["risk_level", "main_error_codes", "feature_vector_28", "recommendation_reason", "pln_subtype", "pln_severity", "model_version", "error_breakdown", "pln_source"],
    "tracking.diagnosis_ml_sessions": ["feature_vector_28", "exercise_route", "risk_probability"],
    "intervention.student_paths": ["route_template_id", "exercise_route", "total_exercises", "pln_profile"],
}


@dataclass
class Check:
    name: str
    ok: bool
    detail: str


def exists_schema(cur, schema: str) -> bool:
    cur.execute("SELECT EXISTS (SELECT 1 FROM information_schema.schemata WHERE schema_name=%s)", (schema,))
    return bool(cur.fetchone()[0])


def exists_relation(cur, relation: str, kind: str) -> bool:
    schema, name = relation.split(".")
    if kind == "table":
        cur.execute(
            '''
            SELECT EXISTS (
              SELECT 1 FROM information_schema.tables
              WHERE table_schema=%s AND table_name=%s AND table_type='BASE TABLE'
            )
            ''',
            (schema, name),
        )
    else:
        cur.execute(
            '''
            SELECT EXISTS (
              SELECT 1 FROM information_schema.views
              WHERE table_schema=%s AND table_name=%s
            )
            ''',
            (schema, name),
        )
    return bool(cur.fetchone()[0])


def count_rows(cur, relation: str) -> int:
    cur.execute(f"SELECT COUNT(*) FROM {relation}")
    return int(cur.fetchone()[0])


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database-url", required=True)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    checks: list[Check] = []
    with psycopg.connect(args.database_url) as conn:
        with conn.cursor() as cur:
            for schema in REQUIRED_SCHEMAS:
                checks.append(Check(f"schema:{schema}", exists_schema(cur, schema), "required schema"))
            for table in REQUIRED_TABLES:
                checks.append(Check(f"table:{table}", exists_relation(cur, table, "table"), "required table"))
            for view in REQUIRED_VIEWS:
                checks.append(Check(f"view:{view}", exists_relation(cur, view, "view"), "required view"))
            for relation, columns in REQUIRED_COLUMNS.items():
                schema, table = relation.split(".")
                for column in columns:
                    cur.execute(
                        '''
                        SELECT EXISTS (
                          SELECT 1 FROM information_schema.columns
                          WHERE table_schema=%s AND table_name=%s AND column_name=%s
                        )
                        ''',
                        (schema, table, column),
                    )
                    checks.append(Check(f"column:{relation}.{column}", bool(cur.fetchone()[0]), "required column"))

            seed_expectations = {
                "assessment.battery_modules": 9,
                "assessment.teacher_screening_items": 8,
                "diagnosis.feature_definitions": 28,
                "diagnosis.error_codes": 10,
                "intervention.route_templates": 5,
            }
            for relation, minimum in seed_expectations.items():
                try:
                    count = count_rows(cur, relation)
                    checks.append(Check(f"seed:{relation}", count >= minimum, f"{count} rows, minimum {minimum}"))
                except Exception as exc:
                    checks.append(Check(f"seed:{relation}", False, str(exc)))

    failed = [check for check in checks if not check.ok]
    if args.json:
        print(json.dumps({"ok": not failed, "checks": [check.__dict__ for check in checks]}, indent=2))
    else:
        for check in checks:
            mark = "OK" if check.ok else "FAIL"
            print(f"[{mark}] {check.name} - {check.detail}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
