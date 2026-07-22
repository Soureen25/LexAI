"""
doc_preview.py
──────────────
Renders an uploaded document (PDF or TXT) as inline preview images/text so
the user never has to reopen the original file to see what they uploaded.

Handles two very different kinds of PDF pages:
  • normal (vector/text) pages       → rendered at a fixed comfortable DPI
  • scanned pages (one big embedded
    image stretched across the page) → rendered at (at least) the image's
                                        OWN native resolution, so we aren't
                                        blindly upscaling a low-res scan and
                                        introducing extra interpolation blur.
    If the scan's native resolution is still below our target DPI, a light
    unsharp-mask pass is applied to keep text edges legible.

Usage:
    from doc_preview import render_pdf_pages, ocr_image_text, MAX_PREVIEW_PAGES

    pages, total_pages, scanned_flags = render_pdf_pages(file_bytes)
    if scanned_flags[0]:
        text = ocr_image_text(pages[0])   # on-demand, only when the user asks for it
"""

import io
import fitz  # PyMuPDF
import pytesseract
from PIL import Image, ImageFilter

MAX_PREVIEW_PAGES = 25   # safety cap so a 300-page contract doesn't hang the UI
PREVIEW_DPI       = 150  # target resolution for normal (non-scanned) pages
MAX_RENDER_DPI    = 300  # hard ceiling, protects memory if a scan's metadata is bogus


def _dominant_image_native_dpi(doc: "fitz.Document", page: "fitz.Page"):
    """
    If a page is essentially a full-page scanned image, return that image's
    native resolution in DPI (relative to the page's physical size).
    Returns None for normal text/vector pages, or pages with no images.
    """
    images = page.get_images(full=True)
    if not images:
        return None

    largest = None
    for img in images:
        xref = img[0]
        try:
            pix = fitz.Pixmap(doc, xref)
            area = pix.width * pix.height
            if largest is None or area > largest[0]:
                largest = (area, pix.width, pix.height)
        except Exception:
            continue

    if not largest:
        return None

    _, img_w, img_h = largest
    page_w_in = page.rect.width / 72.0
    page_h_in = page.rect.height / 72.0
    if page_w_in <= 0 or page_h_in <= 0:
        return None

    return min(img_w / page_w_in, img_h / page_h_in)


def render_pdf_pages(file_bytes: bytes, dpi: int = PREVIEW_DPI, max_pages: int = MAX_PREVIEW_PAGES):
    """
    Rasterize a PDF's pages into PNG images for inline preview.

    Args:
        file_bytes: raw PDF bytes
        dpi: target render resolution for normal pages (higher = sharper, slower)
        max_pages: cap on number of pages rendered

    Returns:
        (list_of_png_bytes, total_page_count, list_of_is_scanned_flags)
    """
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    total_pages = doc.page_count

    images = []
    scanned_flags = []
    for i, page in enumerate(doc):
        if i >= max_pages:
            break

        native_dpi = _dominant_image_native_dpi(doc, page)
        is_scanned = native_dpi is not None
        scanned_flags.append(is_scanned)

        # Never render below our normal target, but for scans render at *least*
        # at the scan's own native resolution so we don't upscale unnecessarily.
        target_dpi = max(dpi, native_dpi) if is_scanned else dpi
        target_dpi = min(target_dpi, MAX_RENDER_DPI)

        zoom = target_dpi / 72.0
        pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom))
        png_bytes = pix.tobytes("png")

        # If we still had to upscale a low-res scan past its native resolution,
        # counteract the resulting interpolation blur with a light sharpen pass.
        if is_scanned and native_dpi < dpi:
            img = Image.open(io.BytesIO(png_bytes))
            img = img.filter(ImageFilter.UnsharpMask(radius=1.4, percent=130, threshold=2))
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            png_bytes = buf.getvalue()

        images.append(png_bytes)

    doc.close()
    return images, total_pages, scanned_flags


def ocr_image_text(png_bytes: bytes) -> str:
    """
    Run OCR on a rendered page image and return the extracted text.

    This does NOT improve image sharpness — it sidesteps the problem by
    giving the user clean, legible text pulled from the (possibly blurry)
    scan, which is the practical fix when a scan's native resolution is
    too low for image processing alone to fix.
    """
    img = Image.open(io.BytesIO(png_bytes))
    return pytesseract.image_to_string(img).strip()