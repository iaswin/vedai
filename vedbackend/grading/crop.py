import io

from PIL import Image


def crop_box(
    png_bytes: bytes,
    box: dict,
    padding: float = 0.01,
) -> bytes:
    """
    Crop a normalized bounding box from a PNG.

    A small padding is added so that handwriting near
    the edge of a detected box isn't accidentally cut.
    """

    image = Image.open(
        io.BytesIO(png_bytes)
    ).convert("RGB")

    width, height = image.size

    x = float(box["x"])
    y = float(box["y"])
    w = float(box["w"])
    h = float(box["h"])

    x1 = max(
        0.0,
        x - padding,
    )

    y1 = max(
        0.0,
        y - padding,
    )

    x2 = min(
        1.0,
        x + w + padding,
    )

    y2 = min(
        1.0,
        y + h + padding,
    )

    left = int(x1 * width)
    top = int(y1 * height)

    right = int(x2 * width)
    bottom = int(y2 * height)

    # Prevent zero-size crop.
    right = max(right, left + 1)
    bottom = max(bottom, top + 1)

    cropped = image.crop(
        (
            left,
            top,
            right,
            bottom,
        )
    )

    buffer = io.BytesIO()

    cropped.save(
        buffer,
        format="PNG",
    )

    return buffer.getvalue()


def get_answer_crops(
    question_number,
    mapping,
    answer_pages,
):
    page_lookup = {
        page["page_number"]: page
        for page in answer_pages
    }

    question = mapping.get(
        question_number
    )

    if not question:
        return []

    crops = []

    for page_num in sorted(
        question["boxes_by_page"],
        key=lambda value: int(value),
    ):

        page = page_lookup.get(
            int(page_num)
        )

        if not page:
            continue

        boxes = question[
            "boxes_by_page"
        ][page_num]

        for box in boxes:

            try:
                crop = crop_box(
                    page["png_bytes"],
                    box,
                )
            except Exception:
                continue

            crops.append(
                {
                    "page_number": int(page_num),
                    "image": crop,
                }
            )

    return crops