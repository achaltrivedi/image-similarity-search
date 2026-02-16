import torch
from transformers import CLIPVisionModel, CLIPProcessor
from PIL import Image
from utils.config import MODEL_NAME, DEVICE

class ImageEmbedder:
    def __init__(self):
        self.device = DEVICE if torch.cuda.is_available() else "cpu"

        self.model = CLIPVisionModel.from_pretrained(
            MODEL_NAME
        ).to(self.device)

        self.processor = CLIPProcessor.from_pretrained(MODEL_NAME)

        self.model.eval()

    def embed_images(self, images):
        """
        images: list of PIL Images
        returns: normalized torch.Tensor (N, D)
        """
        inputs = self.processor(images=images, return_tensors="pt")
        inputs = {k: v.to(self.device) for k, v in inputs.items()}

        with torch.no_grad():
            outputs = self.model(**inputs)
            embeddings = outputs.pooler_output

        # Normalize for cosine similarity
        embeddings = embeddings / embeddings.norm(dim=1, keepdim=True)

        return embeddings
