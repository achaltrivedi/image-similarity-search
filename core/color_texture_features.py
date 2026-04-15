import cv2
import numpy as np
from PIL import Image

COLOR_EMBEDDING_DIM = 256  # 4x4 Grid * 16 bins
TEXTURE_EMBEDDING_DIM = 64 # 8x8 Grid * 1 metric (variance)

def extract_color_features(pil_image: Image.Image) -> list[float]:
    """
    Extracts a 256-dimensional spatial color feature vector.
    Divides the image into a 4x4 grid. Extracts a 16-bin (8 Hue x 2 Sat) histogram per region.
    Returns an L2-normalized vector for direct cosine similarity search.
    """
    img = pil_image.convert("RGB").resize((128, 128))
    cv2_img = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
    hsv_img = cv2.cvtColor(cv2_img, cv2.COLOR_BGR2HSV)

    grid_size = 4
    cell_size = 128 // grid_size  # 32
    feature_vector = []
    
    for row in range(grid_size):
        for col in range(grid_size):
            y_start = row * cell_size
            x_start = col * cell_size
            cell = hsv_img[y_start:y_start+cell_size, x_start:x_start+cell_size]
            
            # 8 bins Hue (0-180), 2 bins Saturation (0-256)
            hist = cv2.calcHist([cell], [0, 1], None, [8, 2], [0, 180, 0, 256]).flatten()
            feature_vector.extend(hist.tolist())

    arr = np.array(feature_vector, dtype=np.float32)
    # L2 normalize so cosine similarity measures directional match (color layout)
    # Do NOT mean-center: subtracting the mean collapses all color spatial vectors toward the same centroid
    norm = np.linalg.norm(arr)
    if norm > 0:
        arr = arr / norm
        
    return arr.tolist()

def extract_texture_features(pil_image: Image.Image) -> list[float]:
    """
    Extracts a 64-dimensional texture feature vector using spatial high-frequency energy.
    Divides the image into an 8x8 grid. Calculates the pixel variance (contrast/energy) per region.
    Returns an L2-normalized vector for direct cosine similarity search.
    """
    img = pil_image.convert("L").resize((128, 128))
    gray = np.array(img, dtype=np.float32)

    grid_size = 8
    cell_size = 128 // grid_size  # 16
    feature_vector = []
    
    for row in range(grid_size):
        for col in range(grid_size):
            y_start = row * cell_size
            x_start = col * cell_size
            cell = gray[y_start:y_start+cell_size, x_start:x_start+cell_size]
            
            # Local variance represents texture energy/roughness
            variance = np.var(cell)
            feature_vector.append(variance)

    arr = np.array(feature_vector, dtype=np.float32)
    # L2 normalize to unit vector for cosine similarity
    # Do NOT mean-center: texture variance values must retain their relative magnitudes
    norm = np.linalg.norm(arr)
    if norm > 0:
        arr = arr / norm
        
    return arr.tolist()
