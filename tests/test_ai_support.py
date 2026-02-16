
import os
import sys
from pathlib import Path

# Ensure project root is importable
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Create a dummy PDF content (minimal PDF header)
# This is a valid minimal PDF 1.4 file
DUMMY_PDF_BYTES = (
    b"%PDF-1.4\n"
    b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
    b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
    b"3 0 obj<</Type/Page/MediaBox[0 0 595 842]/Parent 2 0 R/Resources<<>>>>endobj\n"
    b"xref\n"
    b"0 4\n"
    b"0000000000 65535 f\n"
    b"0000000010 00000 n\n"
    b"0000000053 00000 n\n"
    b"0000000102 00000 n\n"
    b"trailer<</Size 4/Root 1 0 R>>\n"
    b"startxref\n"
    b"178\n"
    b"%%EOF\n"
)

from core.preprocessor import ImagePreprocessor

def test_ai_support():
    print("🧪 Testing .ai Support...")
    
    # 1. Test .ai extension routing
    filename = "test_image.ai"
    
    try:
        # We pass the dummy PDF bytes. If the preprocessor treats it as a PDF (due to .ai extension),
        # pypdfium2 should be able to parse this minimal PDF and render it (or at least try).
        # We mainly want to ensure it DOES NOT go to PIL.Image.open() which would fail or treat it as binary.
        
        image = ImagePreprocessor.process(DUMMY_PDF_BYTES, filename)
        
        print(f"✅ Successfully processed {filename}")
        print(f"   Image Size: {image.size}")
        print(f"   Image Mode: {image.mode}")
        return True
        
    except Exception as e:
        print(f"❌ Failed to process {filename}: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_ai_support()
    sys.exit(0 if success else 1)
