import traceback
import re
from .ai import (
    extract_questions,
    extract_answer_mapping,
    grade_answer,
)

from .storage import (
    get_assessment,
    save_assessment,
)


# ============================================================
# PROGRESS HELPER
# ============================================================

def update_progress(
    session_id,
    percent,
    stage,
    status="processing",
):
    """
    Update assessment processing state.
    """

    data = get_assessment(session_id)

    if not data:
        return

    data["status"] = status

    data["progress"] = {
        "percent": int(percent),
        "stage": stage,
    }

    save_assessment(
        session_id,
        data,
    )


# ============================================================
# PIPELINE
# ============================================================

def run_pipeline(session_id):
    """
    Complete AI pipeline:

        Question paper
              ↓
        Question extraction
              ↓
        Answer label detection
              ↓
        Deterministic answer mapping
              ↓
        Grading
              ↓
        Final result

    This function runs in a background thread.
    """

    try:

        # ----------------------------------------------------
        # LOAD SESSION
        # ----------------------------------------------------

        assessment = get_assessment(
            session_id
        )

        if not assessment:
            return

        question_pages = assessment.get(
            "qp_pages",
            [],
        )

        answer_pages = assessment.get(
            "ans_pages",
            [],
        )

        if not question_pages:
            raise ValueError(
                "No question paper pages found."
            )

        if not answer_pages:
            raise ValueError(
                "No answer sheet pages found."
            )

        # ----------------------------------------------------
        # START
        # ----------------------------------------------------

        update_progress(
            session_id,
            5,
            "Preparing documents",
        )

        # ====================================================
        # 1. EXTRACT QUESTIONS
        # ====================================================

        update_progress(
            session_id,
            10,
            "Extracting questions",
        )

        questions = extract_questions(
            question_pages
        )

        if not questions:
            raise ValueError(
                "No questions could be extracted from the question paper."
            )

        # ----------------------------------------------------
        # Ensure stable IDs/index
        # ----------------------------------------------------

        for index, question in enumerate(
            questions,
            start=1,
        ):
            question["index"] = index

        update_progress(
            session_id,
            30,
            f"Extracted {len(questions)} questions",
        )

        # ====================================================
        # 2. ANSWER EXTRACTION + LABEL DETECTION
        # ====================================================

        per_page_results = {}

        total_answer_pages = len(
            answer_pages
        )

        for index, page in enumerate(
            answer_pages,
            start=1,
        ):

            percent = (
                30
                + int(
                    (index / total_answer_pages)
                    * 30
                )
            )

            update_progress(
                session_id,
                percent,
                (
                    f"Analyzing answer page "
                    f"{index} of "
                    f"{total_answer_pages}"
                ),
            )

            result = extract_answer_mapping(
                page=page,
                questions=questions,
                total_pages=total_answer_pages,
            )

            per_page_results[
                page["page_number"]
            ] = result

        # ====================================================
        # 3. DETERMINISTIC MAPPING
        # ====================================================

        update_progress(
            session_id,
            62,
            "Mapping answers to questions",
        )

        mapping, unmatched = build_final_mapping(
            questions=questions,
            per_page_results=per_page_results,
        )

        # ====================================================
        # 4. BUILD ANSWERED QUESTIONS
        # ====================================================

        update_progress(
            session_id,
            68,
            "Preparing answer regions",
        )

        results = []

        for question in questions:

            number = str(
                question["number"]
            ).strip()

            mapped = mapping.get(
                number,
                {},
            )

            answered = bool(
                mapped.get(
                    "answered",
                    False,
                )
            )

            boxes_by_page = mapped.get(
                "boxes_by_page",
                {},
            )

            answer_text_by_page = mapped.get(
                "answer_text_by_page",
                {},
            )

            confidence_by_page = mapped.get(
                "confidence_by_page",
                {},
            )

            continues_by_page = mapped.get(
                "continues_by_page",
                {},
            )

            # ------------------------------------------------
            # Flatten answer regions
            # ------------------------------------------------

            answer_regions = []

            for page_number, boxes in (
                boxes_by_page.items()
            ):

                for box in boxes:

                    answer_regions.append(
                        {
                            "page": int(
                                page_number
                            ),
                            "x": box["x"],
                            "y": box["y"],
                            "w": box["w"],
                            "h": box["h"],
                        }
                    )

            # ------------------------------------------------
            # Combine answer text
            # ------------------------------------------------

            answer_text_parts = []

            for page_number in sorted(
                answer_text_by_page,
                key=lambda value: int(value),
            ):

                text = str(
                    answer_text_by_page[
                        page_number
                    ]
                ).strip()

                if text:
                    answer_text_parts.append(
                        text
                    )

            answer_text = "\n".join(
                answer_text_parts
            ).strip()

            # ------------------------------------------------
            # Highest confidence
            # ------------------------------------------------

            confidence_values = []

            for value in (
                confidence_by_page.values()
            ):
                try:
                    confidence_values.append(
                        float(value)
                    )
                except (
                    TypeError,
                    ValueError,
                ):
                    pass

            confidence = (
                max(confidence_values)
                if confidence_values
                else 0
            )

            # ------------------------------------------------
            # Continuation
            # ------------------------------------------------

            continues = any(
                bool(value)
                for value in (
                    continues_by_page.values()
                )
            )

            # ------------------------------------------------
            # Result object
            # ------------------------------------------------

            result = {
                "number": number,

                "text": question[
                    "text"
                ],

                "max_marks": question[
                    "max_marks"
                ],

                "answered": answered,

                "answer_text": answer_text,

                "confidence": confidence,

                "continues": continues,

                "answer_regions": answer_regions,

                "marks": 0,

                "feedback": "",
            }

            results.append(
                result
            )

        # ====================================================
        # 5. GRADE ANSWERS
        # ====================================================

        answered_results = [
            result
            for result in results
            if result["answered"]
            and result["answer_regions"]
        ]

        total_to_grade = len(
            answered_results
        )

        for index, result in enumerate(
            answered_results,
            start=1,
        ):

            if total_to_grade:

                percent = (
                    70
                    + int(
                        (
                            index
                            / total_to_grade
                        )
                        * 25
                    )
                )

            else:

                percent = 95

            update_progress(
                session_id,
                percent,
                (
                    f"Grading answer "
                    f"{index} of "
                    f"{total_to_grade}"
                ),
            )

            crop_images = []

            # ----------------------------------------------
            # Crop every mapped region
            # ----------------------------------------------

            for region in (
                result["answer_regions"]
            ):

                page_number = int(
                    region["page"]
                )

                page = next(
                    (
                        page
                        for page in answer_pages
                        if int(
                            page.get(
                                "page_number",
                                -1,
                            )
                        )
                        == page_number
                    ),
                    None,
                )

                if not page:
                    continue

                crop = crop_page_region(
                    page["png_bytes"],
                    region,
                )

                if crop:
                    crop_images.append(
                        crop
                    )

            # ----------------------------------------------
            # Grade
            # ----------------------------------------------

            if crop_images:

                grade = grade_answer(
                    question={
                        "text": result["text"],
                        "max_marks": result[
                            "max_marks"
                        ],
                    },
                    crop_png_list=crop_images,
                )

                result["marks"] = grade.get(
                    "marks",
                    0,
                )

                result["feedback"] = grade.get(
                    "feedback",
                    "",
                )

            else:

                result["marks"] = 0

                result["feedback"] = (
                    "No answer region found."
                )

        # ====================================================
        # 6. FINAL SUMMARY
        # ====================================================

        update_progress(
            session_id,
            97,
            "Preparing final result",
        )

        answered_count = sum(
            1
            for result in results
            if result["answered"]
        )

        unanswered_count = (
            len(results)
            - answered_count
        )

        total_marks = sum(
            float(
                result.get(
                    "marks",
                    0,
                )
            )
            for result in results
        )

        maximum_marks = sum(
            float(
                result.get(
                    "max_marks",
                    0,
                )
            )
            for result in results
        )

        # ====================================================
        # FINAL RESPONSE
        # ====================================================

        final_result = {
            "questions": results,

            "unmatched": unmatched,

            "summary": {
                "total_questions": len(
                    results
                ),

                "answered": answered_count,

                "unanswered": unanswered_count,

                "total_marks": total_marks,

                "maximum_marks": maximum_marks,
            },
        }

        # ====================================================
        # SAVE
        # ====================================================

        assessment = get_assessment(
            session_id
        )

        if not assessment:
            return

        assessment["status"] = "completed"

        assessment["progress"] = {
            "percent": 100,
            "stage": "completed",
        }

        assessment["result"] = final_result

        assessment.pop(
            "error",
            None,
        )

        save_assessment(
            session_id,
            assessment,
        )

    except Exception as exc:

        traceback.print_exc()

        assessment = get_assessment(
            session_id
        )

        if assessment:

            assessment["status"] = "failed"

            assessment["progress"] = {
                "percent": 100,
                "stage": "failed",
            }

            assessment["error"] = str(
                exc
            )

            save_assessment(
                session_id,
                assessment,
            )


# ============================================================
# IMAGE CROPPING
# ============================================================

def crop_page_region(
    png_bytes,
    region,
):
    """
    Crop a normalized answer region from a PNG page.

    region:
        {
            "x": 0.1,
            "y": 0.2,
            "w": 0.8,
            "h": 0.2
        }

    Returns PNG bytes.
    """

    try:

        from PIL import Image
        from io import BytesIO

        image = Image.open(
            BytesIO(png_bytes)
        ).convert("RGB")

        width, height = image.size

        x = float(
            region.get(
                "x",
                0,
            )
        )

        y = float(
            region.get(
                "y",
                0,
            )
        )

        w = float(
            region.get(
                "w",
                0,
            )
        )

        h = float(
            region.get(
                "h",
                0,
            )
        )

        # ----------------------------------------------
        # Clamp
        # ----------------------------------------------

        x = max(
            0,
            min(
                1,
                x,
            ),
        )

        y = max(
            0,
            min(
                1,
                y,
            ),
        )

        w = max(
            0,
            min(
                1 - x,
                w,
            ),
        )

        h = max(
            0,
            min(
                1 - y,
                h,
            ),
        )

        if w <= 0 or h <= 0:
            return None

        left = int(
            x * width
        )

        top = int(
            y * height
        )

        right = int(
            (x + w) * width
        )

        bottom = int(
            (y + h) * height
        )

        # ----------------------------------------------
        # Small padding for grading
        # ----------------------------------------------

        padding_x = int(
            width * 0.01
        )

        padding_y = int(
            height * 0.01
        )

        left = max(
            0,
            left - padding_x,
        )

        top = max(
            0,
            top - padding_y,
        )

        right = min(
            width,
            right + padding_x,
        )

        bottom = min(
            height,
            bottom + padding_y,
        )

        if right <= left:
            return None

        if bottom <= top:
            return None

        cropped = image.crop(
            (
                left,
                top,
                right,
                bottom,
            )
        )

        output = BytesIO()

        cropped.save(
            output,
            format="PNG",
        )

        return output.getvalue()

    except Exception:

        traceback.print_exc()

        return None


# ============================================================
# NORMALIZATION
# ============================================================

NUMBER_WORDS = {
    "zero": 0,
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "eleven": 11,
    "twelve": 12,
    "thirteen": 13,
    "fourteen": 14,
    "fifteen": 15,
    "sixteen": 16,
    "seventeen": 17,
    "eighteen": 18,
    "nineteen": 19,
    "twenty": 20,
    "twenty one": 21,
    "twenty two": 22,
    "twenty three": 23,
    "twenty four": 24,
    "twenty five": 25,
    "twenty six": 26,
    "twenty seven": 27,
    "twenty eight": 28,
    "twenty nine": 29,
    "thirty": 30,
    "thirty one": 31,
    "thirty two": 32,
    "thirty three": 33,
    "thirty four": 34,
    "thirty five": 35,
    "thirty six": 36,
    "thirty seven": 37,
    "thirty eight": 38,
    "thirty nine": 39,
    "forty": 40,
    "fifty": 50,
    "sixty": 60,
    "seventy": 70,
    "eighty": 80,
    "ninety": 90,
}


def normalize_question_number(value):
    """
    Convert the AI-detected handwritten reference into
    the canonical question number.

    Examples:

        1
        Q1
        Q.1
        Q 1
        Question 1
        Answer 1
        Ans. One

            -> 1

        11a
        11 a
        11(a)
        Q11(a)
        Question 11 A
        Answer 11(a)
        Eleven A

            -> 11 (a)

        2001
        Q2001
        Question 2001

            -> 2001
    """

    if value is None:
        return None

    text = str(
        value
    ).strip().lower()

    if not text:
        return None

    # Unicode spaces
    text = re.sub(
        r"\s+",
        " ",
        text,
    )

    # Normalize punctuation
    text = text.replace(
        "：",
        ":",
    )

    text = text.replace(
        "．",
        ".",
    )

    # Remove prefixes
    prefix = re.compile(
        r"^(?:"
        r"question|questions|"
        r"answer|answers|"
        r"ans|"
        r"q|"
        r"que|"
        r"no|"
        r"number"
        r")"
        r"\s*[:.]?\s*",
        re.IGNORECASE,
    )

    for _ in range(3):

        new_text = prefix.sub(
            "",
            text,
            count=1,
        ).strip()

        if new_text == text:
            break

        text = new_text

    # Remove final punctuation
    text = re.sub(
        r"[.:]+$",
        "",
        text,
    ).strip()

    # --------------------------------------------------------
    # 11(a)
    # --------------------------------------------------------

    match = re.fullmatch(
        r"0*(\d+)\s*\(\s*([a-z])\s*\)",
        text,
    )

    if match:

        number = int(
            match.group(1)
        )

        letter = match.group(2)

        return f"{number} ({letter})"

    # --------------------------------------------------------
    # 11 a
    # --------------------------------------------------------

    match = re.fullmatch(
        r"0*(\d+)\s+([a-z])",
        text,
    )

    if match:

        number = int(
            match.group(1)
        )

        letter = match.group(2)

        return f"{number} ({letter})"

    # --------------------------------------------------------
    # 11a
    # --------------------------------------------------------

    match = re.fullmatch(
        r"0*(\d+)([a-z])",
        text,
    )

    if match:

        number = int(
            match.group(1)
        )

        letter = match.group(2)

        return f"{number} ({letter})"

    # --------------------------------------------------------
    # Pure number
    # --------------------------------------------------------

    match = re.fullmatch(
        r"0*(\d+)",
        text,
    )

    if match:

        return str(
            int(
                match.group(1)
            )
        )

    # --------------------------------------------------------
    # Number words
    # --------------------------------------------------------

    if text in NUMBER_WORDS:

        return str(
            NUMBER_WORDS[text]
        )

    return None


# ============================================================
# BUILD QUESTION LOOKUP
# ============================================================

def build_question_lookup(
    questions,
):
    """
    Question paper:

        1
        2
        10
        11
        11 (a)
        11 (b)
        11 (c)
        2001

    becomes:

        {
            "1": "1",
            "2": "2",
            "10": "10",
            "11": "11",
            "11 (a)": "11 (a)",
            "11 (b)": "11 (b)",
            "11 (c)": "11 (c)",
            "2001": "2001"
        }
    """

    lookup = {}

    for question in questions:

        original = str(
            question.get(
                "number",
                "",
            )
        ).strip()

        if not original:
            continue

        normalized = normalize_question_number(
            original
        )

        if normalized is not None:

            lookup[
                normalized
            ] = original

    return lookup


# ============================================================
# BOX CLEANING
# ============================================================

def clean_box(box):

    if not isinstance(
        box,
        dict,
    ):
        return None

    try:

        x = float(
            box.get(
                "x",
                0,
            )
        )

        y = float(
            box.get(
                "y",
                0,
            )
        )

        w = float(
            box.get(
                "w",
                0,
            )
        )

        h = float(
            box.get(
                "h",
                0,
            )
        )

    except (
        TypeError,
        ValueError,
    ):

        return None

    x = max(
        0,
        min(
            1,
            x,
        ),
    )

    y = max(
        0,
        min(
            1,
            y,
        ),
    )

    w = max(
        0,
        min(
            1 - x,
            w,
        ),
    )

    h = max(
        0,
        min(
            1 - y,
            h,
        ),
    )

    if w <= 0 or h <= 0:
        return None

    return {
        "x": x,
        "y": y,
        "w": w,
        "h": h,
    }


def clean_boxes(boxes):

    if not isinstance(
        boxes,
        list,
    ):
        return []

    cleaned = []

    for box in boxes:

        item = clean_box(
            box
        )

        if item:
            cleaned.append(
                item
            )

    return cleaned


# ============================================================
# FINAL DETERMINISTIC MAPPING
# ============================================================

def build_final_mapping(
    questions,
    per_page_results,
):
    """
    IMPORTANT:

    Gemini detects what the student wrote.

    Python performs the final exact mapping.

    Therefore:

        Q1
        Question 1
        Answer 1
        Ans One
        One

            -> question 1

        Q11
        Question Eleven
        Answer 11

            -> question 11

        Q11a
        Q11(a)
        Question 11 A
        Answer 11(a)
        Eleven A

            -> question 11 (a)

        Q11b
        11B
        11 (b)

            -> question 11 (b)

        Q2001
        Answer 2001
        2001

            -> question 2001

    1 NEVER becomes 10 or 11.
    11 NEVER becomes 11(a).
    11(a) NEVER becomes 11(b).

    Answer order is irrelevant.
    """

    question_lookup = build_question_lookup(
        questions
    )

    mapping = {}

    # --------------------------------------------------------
    # Initialize every question
    # --------------------------------------------------------

    for question in questions:

        number = str(
            question["number"]
        ).strip()

        mapping[number] = {
            "answered": False,
            "boxes_by_page": {},
            "answer_text_by_page": {},
            "confidence_by_page": {},
            "continues_by_page": {},
        }

    unmatched = []

    # --------------------------------------------------------
    # Process every answer page
    # --------------------------------------------------------

    for page_number, page_result in (
        per_page_results.items()
    ):

        if not isinstance(
            page_result,
            dict,
        ):
            continue

        matches = page_result.get(
            "matches",
            [],
        )

        if not isinstance(
            matches,
            list,
        ):
            matches = []

        # ====================================================
        # MATCHES
        # ====================================================

        for match in matches:

            if not isinstance(
                match,
                dict,
            ):
                continue

            raw_number = match.get(
                "question_number"
            )

            normalized = normalize_question_number(
                raw_number
            )

            # -----------------------------------------------
            # EXACT lookup
            # -----------------------------------------------

            real_question = (
                question_lookup.get(
                    normalized
                )
            )

            if real_question is None:

                unmatched.append(
                    {
                        "page": page_number,
                        "detected_number": raw_number,
                        "normalized_number": normalized,
                        "boxes": clean_boxes(
                            match.get(
                                "boxes",
                                [],
                            )
                        ),
                        "text_preview": str(
                            match.get(
                                "answer_text",
                                "",
                            )
                        ),
                        "reason": (
                            "Question number does not "
                            "exist in the question paper."
                        ),
                    }
                )

                continue

            # -----------------------------------------------
            # Confidence
            # -----------------------------------------------

            try:

                confidence = float(
                    match.get(
                        "confidence",
                        0,
                    )
                )

            except (
                TypeError,
                ValueError,
            ):

                confidence = 0

            # -----------------------------------------------
            # We trust clear AI label detection
            # -----------------------------------------------

            if confidence < 0.70:

                unmatched.append(
                    {
                        "page": page_number,
                        "detected_number": raw_number,
                        "normalized_number": normalized,
                        "boxes": clean_boxes(
                            match.get(
                                "boxes",
                                [],
                            )
                        ),
                        "text_preview": str(
                            match.get(
                                "answer_text",
                                "",
                            )
                        ),
                        "confidence": confidence,
                        "reason": (
                            "Question label confidence "
                            "is too low."
                        ),
                    }
                )

                continue

            # -----------------------------------------------
            # Boxes
            # -----------------------------------------------

            boxes = clean_boxes(
                match.get(
                    "boxes",
                    [],
                )
            )

            current_boxes = (
                mapping[
                    real_question
                ][
                    "boxes_by_page"
                ].get(
                    page_number,
                    [],
                )
            )

            mapping[
                real_question
            ][
                "boxes_by_page"
            ][
                page_number
            ] = (
                current_boxes
                + boxes
            )

            # -----------------------------------------------
            # Text
            # -----------------------------------------------

            answer_text = str(
                match.get(
                    "answer_text",
                    "",
                )
            ).strip()

            old_text = (
                mapping[
                    real_question
                ][
                    "answer_text_by_page"
                ].get(
                    page_number,
                    "",
                )
            )

            if old_text and answer_text:

                answer_text = (
                    old_text
                    + "\n"
                    + answer_text
                )

            elif old_text:

                answer_text = old_text

            mapping[
                real_question
            ][
                "answer_text_by_page"
            ][
                page_number
            ] = answer_text

            # -----------------------------------------------
            # Confidence
            # -----------------------------------------------

            old_confidence = (
                mapping[
                    real_question
                ][
                    "confidence_by_page"
                ].get(
                    page_number,
                    0,
                )
            )

            mapping[
                real_question
            ][
                "confidence_by_page"
            ][
                page_number
            ] = max(
                old_confidence,
                confidence,
            )

            # -----------------------------------------------
            # Continuation
            # -----------------------------------------------

            mapping[
                real_question
            ][
                "continues_by_page"
            ][
                page_number
            ] = bool(
                match.get(
                    "continues",
                    False,
                )
            )

            # -----------------------------------------------
            # Mark answered
            # -----------------------------------------------

            mapping[
                real_question
            ][
                "answered"
            ] = True

        # ====================================================
        # UNMATCHED REGIONS
        # ====================================================

        unmatched_regions = (
            page_result.get(
                "unmatched_regions",
                [],
            )
        )

        if not isinstance(
            unmatched_regions,
            list,
        ):
            unmatched_regions = []

        for region in unmatched_regions:

            if not isinstance(
                region,
                dict,
            ):
                continue

            unmatched.append(
                {
                    "page": page_number,
                    **region,
                    "boxes": clean_boxes(
                        region.get(
                            "boxes",
                            [],
                        )
                    ),
                }
            )

    return (
        mapping,
        unmatched,
    )