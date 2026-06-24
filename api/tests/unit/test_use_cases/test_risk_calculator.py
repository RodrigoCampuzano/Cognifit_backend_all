from application.services.risk_calculator import FEATURE_NAMES, RiskCalculator


def test_classifies_phonological_gap():
    values = {name: 0.0 for name in FEATURE_NAMES}
    values.update({"error_rate": 0.45, "pseudo_error_rate": 0.65, "word_error_rate": 0.20, "pseudo_vs_word_gap": 0.45, "teacher_score_norm": 0.70})
    vector = [values[name] for name in FEATURE_NAMES]
    result = RiskCalculator().classify(vector, {"FON": 5, "INV": 3})
    assert result.subtype == "PHONOLOGICAL"
    assert result.risk_probability > 0.30
