"""
Similarity Explainer — Post-hoc analysis of WHY images are similar.

After CLIP finds visually similar images, this module runs lightweight
OpenCV comparisons to explain the dominant similarity factor:
  - Color (HSV histogram correlation)
  - Design/Structure (Canny edge histogram)
  - Texture (grayscale variance similarity)

Each comparison returns a 0-1 score. The top aspects are returned as tags.
"""

import cv2
import numpy as np
from PIL import Image


def _pil_to_cv2(pil_image: Image.Image) -> np.ndarray:
    """Convert PIL Image (RGB) to OpenCV BGR numpy array, resized for speed."""
    img = pil_image.convert("RGB")
    img = img.resize((128, 128))  # Downsample for fast analysis
    return cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)


def _color_score(query_cv2: np.ndarray, result_cv2: np.ndarray) -> float:
    """Compare color palettes using HSV histogram correlation.
    
    HSV space separates color (Hue) from brightness, making it robust
    to lighting differences. Returns 0-1 (1 = identical palettes).
    """
    query_hsv = cv2.cvtColor(query_cv2, cv2.COLOR_BGR2HSV)
    result_hsv = cv2.cvtColor(result_cv2, cv2.COLOR_BGR2HSV)

    # Hue + Saturation histogram (ignore Value/brightness)
    hist_q = cv2.calcHist([query_hsv], [0, 1], None, [30, 32], [0, 180, 0, 256])
    hist_r = cv2.calcHist([result_hsv], [0, 1], None, [30, 32], [0, 180, 0, 256])

    cv2.normalize(hist_q, hist_q)
    cv2.normalize(hist_r, hist_r)

    score = cv2.compareHist(hist_q, hist_r, cv2.HISTCMP_CORREL)
    return max(0.0, float(score))  # Clamp to 0-1


def _structure_score(query_cv2: np.ndarray, result_cv2: np.ndarray) -> float:
    """Compare structural/design similarity using Canny edge histograms.
    
    Detects whether images share similar shapes, layouts, and line work
    regardless of color. Returns 0-1 (1 = identical structure).
    """
    query_gray = cv2.cvtColor(query_cv2, cv2.COLOR_BGR2GRAY)
    result_gray = cv2.cvtColor(result_cv2, cv2.COLOR_BGR2GRAY)

    edges_q = cv2.Canny(query_gray, 50, 150)
    edges_r = cv2.Canny(result_gray, 50, 150)

    # Compare edge density histograms
    hist_q = cv2.calcHist([edges_q], [0], None, [64], [0, 256])
    hist_r = cv2.calcHist([edges_r], [0], None, [64], [0, 256])

    cv2.normalize(hist_q, hist_q)
    cv2.normalize(hist_r, hist_r)

    score = cv2.compareHist(hist_q, hist_r, cv2.HISTCMP_CORREL)
    return max(0.0, float(score))


def _texture_score(query_cv2: np.ndarray, result_cv2: np.ndarray) -> float:
    """Compare texture similarity using grayscale histogram + variance.
    
    Captures whether images have similar patterns, grain, or smoothness.
    Returns 0-1 (1 = identical texture profile).
    """
    query_gray = cv2.cvtColor(query_cv2, cv2.COLOR_BGR2GRAY)
    result_gray = cv2.cvtColor(result_cv2, cv2.COLOR_BGR2GRAY)

    # Grayscale histogram correlation
    hist_q = cv2.calcHist([query_gray], [0], None, [64], [0, 256])
    hist_r = cv2.calcHist([result_gray], [0], None, [64], [0, 256])

    cv2.normalize(hist_q, hist_q)
    cv2.normalize(hist_r, hist_r)

    hist_corr = cv2.compareHist(hist_q, hist_r, cv2.HISTCMP_CORREL)

    # Variance similarity (penalize large variance differences)
    var_q = float(np.var(query_gray))
    var_r = float(np.var(result_gray))
    max_var = max(var_q, var_r, 1.0)
    var_sim = 1.0 - abs(var_q - var_r) / max_var

    score = 0.6 * max(0.0, hist_corr) + 0.4 * var_sim
    return max(0.0, min(1.0, score))


# Tag definitions with thresholds
_ASPECTS = [
    {"key": "color",     "label": "Color",   "icon": "🎨", "fn": _color_score,     "threshold": 0.35},
    {"key": "design",    "label": "Design",  "icon": "📐", "fn": _structure_score,  "threshold": 0.40},
    {"key": "texture",   "label": "Texture", "icon": "🔲", "fn": _texture_score,    "threshold": 0.40},
]


def explain_similarity(query_image: Image.Image, result_image: Image.Image) -> list[dict]:
    """Analyze why two images are similar.
    
    Args:
        query_image: The uploaded search query (PIL Image, RGB).
        result_image: A search result image (PIL Image, RGB).
    
    Returns:
        List of similarity tags sorted by score, e.g.:
        [{"label": "Color", "icon": "🎨", "score": 0.87}, ...]
        Only tags above their threshold are included.
    """
    query_cv2 = _pil_to_cv2(query_image)
    result_cv2 = _pil_to_cv2(result_image)

    tags = []
    for aspect in _ASPECTS:
        try:
            score = aspect["fn"](query_cv2, result_cv2)
            if score >= aspect["threshold"]:
                # Map score to priority level
                if score >= 0.70:
                    priority = "High"
                elif score >= 0.50:
                    priority = "Medium"
                else:
                    priority = "Low"
                
                tags.append({
                    "label": aspect["label"],
                    "icon": aspect["icon"],
                    "score": round(score, 2),
                    "priority": priority
                })
        except Exception:
            continue  # Skip if analysis fails for this aspect

    # Sort by score descending, keep top 2
    tags.sort(key=lambda t: t["score"], reverse=True)
    return tags[:2]
