#!/usr/bin/env python3
"""Genera database/005_seed_test_items.sql con los ítems de cada módulo de la batería.

Fuentes:
- TEDE (database/seeds/tede_item_bank.json) → letras, sílabas y pseudopalabras.
- Listas curadas (abajo) → palabras reales, dictado, conciencia fonológica, copia,
  denominación rápida y comprensión.

Cada ítem se inserta enlazado a su test (por module_code) y se marca con
source_instrument_code='COGNIFIT_SEED_V1' para poder re-sembrar de forma idempotente.
El item_kind se fija con los valores que entiende el pipeline NLP/ML
(PSEUDOWORDS, REAL_WORDS, ...).
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEDE = json.loads((ROOT / "seeds" / "tede_item_bank.json").read_text(encoding="utf-8"))
OUT = ROOT / "005_seed_test_items.sql"

SEED_TAG = "COGNIFIT_SEED_V1"


def esc(text: str) -> str:
    return str(text).replace("'", "''")


# ── Construcción de contenido por módulo ──────────────────────────────────────
def tede_letters() -> list[str]:
    nl = TEDE["nivel_lector"]
    return [*nl["nombre_letra"], *nl["sonido_letra"]]


def tede_syllables() -> list[str]:
    nl = TEDE["nivel_lector"]
    out: list[str] = []
    for key in (
        "silabas_directas_sonido_simple",
        "silabas_directas_doble_sonido",
        "silabas_indirectas_simple",
        "silabas_complejas",
        "diptongo_simple",
    ):
        out.extend(nl.get(key, []))
    return out


def tede_pseudowords() -> list[str]:
    ee = TEDE["errores_especificos"]
    return [*ee["grafia_semejante_pseudopalabras"], *ee["confundibles_sonido_palabras"]]


# Listas curadas (español, primaria) para los módulos sin estímulos en TEDE.
REAL_WORDS = ["casa", "perro", "mesa", "sol", "libro", "ventana", "camino", "mariposa",
              "pelota", "escuela", "bicicleta", "tijeras"]
DICTATION = ["bota", "queso", "jirafa", "guitarra", "pingüino", "cielo",
             "burbuja", "chocolate"]
PHON_AWARENESS = ["sol", "casa", "mariposa", "pan", "luna", "camino", "rosa", "barco"]
COPY_TEXT = ["el gato duerme", "la niña corre", "mi casa es azul",
             "vamos al parque", "hoy hace sol"]
COMPREHENSION = [
    "El perro de Ana es café. Le gusta correr en el parque por las tardes.",
    "Pedro tiene una bicicleta roja. Todos los días va a la escuela en ella.",
]
RAN_STIMULI = [
    *(s for s in (TEDE.get("__noop__") or [])),
]
# RAN: colores/objetos del content pack si existen; si no, set básico.
try:
    pack = json.loads((ROOT / "seeds" / "cognifit_app_content_pack.json").read_text(encoding="utf-8"))
    ran_mod = next((m for m in pack["modules"] if m.get("id") == "rapid_naming"), {})
    stim = ran_mod.get("stimuli", {})
    RAN_STIMULI = [*stim.get("colors", []), *stim.get("objects", [])]
except Exception:
    pass
if not RAN_STIMULI:
    RAN_STIMULI = ["rojo", "azul", "verde", "amarillo", "casa", "sol", "perro", "flor"]


# (module_code, item_kind, difficulty, [stimulus, ...])  expected = stimulus salvo override
MODULES: list[tuple[str, str, int, list[str]]] = [
    ("M02_PHONOLOGICAL_AWARENESS", "PHONOLOGICAL_AWARENESS", 1, PHON_AWARENESS),
    ("M03_LETTERS_SYLLABLES", "LETTERS_SYLLABLES", 1, tede_letters() + tede_syllables()),
    ("M04_REAL_WORDS", "REAL_WORDS", 2, REAL_WORDS),
    ("M05_PSEUDOWORDS", "PSEUDOWORDS", 3, tede_pseudowords()),
    ("M06_SMART_DICTATION", "SMART_DICTATION", 3, DICTATION),
    ("M07_CONTROLLED_COPY", "CONTROLLED_COPY", 1, COPY_TEXT),
    ("M08_RAPID_NAMING", "RAPID_NAMING", 1, RAN_STIMULI),
    ("M09_READING_COMPREHENSION", "READING_COMPREHENSION", 3, COMPREHENSION),
]


def build_sql() -> str:
    parts: list[str] = [
        "-- =============================================================",
        "-- 005_seed_test_items.sql  (GENERADO por scripts/generate_test_items_seed.py)",
        "-- Ítems de la batería para que la app los muestre y el alumno los responda.",
        "-- Idempotente: borra y re-inserta los ítems marcados COGNIFIT_SEED_V1.",
        "-- Ejecutar DESPUÉS de schema.sql, 002, 003 y 004.",
        "-- =============================================================",
        "",
        f"DELETE FROM assessment.test_items WHERE source_instrument_code = '{SEED_TAG}';",
        "",
    ]
    for module_code, item_kind, diff, stimuli in MODULES:
        # dedup conservando orden
        seen: set[str] = set()
        clean = [s for s in (x.strip() for x in stimuli) if s and not (s in seen or seen.add(s))]
        rows = []
        prefix = module_code.split("_")[0]  # Mxx
        for i, stim in enumerate(clean, start=1):
            code = f"{prefix}_{i:03d}"
            rows.append(f"  ({i}, '{esc(code)}', '{esc(stim)}', '{esc(stim)}', {diff})")
        values = ",\n".join(rows)
        parts.append(f"-- {module_code} ({len(clean)} ítems)")
        parts.append(
            "WITH m AS (\n"
            "  SELECT t.id AS test_id, t.module_id\n"
            "  FROM assessment.tests t\n"
            "  JOIN assessment.battery_modules bm ON bm.id = t.module_id\n"
            f"  WHERE bm.module_code = '{module_code}'\n"
            "  ORDER BY t.created_at DESC LIMIT 1\n"
            ")\n"
            "INSERT INTO assessment.test_items\n"
            "  (test_id, module_id, item_order, item_code, stimulus_text, expected_response,\n"
            "   item_kind, difficulty, source_instrument_code, tags, is_practice)\n"
            f"SELECT m.test_id, m.module_id, v.ord, v.code, v.stim, v.expected, '{item_kind}', v.diff,\n"
            f"       '{SEED_TAG}', ARRAY['seed','{module_code.lower()}']::text[], FALSE\n"
            "FROM m CROSS JOIN (VALUES\n"
            f"{values}\n"
            ") AS v(ord, code, stim, expected, diff);"
        )
        parts.append("")
    parts.append("-- Verificación rápida:")
    parts.append("--   SELECT bm.module_code, count(*) FROM assessment.test_items ti")
    parts.append("--   JOIN assessment.battery_modules bm ON bm.id=ti.module_id GROUP BY 1 ORDER BY 1;")
    parts.append("")
    return "\n".join(parts)


if __name__ == "__main__":
    OUT.write_text(build_sql(), encoding="utf-8")
    print(f"Generado: {OUT}")
