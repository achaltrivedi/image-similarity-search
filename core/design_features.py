"""
Design Feature Extractor — Structural/shape features for design-weighted search.

Generates a 256-dimensional vector capturing where edges and shapes exist
in an image, using a 16×16 Canny edge density grid. This vector is stored
alongside the CLIP embedding and used for design-weighted scoring.

The design vector is invariant to color — it only captures structure.
"""

import cv2
import numpy as np
from PIL import Image


DESIGN_EMBEDDING_DIM = 256  # 16×16 grid


def extract_design_features(pil_image: Image.Image) -> list[float]:
    """Extract a 256-dim design feature vector from a PIL Image.
    
    Process:
      1. Resize to 128×128 grayscale
      2. Apply Canny edge detection
      3. Divide into 16×16 grid (8px per cell)
      4. Each cell = edge pixel density (0-1)
      5. L2-normalize to unit vector

    Args:
        pil_image: PIL Image in any mode (will be converted to grayscale).

    Returns:
        List of 256 floats (unit-normalized edge density grid).
    """
    # Convert to grayscale and resize
    img = pil_image.convert("L").resize((128, 128))
    gray = np.array(img, dtype=np.uint8)

    # Canny edge detection
    edges = cv2.Canny(gray, 50, 150)

    # 16×16 grid — each cell is 8×8 pixels
    grid_size = 16
    cell_size = 128 // grid_size  # = 8
    feature_vector = []

    for row in range(grid_size):
        for col in range(grid_size):
            y_start = row * cell_size
            x_start = col * cell_size
            cell = edges[y_start:y_start + cell_size, x_start:x_start + cell_size]
            # Edge density: fraction of edge pixels in this cell
            density = float(np.count_nonzero(cell)) / (cell_size * cell_size)
            feature_vector.append(density)

    # L2-normalize to unit vector (for cosine similarity)
    arr = np.array(feature_vector, dtype=np.float32)
    norm = np.linalg.norm(arr)
    if norm > 0:
        arr = arr / norm

    return arr.tolist()
