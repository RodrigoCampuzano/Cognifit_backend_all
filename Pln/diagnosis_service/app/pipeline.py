"""
Orquestador del pipeline de diagnóstico.
Encadena: preprocesamiento -> detección de errores -> feature engineering -> predicción ML.
"""
import json
from pathlib import Path

from app.pln.preprocessor import preprocess, preprocess_item, handle_timeout
from app.pln.error_detector import detect_errors, detect_word_level_errors, is_lexicalization
from app.pln.phonetics import phonetic_similarity, ngram_overlap
from app.pln.features import build_feature_vector, add_context_features
from app.ml.predictor import predict_profile

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

# Cargar léxico una sola vez al importar el módulo
_LEXICON_PATH = DATA_DIR / "lexico_es_2000.json"
if _LEXICON_PATH.exists():
    LEXICON = set(json.loads(_LEXICON_PATH.read_text(encoding="utf-8")))
else:
    LEXICON = set()


def process_session(session: dict, registry) -> dict:
    """
    Procesa una sesión completa de diagnóstico.

    session = {
        "student_id": int, "grade": int, "teacher_score": float,
        "items": [ {target, response, module, response_time_ms, ...}, ... ]
    }

    Devuelve el diagnóstico completo + breakdown de errores + feature vector.
    """
    processed_items = []

    for raw_item in session["items"]:
        # 1. Manejar timeout primero
        item = handle_timeout(raw_item)

        if item.get("is_timeout"):
            # El timeout ya viene con sus errores y métricas calculadas
            processed_items.append(item)
            continue

        # 2. Preprocesar
        target = preprocess(item.get("target", ""))
        response = preprocess_item(item)

        # 3. Detectar errores
        errors = detect_errors(target, response)

        # 3b. Errores a nivel de palabra: inversiones de letras/sílabas (INV),
        # segmentación (SEG) y unión (UNI). detect_word_level_errors existía
        # pero NUNCA se llamaba desde acá, así que esos códigos jamás se
        # emitían y sus dimensiones del feature vector quedaban clavadas en 0.
        #
        # Esto NO cambia las predicciones del modelo actual: sus árboles tienen
        # importancia exactamente 0 en INV/SEG/UNI (se entrenó con esas
        # columnas constantes), así que nunca ramifican por ellas. Se corrige
        # para que el feature_vector_28 que se persiste sea VERDADERO — es el
        # insumo de diagnosis.training_labels y, por lo tanto, del
        # reentrenamiento con etiquetas reales de especialista. Sin esto, el
        # próximo modelo volvería a entrenarse creyendo que ningún niño
        # invierte letras, que es un marcador clásico de dislexia.
        errors += detect_word_level_errors(target.split(), response.split())

        # 4. Detectar lexicalización en pseudopalabras
        if item.get("module") == "pseudopalabras":
            if is_lexicalization(target, response, LEXICON):
                errors.append({
                    "type": "LEX", "expected": target, "produced": response,
                    "detail": "pseudopalabra convertida en palabra real",
                    "is_diagnostic": True,
                })

        # 5. Construir ítem procesado
        processed_items.append({
            **item,
            "module": item.get("module", ""),
            "errors": errors,
            "is_correct": target == response,
            "phonetic_similarity": phonetic_similarity(target, response),
            "ngram_overlap": ngram_overlap(target, response),
            "is_timeout": False,
        })

    # 6. Feature engineering
    fv = build_feature_vector(processed_items)
    fv = add_context_features(
        fv,
        grade=session.get("grade", 1),
        teacher_score=session.get("teacher_score", 0.0),
    )

    # 7. Predicción ML
    profile = predict_profile(fv, registry)

    # 8. Identificar errores dominantes (solo diagnósticos)
    error_counts = {}
    for item in processed_items:
        for err in item.get("errors", []):
            if err.get("is_diagnostic", True):
                code = err["type"]
                error_counts[code] = error_counts.get(code, 0) + 1

    main_errors = sorted(error_counts, key=error_counts.get, reverse=True)[:3]

    return {
        **profile,
        "main_error_codes": main_errors,
        "error_breakdown": error_counts,
        "feature_vector": fv.tolist(),
        "items_processed": len(processed_items),
        "items_timeout": sum(1 for it in processed_items if it.get("is_timeout")),
    }
