
MODEL_NAME = "openai/clip-vit-base-patch32"
IMAGE_DIR = "images"

DEVICE = "cuda"  # fallback handled in code

IMAGE_EXTENSIONS = (".png", ".jpg", ".jpeg")

EMBEDDING_DIM = 768  # because we are using CLIPVisionModel

TOP_K = 5
