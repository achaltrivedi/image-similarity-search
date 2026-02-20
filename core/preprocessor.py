import io
from PIL import Image, ImageOps
import pypdfium2 as pdfium

class ImagePreprocessor:
    """
    Handles conversion of various file formats (PDF, GIF, TIFF, etc.)
    into standard static RGB images for embedding.
    """

    @staticmethod
    def process(file_bytes: bytes, filename: str) -> Image.Image:
        """
        Detects file type based on extension and processes accordingly.
        Returns a clean PIL.Image (RGB).
        """
        ext = filename.split(".")[-1].lower() if "." in filename else ""
        
        try:
            if ext in ("pdf", "ai"):
                return ImagePreprocessor._process_pdf(file_bytes)
            
            # Standard Image formats (JPG, PNG, GIF, BMP, TIFF, WEBP)
            return ImagePreprocessor._process_image(file_bytes)
            
        except Exception as e:
            print(f"⚠️ Preprocessing failed for {filename}: {e}")
            raise e

    @staticmethod
    def _process_pdf(file_bytes: bytes) -> Image.Image:
        """Renders the first page of a PDF to an image."""
        pdf = None
        try:
            pdf = pdfium.PdfDocument(file_bytes)
            # Render first page (index 0)
            page = pdf[0]
            # Render at 300 DPI for good quality
            bitmap = page.render(scale=4.16)  # 72dpi * 4.16 ~= 300dpi
            pil_image = bitmap.to_pil()
            
            # handle transparency by compositing on white
            if pil_image.mode in ('RGBA', 'LA') or (pil_image.mode == 'P' and 'transparency' in pil_image.info):
                alpha = pil_image.convert('RGBA').split()[-1]
                bg = Image.new("RGB", pil_image.size, (255, 255, 255))
                bg.paste(pil_image, mask=alpha)
                return bg

            return pil_image.convert("RGB")
        except Exception as e:
            print(f"❌ PDF processing error: {e}")
            raise ValueError(f"Could not render PDF: {e}")
        finally:
            if pdf:
                pdf.close()

    @staticmethod
    def _process_image(file_bytes: bytes) -> Image.Image:
        """Handles standard images, including animated GIFs."""
        img = Image.open(io.BytesIO(file_bytes))
        
        # Handle Animation (GIF/WebP) -> Take first frame
        if getattr(img, "is_animated", False):
            img.seek(0)
        
        # Convert to RGB (removes alpha channel, handles Indexed color)
        # Some PNGs with transparency need a white background
        if img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info):
            # Create white background
            alpha = img.convert('RGBA').split()[-1]
            bg = Image.new("RGB", img.size, (255, 255, 255))
            bg.paste(img, mask=alpha)
            return bg
            
        return img.convert("RGB")

    @staticmethod
    def create_thumbnail(image: Image.Image, max_size: int = 512) -> bytes:
        """
        Creates a thumbnail from a PIL Image.
        Returns PNG bytes, or empty bytes on failure.
        """
        try:
            # Copy to avoid modifying original
            thumb = image.copy()
            thumb.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
            
            output = io.BytesIO()
            thumb.save(output, format="PNG", optimize=True)
            png_bytes = output.getvalue()
            
            # Validate: PNG must start with magic bytes and be at least 100 bytes
            if len(png_bytes) < 100 or not png_bytes.startswith(b'\x89PNG'):
                print(f"⚠️ Thumbnail produced invalid PNG ({len(png_bytes)} bytes)")
                return b""
            
            return png_bytes
        except Exception as e:
            print(f"⚠️ Thumbnail generation failed: {e}")
            return b""

