"""
Construcción del feature vector de 28 dimensiones.
DEBE producir vectores idénticos a los del notebook de entrenamiento,
de lo contrario el modelo recibirá features inconsistentes.
"""
import numpy as np

FEATURE_NAMES = [
    "OMI_rate", "SUS_rate", "INV_rate", "ROT_rate", "LEX_rate", "SEG_rate",
    "UNI_rate", "FON_rate", "ADD_rate", "LEN_rate", "accuracy", "error_rate",
    "pseudo_vs_word_gap", "pseudo_error_rate", "word_error_rate",
    "avg_time_norm", "std_time_norm", "slow_response_rate", "avg_phonetic_sim",
    "avg_ngram_overlap", "rot_sus_ratio", "lex_flag", "seg_uni_rate",
    "inv_omi_ratio", "grade_norm", "teacher_score_norm", "timeout_rate",
    "lex_pseudo_flag",
]
assert len(FEATURE_NAMES) == 28


def build_feature_vector(items: list) -> np.ndarray:
    """Convierte los ítems de una sesión en un vector de 28 features."""
    codes = ["OMI", "SUS", "INV", "ROT", "LEX", "SEG", "UNI", "FON", "ADD", "LEN"]
    ec = {c: 0 for c in codes}
    total = len(items)
    if total == 0:
        return np.zeros(28)

    correct = 0
    times, psims, ngrams = [], [], []
    pe = pt = we = wt = 0

    for it in items:
        if it.get("is_correct"):
            correct += 1
        if not it.get("is_timeout") and it.get("response_time_ms"):
            times.append(it["response_time_ms"])
        for e in it.get("errors", []):
            if e["type"] in ec and e.get("is_diagnostic", True):
                ec[e["type"]] += 1
        if it.get("module") == "pseudopalabras":
            pt += 1
            if not it.get("is_correct"):
                pe += 1
        if it.get("module") == "palabras_reales":
            wt += 1
            if not it.get("is_correct"):
                we += 1
        if "phonetic_similarity" in it:
            psims.append(it["phonetic_similarity"])
        if "ngram_overlap" in it:
            ngrams.append(it["ngram_overlap"])

    acc = correct / total if total else 0
    per = pe / pt if pt else 0
    wer = we / wt if wt else 0
    at = np.mean(times) if times else 0
    st = np.std(times) if times else 0
    slow = sum(1 for t in times if t > 5000) / len(times) if times else 0

    return np.array([
        ec["OMI"] / total, ec["SUS"] / total, ec["INV"] / total, ec["ROT"] / total,
        ec["LEX"] / total, ec["SEG"] / total, ec["UNI"] / total, ec["FON"] / total,
        ec["ADD"] / total, ec["LEN"] / total,
        acc, 1 - acc, per - wer, per, wer,
        at / 10000, st / 10000, slow,
        np.mean(psims) if psims else 0, np.mean(ngrams) if ngrams else 0,
        ec["ROT"] / (ec["SUS"] + 1), 1 if ec["LEX"] > 0 else 0,
        (ec["SEG"] + ec["UNI"]) / total, ec["INV"] / (ec["OMI"] + 1),
        0.0, 0.0,  # grade_norm, teacher_score_norm (rellenados por add_context_features)
        sum(1 for it in items if it.get("is_timeout")) / total,
        1.0 if any(
            e["type"] == "LEX"
            for it in items
            for e in it.get("errors", [])
            if it.get("module") == "pseudopalabras"
        ) else 0.0,
    ])


def add_context_features(vector: np.ndarray, grade: int, teacher_score: float) -> np.ndarray:
    """Rellena grade_norm (idx 24) y teacher_score_norm (idx 25)."""
    vector[24] = grade / 6.0
    vector[25] = teacher_score / 100.0
    return vector
