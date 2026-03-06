import os

MODEL_NAME = "openai/clip-vit-base-patch32"
IMAGE_DIR = "images"

IMAGE_EXTENSIONS = (".png", ".jpg", ".jpeg")

EMBEDDING_DIM = 768  # CLIP ViT-Base produces 768-dimensional vectors

TOP_K = 5

# Path to the exported ONNX model file
ONNX_MODEL_PATH = os.path.join(
    os.path.dirname(__file__), "..", "models", "clip-vit-base-patch32.onnx"
)
