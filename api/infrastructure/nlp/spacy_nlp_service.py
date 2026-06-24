from __future__ import annotations

from collections import Counter
from difflib import SequenceMatcher
from statistics import mean, pstdev
from typing import Any

from application.services.risk_calculator import FEATURE_NAMES
from infrastructure.nlp.text_preprocessor import normalize_text, strip_accents, tokenize


ROTATION_PAIRS = {
    ("b", "d"),
    ("d", "b"),
    ("p", "q"),
    ("q", "p"),
    ("u", "n"),
    ("n", "u"),
    ("m", "w"),
    ("w", "m"),
}

SPANISH_EQUIV = {
    "b": "v",
    "v": "b",
    "c": "k",
    "k": "c",
    "s": "z",
    "z": "s",
    "y": "ll",
    "ll": "y",
    "g": "j",
    "j": "g",
}

KNOWN_WORDS = {
    "casa",
    "mesa",
    "silla",
    "sol",
    "luna",
    "vaso",
    "perro",
    "gato",
    "mano",
    "pato",
    "dado",
    "plato",
}


class SpacyNlpService:
    def __init__(self) -> None:
        self._nlp = None
        try:
            import spacy  # type: ignore

            self._nlp = spacy.load("es_core_news_md")
        except Exception:
            self._nlp = None

    def analyze_response(
        self,
        expected: str,
        produced: str | None,
        item_kind: str | None = None,
        response_time_ms: int | None = None,
        expected_time_ms: int = 5000,
    ) -> dict[str, Any]:
        exp = normalize_text(expected)
        prod = normalize_text(produced)
        exp_plain = strip_accents(exp)
        prod_plain = strip_accents(prod)

        codes = self._detect_codes(exp_plain, prod_plain)
        if response_time_ms and response_time_ms > expected_time_ms:
            codes.append("LEN")
        if exp and prod and exp != prod and exp_plain == prod_plain:
            codes.append("ACC")

        lexicalization = item_kind == "PSEUDOWORDS" and prod_plain in KNOWN_WORDS
        if lexicalization:
            codes.append("LEX")

        breakdown = dict(Counter(codes))
        return {
            "expected_text": exp,
            "normalized_response": prod,
            "is_correct": exp_plain == prod_plain,
            "error_tags": sorted(set(codes)),
            "edit_distance": self.edit_distance(exp_plain, prod_plain),
            "phonetic_similarity": self.phonetic_similarity(exp_plain, prod_plain),
            "ngram_overlap": self.ngram_overlap(exp_plain, prod_plain),
            "lexicalization_flag": lexicalization,
            "error_breakdown": breakdown,
        }

    def _detect_codes(self, expected: str, produced: str) -> list[str]:
        if expected == produced:
            return []
        if not produced:
            return ["OMI"]

        codes: list[str] = []
        if " " in produced and " " not in expected:
            codes.append("SEG")
        if " " not in produced and " " in expected:
            codes.append("UNI")

        if len(expected) == len(produced):
            inversions = sum(1 for a, b in zip(expected, produced, strict=False) if (a, b) in ROTATION_PAIRS)
            if inversions:
                codes.extend(["ROT"] * inversions)
            if self._is_adjacent_inversion(expected, produced):
                codes.append("INV")

        matcher = SequenceMatcher(a=expected, b=produced)
        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == "equal":
                continue
            exp_frag = expected[i1:i2]
            prod_frag = produced[j1:j2]
            if tag == "delete":
                codes.append("OMI")
            elif tag == "insert":
                codes.append("ADD")
            elif tag == "replace":
                if len(exp_frag) == len(prod_frag) == 1 and (exp_frag, prod_frag) in ROTATION_PAIRS:
                    codes.append("ROT")
                elif self._phonological_substitution(exp_frag, prod_frag):
                    codes.append("FON")
                else:
                    codes.append("SUS")
        return codes or ["SUS"]

    def _is_adjacent_inversion(self, expected: str, produced: str) -> bool:
        if len(expected) != len(produced) or len(expected) < 2:
            return False
        diffs = [i for i, (a, b) in enumerate(zip(expected, produced, strict=False)) if a != b]
        return len(diffs) == 2 and diffs[1] == diffs[0] + 1 and expected[diffs[0]] == produced[diffs[1]] and expected[diffs[1]] == produced[diffs[0]]

    def _phonological_substitution(self, expected: str, produced: str) -> bool:
        if not expected or not produced:
            return False
        if SPANISH_EQUIV.get(expected) == produced:
            return True
        return self.phonetic_similarity(expected, produced) >= 0.75

    def edit_distance(self, expected: str, produced: str) -> int:
        try:
            from rapidfuzz.distance import Levenshtein  # type: ignore

            return int(Levenshtein.distance(expected, produced))
        except Exception:
            return self._levenshtein(expected, produced)

    def phonetic_similarity(self, expected: str, produced: str) -> float:
        def sound_key(value: str) -> str:
            value = value.replace("h", "")
            value = value.replace("qu", "k").replace("c", "k").replace("z", "s")
            value = value.replace("v", "b").replace("ll", "y").replace("gue", "ge").replace("gui", "gi")
            return value

        a = sound_key(expected)
        b = sound_key(produced)
        if not a and not b:
            return 1.0
        max_len = max(len(a), len(b), 1)
        return round(1 - (self.edit_distance(a, b) / max_len), 4)

    def ngram_overlap(self, expected: str, produced: str, n: int = 2) -> float:
        def grams(value: str) -> set[str]:
            if len(value) < n:
                return {value} if value else set()
            return {value[i : i + n] for i in range(len(value) - n + 1)}

        left = grams(expected)
        right = grams(produced)
        if not left and not right:
            return 1.0
        if not left or not right:
            return 0.0
        return round(len(left & right) / len(left | right), 4)

    def build_feature_vector(self, analyses: list[dict], grade: int, teacher_score: float) -> list[float]:
        total = max(len(analyses), 1)
        counter: Counter[str] = Counter()
        for analysis in analyses:
            counter.update(analysis.get("error_breakdown", {}))

        accuracy = sum(1 for analysis in analyses if analysis.get("is_correct")) / total
        error_rate = 1 - accuracy
        pseudo = [a for a in analyses if str(a.get("item_kind", "")).upper() == "PSEUDOWORDS"]
        words = [a for a in analyses if str(a.get("item_kind", "")).upper() in {"LEXICO_VISUAL", "REAL_WORD", "REAL_WORDS"}]
        pseudo_error = self._error_rate(pseudo)
        word_error = self._error_rate(words)
        times = [float(a.get("response_time_ms") or 0) / 5000 for a in analyses if a.get("response_time_ms")]
        phon = [float(a.get("phonetic_similarity", 1)) for a in analyses]
        ngrams = [float(a.get("ngram_overlap", 1)) for a in analyses]
        dominant = max(counter.values(), default=0) / max(sum(counter.values()), 1)

        raw = {
            "OMI_rate": counter["OMI"] / total,
            "SUS_rate": counter["SUS"] / total,
            "INV_rate": counter["INV"] / total,
            "ROT_rate": counter["ROT"] / total,
            "LEX_rate": counter["LEX"] / total,
            "SEG_rate": counter["SEG"] / total,
            "UNI_rate": counter["UNI"] / total,
            "FON_rate": counter["FON"] / total,
            "ADD_rate": counter["ADD"] / total,
            "LEN_rate": counter["LEN"] / total,
            "accuracy": accuracy,
            "error_rate": error_rate,
            "pseudo_vs_word_gap": max(0.0, pseudo_error - word_error),
            "pseudo_error_rate": pseudo_error,
            "word_error_rate": word_error,
            "avg_time_norm": mean(times) if times else 0.0,
            "std_time_norm": pstdev(times) if len(times) > 1 else 0.0,
            "slow_response_rate": sum(1 for t in times if t > 1) / max(len(times), 1),
            "avg_phonetic_sim": mean(phon) if phon else 1.0,
            "avg_ngram_overlap": mean(ngrams) if ngrams else 1.0,
            "rot_sus_ratio": counter["ROT"] / max(counter["SUS"], 1),
            "lex_flag": 1.0 if counter["LEX"] else 0.0,
            "seg_uni_rate": (counter["SEG"] + counter["UNI"]) / total,
            "inv_omi_ratio": counter["INV"] / max(counter["OMI"], 1),
            "module_completion_rate_suggested": 1.0,
            "dominant_error_concentration_suggested": dominant,
            "grade_norm": max(0.0, min(1.0, grade / 6)),
            "teacher_score_norm": max(0.0, min(1.0, teacher_score / 100)),
        }
        return [round(float(raw[name]), 4) for name in FEATURE_NAMES]

    def _error_rate(self, analyses: list[dict]) -> float:
        if not analyses:
            return 0.0
        return 1 - (sum(1 for item in analyses if item.get("is_correct")) / len(analyses))

    def _levenshtein(self, a: str, b: str) -> int:
        if len(a) < len(b):
            a, b = b, a
        previous = list(range(len(b) + 1))
        for i, ca in enumerate(a, 1):
            current = [i]
            for j, cb in enumerate(b, 1):
                current.append(min(previous[j] + 1, current[j - 1] + 1, previous[j - 1] + (ca != cb)))
            previous = current
        return previous[-1]
