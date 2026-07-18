"""Reentrena los modelos de subtipo y severidad con etiquetas REALES de especialista.

Por qué existe
--------------
Los modelos en producción (`app/models/*.pkl`, versión 20260618_0309) se
entrenaron con 1500 muestras sintéticas. Al inspeccionarlos se encontró que
**12 de sus 28 features tienen importancia exactamente 0**, o sea que fueron
constantes en ese dataset — entre ellas `teacher_score_norm` (el cuestionario
PRODISLEX del docente, que hoy no influye en nada), `FON_rate`, `LEX_rate`,
`timeout_rate` e `INV_rate`. Su f1 de 0.95 mide ajuste a datos sintéticos, no
exactitud clínica.

La corrección real no es tocar el código de inferencia: es reentrenar con los
casos que los especialistas van confirmando en la app. Cada vez que un
especialista corrige un diagnóstico (`POST /screening/diagnoses/{id}/label`),
se guarda en `diagnosis.training_labels` el `feature_vector_28` junto con el
subtipo/severidad/riesgo confirmados, sin PII. Este script consume esa tabla.

Uso
---
    export DATABASE_URL='postgresql://...'
    python -m training.retrain_from_labels --dry-run     # solo reporta
    python -m training.retrain_from_labels --min-per-class 50

Por defecto NO sobrescribe los modelos en producción: escribe en
`app/models/candidates/` con la fecha en el nombre. Promoverlos es una decisión
humana — se comparan métricas contra el modelo vigente y se despliega a mano.

Requisitos de datos
-------------------
`--min-per-class` (50 por defecto, el umbral que fija el COMMENT de la tabla)
evita entrenar con un puñado de casos: un modelo clínico ajustado a 5 ejemplos
por clase es peor que el que ya está, aunque sus métricas se vean bien.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

MODELS_DIR = Path(__file__).resolve().parent.parent / "app" / "models"
CANDIDATES_DIR = MODELS_DIR / "candidates"

# Debe coincidir 1:1 con app/pln/features.py — si el vector cambia de tamaño o
# de orden, los modelos viejos y los nuevos dejan de ser comparables.
EXPECTED_DIMS = 28

QUERY = """
    SELECT feature_vector_28, confirmed_subtype, confirmed_severity, confirmed_risk_level
    FROM diagnosis.training_labels
    ORDER BY labeled_at
"""

# La DB guarda el enum clínico; los modelos predicen el vocabulario RAW del PLN.
ENUM_TO_PLN_SUBTYPE = {
    "PHONOLOGICAL": "fonologico",
    "VISUAL_SURFACE": "visual",
    "MIXED": "mixto",
    "NO_DYSLEXIA": "sin_riesgo",
}
ENUM_TO_PLN_SEVERITY = {"MILD": "leve", "MODERATE": "moderado", "SEVERE": "severo"}


def fetch_labels(database_url: str) -> list[dict]:
    import psycopg

    with psycopg.connect(database_url) as conn, conn.cursor() as cur:
        cur.execute(QUERY)
        return [
            {
                "features": [float(x) for x in row[0]],
                "subtype": ENUM_TO_PLN_SUBTYPE.get(str(row[1]), str(row[1])),
                "severity": ENUM_TO_PLN_SEVERITY.get(str(row[2]), str(row[2])),
                "risk_level": row[3],
            }
            for row in cur.fetchall()
        ]


def report(labels: list[dict]) -> tuple[Counter, Counter]:
    subt = Counter(l["subtype"] for l in labels)
    sev = Counter(l["severity"] for l in labels if l["subtype"] != "sin_riesgo")
    print(f"\nEtiquetas disponibles: {len(labels)}")
    print("  por subtipo:  " + (", ".join(f"{k}={v}" for k, v in sorted(subt.items())) or "—"))
    print("  por severidad:" + (", ".join(f" {k}={v}" for k, v in sorted(sev.items())) or " —"))
    return subt, sev


def check_ready(subt: Counter, sev: Counter, min_per_class: int) -> list[str]:
    """Devuelve los motivos por los que todavía NO conviene reentrenar."""
    problemas = []
    if len(subt) < 2:
        problemas.append("hay una sola clase de subtipo; un clasificador necesita al menos dos")
    for clase, n in sorted(subt.items()):
        if n < min_per_class:
            problemas.append(f"subtipo '{clase}': {n} etiquetas (<{min_per_class})")
    for clase, n in sorted(sev.items()):
        if n < min_per_class:
            problemas.append(f"severidad '{clase}': {n} etiquetas (<{min_per_class})")
    return problemas


def train(labels: list[dict], out_dir: Path) -> dict:
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.metrics import balanced_accuracy_score, f1_score
    from sklearn.model_selection import train_test_split
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import StandardScaler
    import joblib

    from app.pln.features import FEATURE_NAMES

    X = np.array([l["features"] for l in labels], dtype=float)
    if X.shape[1] != EXPECTED_DIMS:
        raise SystemExit(
            f"Los vectores guardados tienen {X.shape[1]} dimensiones y se esperaban "
            f"{EXPECTED_DIMS}. Revisá app/pln/features.py antes de reentrenar."
        )

    version = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M")
    out_dir.mkdir(parents=True, exist_ok=True)
    resumen = {"version": version, "n_samples": len(labels)}

    for nombre, clave in (("subtype", "subtype"), ("severity", "severity")):
        if clave == "severity":
            idx = [i for i, l in enumerate(labels) if l["subtype"] != "sin_riesgo"]
            Xi, y = X[idx], [labels[i]["severity"] for i in idx]
        else:
            Xi, y = X, [l["subtype"] for l in labels]

        X_tr, X_te, y_tr, y_te = train_test_split(Xi, y, test_size=0.2, random_state=42, stratify=y)
        pipe = Pipeline([
            ("scaler", StandardScaler()),
            ("classifier", RandomForestClassifier(n_estimators=300, random_state=42, class_weight="balanced")),
        ])
        pipe.fit(X_tr, y_tr)
        pred = pipe.predict(X_te)
        metrics = {
            "f1_macro": float(f1_score(y_te, pred, average="macro")),
            "balanced_accuracy": float(balanced_accuracy_score(y_te, pred)),
            "n_samples": len(Xi),
        }

        # Se avisa de features que siguen sin aportar: es exactamente el problema
        # que tiene el modelo actual (12/28 constantes) y conviene detectarlo
        # ANTES de promover un candidato.
        importancias = pipe.named_steps["classifier"].feature_importances_
        inertes = [FEATURE_NAMES[i] for i, imp in enumerate(importancias) if imp == 0.0]

        joblib.dump(
            {
                "model": pipe,
                "version": version,
                "metrics": metrics,
                "feature_names": list(FEATURE_NAMES),
                "n_features": EXPECTED_DIMS,
                "classes": list(pipe.named_steps["classifier"].classes_),
                "trained_on_samples": len(Xi),
                "trained_from": "diagnosis.training_labels",
                "dataset_sha256": hashlib.sha256(Xi.tobytes()).hexdigest(),
                "inert_features": inertes,
            },
            out_dir / f"{nombre}_model_{version}.pkl",
        )
        resumen[nombre] = {"metrics": metrics, "inert_features": inertes}
        print(f"\n[{nombre}] f1_macro={metrics['f1_macro']:.3f} "
              f"balanced_acc={metrics['balanced_accuracy']:.3f} (n={len(Xi)})")
        if inertes:
            print(f"  ⚠ {len(inertes)}/28 features sin aporte: {', '.join(inertes)}")

    return resumen


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--database-url", default=os.getenv("DATABASE_URL"))
    ap.add_argument("--min-per-class", type=int, default=50)
    ap.add_argument("--dry-run", action="store_true", help="solo reporta cuántas etiquetas hay")
    ap.add_argument("--force", action="store_true", help="entrena aunque falten etiquetas (NO usar para producción)")
    ap.add_argument("--out", type=Path, default=CANDIDATES_DIR)
    args = ap.parse_args()

    if not args.database_url:
        print("Falta DATABASE_URL (o --database-url).", file=sys.stderr)
        return 2

    labels = fetch_labels(args.database_url)
    subt, sev = report(labels)

    problemas = check_ready(subt, sev, args.min_per_class)
    if problemas:
        print("\nTodavía no conviene reentrenar:")
        for p in problemas:
            print(f"  - {p}")
        print("\nCada diagnóstico que un especialista confirme en la app suma una etiqueta.")
        if not args.force:
            return 1
        print("\n--force: se entrena igual. El resultado NO es apto para producción.")

    if args.dry_run:
        print("\n--dry-run: no se entrena nada.")
        return 0

    resumen = train(labels, args.out)
    (args.out / f"resumen_{resumen['version']}.json").write_text(
        json.dumps(resumen, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"\nCandidatos escritos en {args.out}")
    print("NO se tocaron los modelos en producción. Para promover uno:")
    print("  1. comparar métricas contra el modelo vigente (GET /model/info)")
    print("  2. revisar que no queden features inertes relevantes")
    print("  3. copiarlo a app/models/{subtype,severity}_model_latest.pkl y redesplegar")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
