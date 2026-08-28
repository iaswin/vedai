import io

import fitz

from PIL import Image


def file_to_images(
    file_bytes,
    filename,
    dpi=150,
):
    """
    Convert PDF/image into PNG pages.

    Coordinates used by Gemini are normalized
    against these generated PNG dimensions.
    """

    filename = filename.lower()

    if filename.endswith(".pdf"):
        doc = fitz.open(
            stream=file_bytes,
            filetype="pdf",
        )

        pages = []

        for i, page in enumerate(doc):
            pix = page.get_pixmap(
                dpi=dpi,
                alpha=False,
            )

            png_bytes = pix.tobytes(
                "png"
            )

            pages.append(
                {
                    "page_number": i + 1,
                    "width": pix.width,
                    "height": pix.height,
                    "png_bytes": png_bytes,
                }
            )

        doc.close()

        return pages

    image = Image.open(
        io.BytesIO(file_bytes)
    ).convert("RGB")

    buffer = io.BytesIO()

    image.save(
        buffer,
        format="PNG",
    )

    return [
        {
            "page_number": 1,
            "width": image.width,
            "height": image.height,
            "png_bytes": buffer.getvalue(),
        }
    ]