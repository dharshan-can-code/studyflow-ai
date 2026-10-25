import base64
from io import BytesIO

from PIL import Image, ImageOps
from pypdf import PdfReader


IMAGE_TYPES = ["png", "jpg", "jpeg", "webp"]
MAX_IMAGE_SIDE = 1600
MAX_PDF_CHARACTERS = 20000


# ============================================================
# IMAGES
# ============================================================

def encode_image(uploaded_file):
    try:
        image = Image.open(BytesIO(uploaded_file.getvalue()))
        image.load()
        image = ImageOps.exif_transpose(image)
        image.thumbnail((MAX_IMAGE_SIDE, MAX_IMAGE_SIDE))

        has_transparency = image.mode in ("RGBA", "LA") or "transparency" in image.info
        image = image.convert("RGBA" if has_transparency else "RGB")

        buffer = BytesIO()
        image.save(buffer, format="PNG", optimize=True)
        return base64.b64encode(buffer.getvalue()).decode("utf-8")
    except (OSError, ValueError, TypeError) as error:
        raise ValueError("Please choose a valid PNG, JPG, JPEG, or WEBP image.") from error


def decode_image(image_data):
    return Image.open(BytesIO(base64.b64decode(image_data)))


# ============================================================
# PDFS
# ============================================================

def is_pdf(uploaded_file):
    return uploaded_file.name.lower().endswith(".pdf")


def pdf_text(uploaded_file):
    try:
        reader = PdfReader(BytesIO(uploaded_file.getvalue()))
        pages = [page.extract_text() or "" for page in reader.pages]
    except Exception as error:
        raise ValueError("That PDF couldn't be opened. Try a different file.") from error

    text = "\n\n".join(page.strip() for page in pages if page.strip())
    if not text:
        raise ValueError(
            "This PDF doesn't contain any readable text (it may be a scan). "
            "Try uploading a photo of it instead."
        )
    return text[:MAX_PDF_CHARACTERS]
