import io

import fitz

from PIL import Image, UnidentifiedImageError


# ============================================================
# IMAGE VALIDATION
# ============================================================

SUPPORTED_IMAGE_FORMATS = {
    "JPEG",
    "PNG",
    "WEBP",
    "BMP",
    "TIFF",
    "GIF",
}


def _image_to_png_page(image, page_number=1):
    """
    Convert a PIL image into the standard page structure
    used by the rest of the application.
    """

    # Force complete decoding while the source is still open.
    image.load()

    # Handle palette, grayscale, RGBA, CMYK, etc.
    image = image.convert("RGB")

    buffer = io.BytesIO()

    image.save(
        buffer,
        format="PNG",
    )

    png_bytes = buffer.getvalue()

    if not png_bytes:
        raise ValueError(
            "Image conversion produced empty PNG data."
        )

    return {
        "page_number": page_number,
        "width": image.width,
        "height": image.height,
        "png_bytes": png_bytes,
    }


# ============================================================
# PDF
# ============================================================

def _pdf_to_images(file_bytes, dpi=150):
    """
    Convert every PDF page into PNG.
    """

    if not file_bytes:
        raise ValueError(
            "Uploaded PDF is empty."
        )

    try:
        doc = fitz.open(
            stream=file_bytes,
            filetype="pdf",
        )
    except Exception as exc:
        raise ValueError(
            f"Could not open PDF: {exc}"
        ) from exc

    try:

        if len(doc) == 0:
            raise ValueError(
                "PDF contains no pages."
            )

        pages = []

        for index, page in enumerate(
            doc,
            start=1,
        ):

            try:

                pix = page.get_pixmap(
                    dpi=dpi,
                    alpha=False,
                )

                png_bytes = pix.tobytes(
                    "png"
                )

                if not png_bytes:
                    raise ValueError(
                        "PDF page produced empty PNG."
                    )

                pages.append({
                    "page_number": index,
                    "width": pix.width,
                    "height": pix.height,
                    "png_bytes": png_bytes,
                })

            except Exception as exc:

                raise ValueError(
                    f"Could not convert PDF page "
                    f"{index}: {exc}"
                ) from exc

        return pages

    finally:
        doc.close()


# ============================================================
# NORMAL IMAGE
# ============================================================

def _image_file_to_images(
    file_bytes,
    filename,
):
    """
    Convert a normal uploaded image into one PNG page.
    """

    if not file_bytes:
        raise ValueError(
            "Uploaded image is empty."
        )

    try:

        image = Image.open(
            io.BytesIO(file_bytes)
        )

        # Validate that PIL can actually decode it.
        image.verify()

    except UnidentifiedImageError as exc:

        raise ValueError(
            f"'{filename}' is not a valid image file."
        ) from exc

    except Exception as exc:

        raise ValueError(
            f"Could not read image "
            f"'{filename}': {exc}"
        ) from exc

    # IMPORTANT:
    # verify() invalidates the image object.
    # Open it again before calling load()/convert().
    try:

        image = Image.open(
            io.BytesIO(file_bytes)
        )

        image.load()

    except Exception as exc:

        raise ValueError(
            f"Could not decode image "
            f"'{filename}': {exc}"
        ) from exc

    image_format = (
        image.format or ""
    ).upper()

    if image_format not in SUPPORTED_IMAGE_FORMATS:

        raise ValueError(
            f"Unsupported image format: "
            f"{image_format or 'unknown'}"
        )

    return [
        _image_to_png_page(
            image,
            page_number=1,
        )
    ]


# ============================================================
# MAIN FILE CONVERTER
# ============================================================

def file_to_images(
    file_bytes,
    filename,
    dpi=150,
):
    """
    Convert an uploaded PDF or image into PNG pages.

    Supported:

        PDF
        JPG
        JPEG
        PNG
        WEBP
        BMP
        TIFF
        GIF

    Every returned page has:

        {
            "page_number": int,
            "width": int,
            "height": int,
            "png_bytes": bytes,
        }

    The rest of the application can therefore treat
    PDF pages and uploaded images identically.
    """

    if not file_bytes:
        raise ValueError(
            "Uploaded file is empty."
        )

    filename = (
        filename or ""
    ).strip()

    lower_filename = filename.lower()

    # ========================================================
    # PDF
    # ========================================================

    if lower_filename.endswith(".pdf"):

        return _pdf_to_images(
            file_bytes=file_bytes,
            dpi=dpi,
        )

    # ========================================================
    # IMAGE
    # ========================================================

    return _image_file_to_images(
        file_bytes=file_bytes,
        filename=filename,
    )
