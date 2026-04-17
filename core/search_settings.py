DEFAULT_SEARCH_SETTINGS = {
    "default_results_per_page": 50,
    "similarity_threshold": 0.0,
    "weights": {
        "semantic": 0.55,
        "design": 0.20,
        "color": 0.15,
        "texture": 0.10,
    },
    "enable_sub_part_localization": True,
    "bounding_box_effect": "scanner",
}

BOUNDING_BOX_EFFECTS = {"scanner", "simple", "off"}
WEIGHT_KEYS = ("semantic", "design", "color", "texture")


def _coerce_int(value, fallback):
    try:
        return int(value)
    except (TypeError, ValueError):
        return fallback


def _coerce_float(value, fallback):
    try:
        return float(value)
    except (TypeError, ValueError):
        return fallback


def _coerce_bool(value, fallback):
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"1", "true", "yes", "on"}:
            return True
        if lowered in {"0", "false", "no", "off"}:
            return False
    return fallback


def normalize_search_settings(payload: dict | None) -> dict:
    payload = payload or {}
    defaults = DEFAULT_SEARCH_SETTINGS

    page_size = _coerce_int(
        payload.get("default_results_per_page"),
        defaults["default_results_per_page"],
    )
    page_size = max(1, min(100, page_size))

    threshold = _coerce_float(
        payload.get("similarity_threshold"),
        defaults["similarity_threshold"],
    )
    threshold = max(0.0, min(1.0, threshold))

    raw_weights = payload.get("weights") or {}
    normalized_weights = {}
    weight_total = 0.0
    for key in WEIGHT_KEYS:
        fallback_weight = defaults["weights"][key]
        weight = _coerce_float(raw_weights.get(key), fallback_weight)
        weight = max(0.0, weight)
        normalized_weights[key] = weight
        weight_total += weight

    if weight_total <= 0:
        normalized_weights = defaults["weights"].copy()
    else:
        normalized_weights = {
            key: value / weight_total for key, value in normalized_weights.items()
        }

    localization_enabled = _coerce_bool(
        payload.get("enable_sub_part_localization"),
        defaults["enable_sub_part_localization"],
    )

    effect = str(payload.get("bounding_box_effect") or defaults["bounding_box_effect"]).lower()
    if effect not in BOUNDING_BOX_EFFECTS:
        effect = defaults["bounding_box_effect"]

    return {
        "default_results_per_page": page_size,
        "similarity_threshold": threshold,
        "weights": normalized_weights,
        "enable_sub_part_localization": localization_enabled,
        "bounding_box_effect": effect,
    }


def build_effective_search_settings(
    saved_settings: dict | None,
    overrides: dict | None = None,
) -> dict:
    saved = normalize_search_settings(saved_settings)
    overrides = overrides or {}
    merged = {
        **saved,
        **{k: v for k, v in overrides.items() if k != "weights"},
        "weights": {
            **saved["weights"],
            **(overrides.get("weights") or {}),
        },
    }
    return normalize_search_settings(merged)


def compute_weighted_similarity(similarity_scores: dict, weights: dict | None) -> float:
    weights = normalize_search_settings({"weights": weights or {}})["weights"]
    weighted_total = 0.0
    total_weight = 0.0

    for key in WEIGHT_KEYS:
        score = similarity_scores.get(key)
        weight = weights.get(key, 0.0)
        if score is None or weight <= 0:
            continue
        weighted_total += score * weight
        total_weight += weight

    if total_weight <= 0:
        semantic_score = similarity_scores.get("semantic")
        return float(semantic_score) if semantic_score is not None else 0.0

    return weighted_total / total_weight
