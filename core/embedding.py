import os
import numpy as np
from transformers import CLIPImageProcessor
from PIL import Image
from utils.config import MODEL_NAME, ONNX_MODEL_PATH


class ImageEmbedder:
    def __init__(self):
        import onnxruntime as ort

        if not os.path.exists(ONNX_MODEL_PATH):
            raise FileNotFoundError(
                f"ONNX model not found at {ONNX_MODEL_PATH}. "
                f"Run: python tools/export_clip_onnx.py"
            )

        # Use all available CPU cores for inference
        sess_options = ort.SessionOptions()
        sess_options.intra_op_num_threads = os.cpu_count() or 4
        sess_options.inter_op_num_threads = 2
        sess_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL

        self.session = ort.InferenceSession(
            ONNX_MODEL_PATH,
            sess_options=sess_options,
            providers=["CPUExecutionProvider"],
        )

        # CLIPImageProcessor handles resize, normalize, center-crop
        # (lighter than full CLIPProcessor — no text tokenizer loaded)
        self.processor = CLIPImageProcessor.from_pretrained(MODEL_NAME)

        print(f"ONNX model loaded: {ONNX_MODEL_PATH}")

    def embed_images(self, images):
        """
        images: list of PIL Images
        returns: normalized numpy.ndarray (N, 768)
        """
        inputs = self.processor(images=images, return_tensors="np")
        pixel_values = inputs["pixel_values"].astype(np.float32)

        # Run inference — pooler_output is the second output node
        outputs = self.session.run(None, {"pixel_values": pixel_values})
        embeddings = outputs[1]  # pooler_output: (N, 768)

        # L2-normalize for cosine similarity
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        norms = np.clip(norms, a_min=1e-8, a_max=None)
        embeddings = embeddings / norms

        return embeddings
