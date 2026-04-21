import math

import cv2
import numpy as np
from PIL import Image


def _hex_color(rgb: tuple[int, int, int]) -> str:
    return "#{:02x}{:02x}{:02x}".format(*rgb)


def _dominant_colors(image: Image.Image, count: int = 4) -> list[str]:
    thumb = image.convert("RGB").resize((64, 64))
    quantized = thumb.quantize(colors=count, method=Image.Quantize.MEDIANCUT)
    palette = quantized.getpalette() or []
    colors = quantized.getcolors(maxcolors=64 * 64) or []
    colors.sort(reverse=True)

    dominant = []
    for _, palette_index in colors[:count]:
        start = palette_index * 3
        if start + 2 >= len(palette):
            continue
        dominant.append(_hex_color(tuple(palette[start:start + 3])))
    return dominant


def _visual_complexity(image: Image.Image) -> float:
    gray = np.array(image.convert("L").resize((128, 128)), dtype=np.uint8)
    edges = cv2.Canny(gray, 50, 150)
    return round(float(np.count_nonzero(edges)) / float(edges.size), 4)


def _perceptual_hash(image: Image.Image) -> str:
    gray = image.convert("L").resize((9, 8), Image.Resampling.LANCZOS)
    pixels = np.array(gray, dtype=np.int16)
    diff = pixels[:, 1:] > pixels[:, :-1]
    value = 0
    for bit in diff.flatten():
        value = (value << 1) | int(bit)
    return f"{value:016x}"


def extract_image_metadata(
    image: Image.Image,
    object_key: str | None = None,
    file_size: int | None = None,
) -> dict:
    width, height = image.size
    file_type = None
    if object_key and "." in object_key:
        file_type = object_key.rsplit(".", 1)[-1].lower()

    return {
        "file_size": file_size,
        "width": width,
        "height": height,
        "aspect_ratio": round(width / max(height, 1), 4),
        "file_type": file_type,
        "dominant_colors": _dominant_colors(image),
        "visual_complexity": _visual_complexity(image),
        "perceptual_hash": _perceptual_hash(image),
    }


def hash_distance(left: str | None, right: str | None) -> int | None:
    if not left or not right:
        return None
    try:
        return (int(left, 16) ^ int(right, 16)).bit_count()
    except ValueError:
        return None


def aspect_ratio_delta(left: float | None, right: float | None) -> float | None:
    if not left or not right or left <= 0 or right <= 0:
        return None
    return abs(math.log(left / right))
