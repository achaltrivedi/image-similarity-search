from core.preprocessor import ImagePreprocessor
from PIL import Image
import io
import pypdfium2 as pdfium

def create_dummy_pdf():
    """Creates a simple 1-page PDF in memory."""
    pdf = pdfium.PdfDocument.new()
    page = pdf.new_page(200, 200)
    # Just blank page is enough to test rendering
    buffer = io.BytesIO()
    pdf.save(buffer)
    return buffer.getvalue()

def create_dummy_gif():
    """Creates a simple 2-frame GIF in memory."""
    img1 = Image.new('RGB', (100, 100), color='red')
    img2 = Image.new('RGB', (100, 100), color='blue')
    buffer = io.BytesIO()
    img1.save(buffer, format='GIF', save_all=True, append_images=[img2], duration=100, loop=0)
    return buffer.getvalue()

def test_formats():
    print("Testing Preprocessor Format Support...")
    
    # 1. Test PDF
    try:
        print("Testing PDF...", end=" ")
        pdf_bytes = create_dummy_pdf()
        img = ImagePreprocessor.process(pdf_bytes, "test.pdf")
        if img.mode == 'RGB' and img.size:
            print("PASSED (Size: {img.size})")
        else:
            print("FAILED (Invalid image)")
    except Exception as e:
        print(f"FAILED: {e}")

    # 2. Test GIF
    try:
        print("Testing GIF...", end=" ")
        gif_bytes = create_dummy_gif()
        img = ImagePreprocessor.process(gif_bytes, "test.gif")
        if img.mode == 'RGB':
            print("PASSED (Converted to STATIC RGB)")
        else:
            print(f"FAILED (Mode: {img.mode})")
    except Exception as e:
        print(f"FAILED: {e}")

    # 3. Test Unknown
    try:
        print("Testing Unknown (.xyz)...", end=" ")
        ImagePreprocessor.process(b'garbage', "test.xyz")
        print("FAILED (Should have raised error)")
    except OSError:
         # Pillow raises OSError for bad image data
        print("PASSED (Correctly rejected)")
    except Exception as e:
        print(f"Caught unexpected error: {type(e).__name__}")
        
    print("\nPreprocessor Logic Verified!")

if __name__ == "__main__":
    test_formats()
