from application.services.screening_service import ScreeningService


def test_teacher_score_selects_full_battery():
    items = [{"item_code": f"q{i}", "weight": 12.5, "tags": []} for i in range(8)]
    answers = [{"item_code": f"q{i}", "value": "Frecuente"} for i in range(8)]
    result = ScreeningService().calculate_teacher_score(items, answers)
    assert result["score"] == 100
    assert result["battery_mode"] == "FULL"
    assert len(result["enabled_module_codes"]) == 9


def test_teacher_score_selects_quick_screening():
    items = [{"item_code": f"q{i}", "weight": 12.5, "tags": []} for i in range(8)]
    answers = [{"item_code": f"q{i}", "value": "Nunca"} for i in range(8)]
    result = ScreeningService().calculate_teacher_score(items, answers)
    assert result["score"] == 0
    assert result["battery_mode"] == "QUICK"
    assert result["enabled_module_codes"] == [
        "M02_PHONOLOGICAL_AWARENESS",
        "M04_REAL_WORDS",
        "M08_RAPID_NAMING",
    ]
