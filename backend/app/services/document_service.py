import io
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

MAX_FILE_BYTES  = 10 * 1024 * 1024   # 10 MB
MAX_TEXT_CHARS  = 5000                # matches ChatRequest.document_text max_length

SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".doc", ".txt", ".png", ".jpg", ".jpeg", ".webp"}


def extract_text(content: bytes, filename: str, content_type: str = "") -> tuple[str, str]:
    """
    Returns (extracted_text, method_label).
    Raises ValueError for unsupported or unreadable files.
    """
    suffix = Path(filename).suffix.lower()
    ct     = (content_type or "").lower()

    if suffix == ".pdf" or "pdf" in ct:
        return _from_pdf(content), "pypdf"

    if suffix == ".docx" or "wordprocessingml" in ct:
        return _from_docx(content), "python-docx"

    if suffix == ".doc":
        raise ValueError(
            ".doc (old Word format) is not supported — please save as .docx and re-upload."
        )

    if suffix == ".txt" or "text/plain" in ct:
        return content.decode("utf-8", errors="replace"), "plain-text"

    if suffix in (".png", ".jpg", ".jpeg", ".webp") or ct.startswith("image/"):
        return _from_image(content), "tesseract-ocr"

    raise ValueError(
        f"Unsupported file type '{suffix}'. "
        f"Supported: {', '.join(sorted(SUPPORTED_EXTENSIONS))}"
    )


# ── Extractors ────────────────────────────────────────────────────────────────

def _from_pdf(content: bytes) -> str:
    try:
        import pypdf
    except ImportError:
        raise ValueError("PDF support requires pypdf — run: pip install pypdf")

    reader = pypdf.PdfReader(io.BytesIO(content))
    if not reader.pages:
        raise ValueError("PDF has no readable pages.")

    pages = []
    for page in reader.pages:
        text = page.extract_text()
        if text and text.strip():
            pages.append(text.strip())

    if not pages:
        raise ValueError(
            "No text could be extracted from this PDF. "
            "It may be a scanned image — try uploading as PNG/JPG for OCR instead."
        )

    return "\n\n".join(pages)


def _from_docx(content: bytes) -> str:
    try:
        import docx
    except ImportError:
        raise ValueError("DOCX support requires python-docx — run: pip install python-docx")

    doc   = docx.Document(io.BytesIO(content))
    lines = [p.text for p in doc.paragraphs if p.text.strip()]
    if not lines:
        raise ValueError("No text found in this Word document.")

    return "\n".join(lines)


def _from_image(content: bytes) -> str:
    try:
        import pytesseract
        from PIL import Image
    except ImportError:
        raise ValueError(
            "Image OCR requires Pillow + pytesseract.\n"
            "Install: pip install Pillow pytesseract\n"
            "Then install Tesseract: brew install tesseract  (macOS) "
            "or apt-get install tesseract-ocr  (Linux)"
        )

    try:
        img  = Image.open(io.BytesIO(content))
        text = pytesseract.image_to_string(img)
    except Exception as e:
        raise ValueError(f"OCR failed: {e}")

    if not text.strip():
        raise ValueError(
            "No text detected in the image. "
            "Make sure the image is clear and the text is readable."
        )

    return text
