from PIL import Image

from core.image_metadata import extract_image_metadata, hash_distance


def test_extract_image_metadata_returns_precision_ranking_fields():
    image = Image.new("RGB", (120, 60), color="red")

    metadata = extract_image_metadata(image, "folder/test.png", 1234)

    assert metadata["file_size"] == 1234
    assert metadata["width"] == 120
    assert metadata["height"] == 60
    assert metadata["aspect_ratio"] == 2.0
    assert metadata["file_type"] == "png"
    assert metadata["dominant_colors"]
    assert len(metadata["perceptual_hash"]) == 16
    assert 0 <= metadata["visual_complexity"] <= 1


def test_hash_distance_counts_changed_bits():
    assert hash_distance("ffffffffffffffff", "fffffffffffffffe") == 1
