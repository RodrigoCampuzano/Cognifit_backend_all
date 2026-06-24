from infrastructure.nlp.spacy_nlp_service import SpacyNlpService


def test_detects_rotation():
    service = SpacyNlpService()
    result = service.analyze_response("dado", "bado")
    assert "ROT" in result["error_tags"]


def test_builds_28_features():
    service = SpacyNlpService()
    analysis = service.analyze_response("nomino", "camino", item_kind="PSEUDOWORDS")
    analysis["item_kind"] = "PSEUDOWORDS"
    vector = service.build_feature_vector([analysis], grade=3, teacher_score=60)
    assert len(vector) == 28
