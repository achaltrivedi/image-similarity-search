from __future__ import annotations

from core.image_metadata import aspect_ratio_delta, hash_distance


def score_confidence(score: float) -> str:
    if score >= 0.72:
        return "high"
    if score >= 0.48:
        return "medium"
    return "low"


def build_rank_reason(scores: dict, penalties: list[str], boosts: list[str]) -> str:
    scored = [
        ("semantic", "semantic meaning", scores.get("semantic")),
        ("design", "layout", scores.get("design")),
        ("color", "color palette", scores.get("color")),
        ("texture", "texture", scores.get("texture")),
    ]
    strong = [label for _, label, value in scored if value is not None and value >= 0.55]
    moderate = [label for _, label, value in scored if value is not None and 0.38 <= value < 0.55]

    if boosts:
        return boosts[0]
    if len(strong) >= 2:
        return f"Strong {' and '.join(strong[:2])} match"
    if strong:
        return f"Strong {strong[0]} match"
    if moderate:
        return f"Moderate {moderate[0]} match"
    if penalties:
        return "Lower confidence because " + penalties[0]
    return "Weak visual similarity"


def apply_precision_ranking(
    base_similarity: float,
    scores: dict,
    result_metadata: dict | None,
    query_metadata: dict | None,
) -> dict:
    result_metadata = result_metadata or {}
    query_metadata = query_metadata or {}
    adjusted = float(base_similarity)
    penalties: list[str] = []
    boosts: list[str] = []

    semantic = scores.get("semantic") or 0.0
    feature_values = [
        value for key, value in scores.items()
        if key != "semantic" and value is not None
    ]

    if semantic < 0.12 and adjusted > 0.25:
        adjusted -= 0.15
        penalties.append("semantic meaning is very weak")
    elif semantic < 0.22 and adjusted > 0.35:
        adjusted -= 0.10
        penalties.append("semantic meaning is weaker than the visual match")

    ratio_delta = aspect_ratio_delta(
        query_metadata.get("aspect_ratio"),
        result_metadata.get("aspect_ratio"),
    )
    if ratio_delta is not None:
        if ratio_delta > 1.1:
            adjusted -= 0.12
            penalties.append("image proportions are very different")
        elif ratio_delta > 0.7:
            adjusted -= 0.07
            penalties.append("image proportions differ")

    if feature_values:
        strongest_feature = max(feature_values)
        weaker_average = sum(feature_values) / len(feature_values)
        if strongest_feature >= 0.70 and semantic < 0.25 and weaker_average < 0.42:
            adjusted -= 0.08
            penalties.append("only one visual signal is strong")

    phash_distance = hash_distance(
        query_metadata.get("perceptual_hash"),
        result_metadata.get("perceptual_hash"),
    )
    if phash_distance is not None:
        if phash_distance <= 4:
            adjusted += 0.08
            boosts.append("Near-duplicate visual fingerprint")
        elif phash_distance <= 10:
            adjusted += 0.04
            boosts.append("Similar visual fingerprint")

    if semantic >= 0.45 and len([v for v in feature_values if v >= 0.45]) >= 2:
        adjusted += 0.04
        boosts.append("Multiple visual signals agree")

    adjusted = max(0.0, min(1.0, adjusted))
    return {
        "similarity": adjusted,
        "base_similarity": float(base_similarity),
        "match_confidence": score_confidence(adjusted),
        "rank_reason": build_rank_reason(scores, penalties, boosts),
        "penalties": penalties,
        "boosts": boosts,
    }
