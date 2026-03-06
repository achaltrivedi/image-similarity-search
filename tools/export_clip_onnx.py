"""
One-time script to export the CLIP Vision model from PyTorch to ONNX format.

Usage:
    python tools/export_clip_onnx.py

This will create:
    models/clip-vit-base-patch32.onnx
"""

import os
import sys
import numpy as np

# Ensure project root is on the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

def export():
    import torch
    from transformers import CLIPVisionModel, CLIPProcessor
    from utils.config import MODEL_NAME

    output_dir = os.path.join(os.path.dirname(__file__), "..", "models")
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "clip-vit-base-patch32.onnx")

    print(f"Loading PyTorch model: {MODEL_NAME}")
    model = CLIPVisionModel.from_pretrained(MODEL_NAME, use_safetensors=True)
    model.eval()

    processor = CLIPProcessor.from_pretrained(MODEL_NAME)

    # Create a dummy input (224x224 RGB image)
    from PIL import Image
    dummy_image = Image.new("RGB", (224, 224), color=(128, 128, 128))
    inputs = processor(images=dummy_image, return_tensors="pt")
    pixel_values = inputs["pixel_values"]

    print(f"Input shape: {pixel_values.shape}")  # [1, 3, 224, 224]

    # Export to ONNX
    print(f"Exporting to ONNX: {output_path}")
    torch.onnx.export(
        model,
        (pixel_values,),
        output_path,
        input_names=["pixel_values"],
        output_names=["last_hidden_state", "pooler_output"],
        dynamic_axes={
            "pixel_values": {0: "batch_size"},
            "last_hidden_state": {0: "batch_size"},
            "pooler_output": {0: "batch_size"},
        },
        opset_version=18,
        do_constant_folding=True,
        dynamo=False,  # Use legacy exporter to embed weights in a single .onnx file
    )

    # Verify the exported model
    import onnxruntime as ort

    session = ort.InferenceSession(output_path)
    ort_inputs = {"pixel_values": pixel_values.numpy()}
    ort_outputs = session.run(None, ort_inputs)

    # Compare PyTorch vs ONNX outputs
    with torch.no_grad():
        pt_outputs = model(pixel_values)
        pt_pooler = pt_outputs.pooler_output.numpy()

    onnx_pooler = ort_outputs[1]

    max_diff = np.abs(pt_pooler - onnx_pooler).max()
    print(f"\nVerification:")
    print(f"  PyTorch output shape:  {pt_pooler.shape}")
    print(f"  ONNX output shape:    {onnx_pooler.shape}")
    print(f"  Max absolute diff:    {max_diff:.8f}")

    if max_diff < 1e-4:
        print("\n✅ Export successful! Outputs match within tolerance.")
    else:
        print(f"\n⚠️  Outputs differ by {max_diff:.6f} — may affect search ranking slightly.")

    file_size_mb = os.path.getsize(output_path) / (1024 * 1024)
    print(f"\nONNX model saved: {output_path} ({file_size_mb:.1f} MB)")


if __name__ == "__main__":
    export()
