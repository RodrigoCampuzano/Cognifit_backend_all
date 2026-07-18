"""Mide cuántos diagnósticos cambian al corregir la medición del tiempo.

Contexto
--------
El tiempo de respuesta es la señal con más peso del modelo: `avg_time_norm` es
la feature #1 de las 28 (importancia 0.163), `slow_response_rate` la #3 y
`std_time_norm` la #6 — juntas ~36% del total. Hasta ahora ese número incluía
la reproducción del audio TTS y el tiempo con la app en segundo plano, así que
medía algo distinto de lo que dice medir.

Corregirlo es lo correcto, pero **cambia diagnósticos existentes**: al restar el
audio, muchos niños hoy clasificados `fluidez` (el perfil "responde bien pero
lento") dejan de estarlo. Este script cuantifica ese corrimiento ANTES de
desplegar, para no cambiar a ciegas la señal dominante de una herramienta que
tamiza niños.

Uso
---
    python -m training.compare_timing_impact                 # casos representativos
    python -m training.compare_timing_impact --tts-ms 4000   # audio asumido por ítem

Limitación honesta
------------------
La base de producción todavía no tiene respuestas reales, así que por defecto
corre sobre casos construidos a mano (con y sin uso de audio, distintos grados).
El número real de diagnósticos afectados solo se sabrá con datos de uso: cuando
existan, este script debe re-correrse leyendo `assessment.student_responses`
(`timing_detail.total_ms` vs `timing_detail.net_ms`) antes de dar por buena la
corrección.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.ml.predictor import ModelRegistry  # noqa: E402
from app.pipeline import process_session  # noqa: E402

PALABRAS = ["casa", "mesa", "silla", "libro", "perro", "gato"]


def _sesion(grade: int, ms: int, correctas: bool) -> dict:
    return {
        "student_id": 1,
        "grade": grade,
        "teacher_score": 50.0,
        "items": [
            {
                "target": w,
                "response": w if correctas else w[:-1],
                "module": "palabras_reales",
                "response_time_ms": ms,
            }
            for w in PALABRAS
        ],
    }


def _diagnostico(reg, grade: int, ms: int, correctas: bool) -> tuple[str, str]:
    r = process_session(_sesion(grade, ms, correctas), reg)
    return r["subtype"], r["risk_level"]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tts-ms", type=int, default=4000,
                    help="ms de audio que se estaban contando como tiempo de respuesta")
    args = ap.parse_args()

    reg = ModelRegistry()
    print(f"Descontando {args.tts_ms} ms de audio por ítem.\n")

    encabezado = f"{'grado':>5} {'respuestas':>11} {'neto':>7} {'ANTES (con audio)':>26} {'DESPUES (neto)':>24}"
    print(encabezado)
    print("-" * len(encabezado))

    cambios = 0
    total = 0
    for correctas in (True, False):
        for grade in (1, 3, 6):
            for neto in (1500, 3000, 5000):
                antes = _diagnostico(reg, grade, neto + args.tts_ms, correctas)
                despues = _diagnostico(reg, grade, neto, correctas)
                total += 1
                cambio = antes != despues
                cambios += cambio
                marca = "  <-- CAMBIA" if cambio else ""
                etiqueta = "correctas" if correctas else "con error"
                print(f"{grade:>5} {etiqueta:>11} {neto:>6}ms "
                      f"{antes[0] + '/' + antes[1]:>26} {despues[0] + '/' + despues[1]:>24}{marca}")

    print()
    print(f"Escenarios que cambian de diagnóstico: {cambios}/{total}")
    if cambios:
        print(
            "\nEl corrimiento es el esperado: al dejar de contar el audio como\n"
            "tiempo de resolución, deja de marcarse 'fluidez' a niños que solo\n"
            "estaban usando el apoyo auditivo. Revisar la dirección de cada\n"
            "cambio antes de desplegar."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
