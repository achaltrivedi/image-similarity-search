from core.ranking import apply_precision_ranking


def test_precision_ranking_penalizes_weak_semantic_false_positive():
    ranking = apply_precision_ranking(
        0.62,
        {
            "semantic": 0.08,
            "design": 0.76,
            "color": 0.18,
            "texture": 0.12,
        },
        {"aspect_ratio": 1.0},
        {"aspect_ratio": 1.0},
    )

    assert ranking["similarity"] < 0.62
    assert ranking["match_confidence"] in {"low", "medium"}
    assert ranking["penalties"]


def test_precision_ranking_boosts_near_duplicate_hashes():
    ranking = apply_precision_ranking(
        0.68,
        {
            "semantic": 0.62,
            "design": 0.57,
            "color": 0.55,
            "texture": 0.41,
        },
        {"aspect_ratio": 1.0, "perceptual_hash": "ffffffffffffffff"},
        {"aspect_ratio": 1.0, "perceptual_hash": "fffffffffffffffe"},
    )

    assert ranking["similarity"] > 0.68
    assert ranking["match_confidence"] == "high"
    assert ranking["boosts"]


def test_precision_ranking_penalizes_large_aspect_ratio_mismatch():
    ranking = apply_precision_ranking(
        0.55,
        {
            "semantic": 0.44,
            "design": 0.42,
            "color": 0.38,
            "texture": 0.35,
        },
        {"aspect_ratio": 3.0},
        {"aspect_ratio": 0.7},
    )

    assert ranking["similarity"] < 0.55
    assert any("proportions" in item for item in ranking["penalties"])
