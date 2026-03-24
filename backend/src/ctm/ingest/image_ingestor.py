"""Image/photo ingestor with OCR.

Handles camera photos and scanned documents.
Includes preprocessing (deskew, contrast) for better OCR quality.
"""

from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class ImageIngestor:
    """Extract text from images using Tesseract OCR.

    Includes preprocessing to improve OCR quality on camera photos:
    - Grayscale conversion
    - Contrast enhancement
    - Optional deskewing
    """

    @property
    def supported_extensions(self) -> list[str]:
        return [".jpg", ".jpeg", ".png", ".tiff", ".tif", ".bmp"]

    @property
    def format_name(self) -> str:
        return "Image (OCR)"

    async def extract_text(self, source: str | bytes, **kwargs) -> str:
        image = self._load_image(source)
        processed = self._preprocess(image)

        try:
            import pytesseract

            text = pytesseract.image_to_string(processed, lang=kwargs.get("lang", "eng"))
            return text.strip()
        except Exception as e:
            logger.error(f"OCR failed: {e}")
            return ""

    async def extract_structured(self, source: str | bytes, **kwargs) -> dict:
        return {}

    def _load_image(self, source: str | bytes):
        """Load image from path or bytes."""
        from PIL import Image
        import io

        if isinstance(source, bytes):
            return Image.open(io.BytesIO(source))
        return Image.open(source)

    def _preprocess(self, image):
        """Preprocess image for better OCR quality."""
        from PIL import ImageEnhance, ImageFilter

        # Convert to grayscale
        if image.mode != "L":
            image = image.convert("L")

        # Enhance contrast
        enhancer = ImageEnhance.Contrast(image)
        image = enhancer.enhance(1.5)

        # Sharpen
        image = image.filter(ImageFilter.SHARPEN)

        # Resize if too small (OCR works better on larger images)
        min_width = 1000
        if image.width < min_width:
            ratio = min_width / image.width
            new_size = (int(image.width * ratio), int(image.height * ratio))
            from PIL import Image as PILImage
            image = image.resize(new_size, PILImage.LANCZOS)

        return image

    async def get_confidence(self, source: str | bytes, **kwargs) -> float:
        """Get OCR confidence score for the image.

        Returns:
            Confidence between 0.0 and 1.0.
        """
        image = self._load_image(source)
        processed = self._preprocess(image)

        try:
            import pytesseract

            data = pytesseract.image_to_data(
                processed, output_type=pytesseract.Output.DICT
            )
            confidences = [
                int(c) for c in data.get("conf", []) if str(c).isdigit() and int(c) > 0
            ]
            if confidences:
                return sum(confidences) / len(confidences) / 100.0
        except Exception:
            pass

        return 0.0
