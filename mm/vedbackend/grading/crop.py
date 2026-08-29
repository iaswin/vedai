import io

from PIL import Image


def crop_box(
    png_bytes: bytes,
    box: dict,
    padding: float = 0.01,
) -> bytes:
    """
    Crop a normalized bounding box from a PNG.
    """

    if not png_bytes:
        raise ValueError(
            "Empty PNG bytes."
        )

    image = Image.open(
        io.BytesIO(png_bytes)
    )

    image.load()

    image = image.convert(
        "RGB"
    )

    width, height = image.size

    try:

        x = float(
            box["x"]
        )

        y = float(
            box["y"]
        )

        w = float(
            box["w"]
        )

        h = float(
            box["h"]
        )

    except (
        KeyError,
        TypeError,
        ValueError,
    ) as exc:

        raise ValueError(
            f"Invalid bounding box: {box}"
        ) from exc

    # --------------------------------------------------------
    # Clamp
    # --------------------------------------------------------

    x = max(
        0.0,
        min(
            1.0,
            x,
        ),
    )

    y = max(
        0.0,
        min(
            1.0,
            y,
        ),
    )

    w = max(
        0.0,
        min(
            1.0 - x,
            w,
        ),
    )

    h = max(
        0.0,
        min(
            1.0 - y,
            h,
        ),
    )

    if w <= 0 or h <= 0:

        raise ValueError(
            f"Invalid bounding box dimensions: {box}"
        )

    # --------------------------------------------------------
    # Padding
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # Convert to pixels
    # --------------------------------------------------------

    left = int(
        x1 * width
    )

    top = int(
        y1 * height
    )

    right = int(
        x2 * width
    )

    bottom = int(
        y2 * height
    )

    # --------------------------------------------------------
    # Prevent zero-size crop
    # --------------------------------------------------------

    right = max(
        right,
        left + 1,
    )

    bottom = max(
        bottom,
        top + 1,
    )

    right = min(
        right,
        width,
    )

    bottom = min(
        bottom,
        height,
    )

    if right <= left:
        raise ValueError(
            "Crop width is zero."
        )

    if bottom <= top:
        raise ValueError(
            "Crop height is zero."
        )

    # --------------------------------------------------------
    # Crop
    # --------------------------------------------------------

    cropped = image.crop(
        (
            left,
            top,
            right,
            bottom,
        )
    )

    # --------------------------------------------------------
    # Return PNG
    # --------------------------------------------------------

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
    """
    Return cropped answer images for a question.
    """

    page_lookup = {
        int(page["page_number"]): page
        for page in answer_pages
    }

    question = mapping.get(
        question_number
    )

    if not question:
        return []

    crops = []

    boxes_by_page = question.get(
        "boxes_by_page",
        {}
    )

    for page_num in sorted(
        boxes_by_page,
        key=lambda value: int(value),
    ):

        page_number = int(
            page_num
        )

        page = page_lookup.get(
            page_number
        )

        if not page:
            continue

        boxes = boxes_by_page[
            page_num
        ]

        for box in boxes:

            crop = crop_box(
                page["png_bytes"],
                box,
            )

            crops.append({
                "page_number": page_number,
                "image": crop,
            })

    return crops
