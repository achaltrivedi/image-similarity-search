import cv2
import numpy as np
from PIL import Image

COLOR_EMBEDDING_DIM = 256  # 16x16 Hue-Saturation histogram
TEXTURE_EMBEDDING_DIM = 64 # 64-bin Grayscale histogram

def extract_color_features(pil_image: Image.Image) -> list[float]:
    """
    Extracts a 256-dimensional color feature vector using HSV histograms.
    Returns an L2-normalized vector for direct cosine similarity search.
    """
    img = pil_image.convert("RGB").resize((128, 128))
    cv2_img = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
    hsv_img = cv2.cvtColor(cv2_img, cv2.COLOR_BGR2HSV)

    # 16 bins for Hue (0-180), 16 bins for Saturation (0-256) -> 256 dimensions
    hist = cv2.calcHist([hsv_img], [0, 1], None, [16, 16], [0, 180, 0, 256]).flatten()
    
    # Mean centering + L2 normalize transforms Cosine Similarity mathematically into Pearson Correlation
    hist = hist - np.mean(hist)
    norm = np.linalg.norm(hist)
    if norm > 0:
        hist = hist / norm
        
    return hist.tolist()

def extract_texture_features(pil_image: Image.Image) -> list[float]:
    """
    Extracts a 64-dimensional texture feature vector using grayscale histograms.
    Returns an L2-normalized vector for direct cosine similarity search.
    """
    img = pil_image.convert("L").resize((128, 128))
    cv2_gray = np.array(img, dtype=np.uint8)

    # 64 bins for grayscale intensity (0-256)
    hist = cv2.calcHist([cv2_gray], [0], None, [64], [0, 256]).flatten()
    
    # Mean centering + L2 normalize into Pearson Correlation equivalent
    hist = hist - np.mean(hist)
    norm = np.linalg.norm(hist)
    if norm > 0:
        hist = hist / norm
        
    return hist.tolist()
