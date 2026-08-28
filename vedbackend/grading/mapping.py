import re


# ============================================================
# NUMBER WORDS
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
    "thirty": 30,
    "forty": 40,
    "fifty": 50,
    "sixty": 60,
    "seventy": 70,
    "eighty": 80,
    "ninety": 90,
}


# ============================================================
# TEXT CLEANING
# ============================================================

def clean_label(value):
    if value is None:
        return ""

    text = str(value).strip().lower()

    text = text.replace("：", ":")
    text = text.replace("．", ".")
    text = text.replace("–", "-")
    text = text.replace("—", "-")

    text = re.sub(r"\s+", " ", text)

    return text.strip()


# ============================================================
# NUMBER WORD PARSER
# ============================================================

def number_word_to_int(text):
    """
    Supports:

        one
        eleven
        twenty one
        thirty five
        two hundred one
        two thousand one
        2001 written as words

    """

    text = clean_label(text)

    if not text:
        return None

    if text in NUMBER_WORDS:
        return NUMBER_WORDS[text]

    tokens = text.split()

    total = 0
    current = 0

    units = {
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
        "thirty": 30,
        "forty": 40,
        "fifty": 50,
        "sixty": 60,
        "seventy": 70,
        "eighty": 80,
        "ninety": 90,
    }

    for token in tokens:

        if token in units:
            current += units[token]

        elif token == "hundred":
            if current == 0:
                current = 1

            current *= 100

        elif token == "thousand":
            if current == 0:
                current = 1

            total += current * 1000
            current = 0

        elif token == "and":
            continue

        else:
            return None

    return total + current


# ============================================================
# NORMALIZE QUESTION NUMBER
# ============================================================

def normalize_question_number(value):
    """
    Converts different handwritten/AI-detected labels
    to one exact canonical representation.

    Examples:

        1
        01
        Q1
        Q.1
        Q 1
        Question 1
        Question: 1
        Answer 1
        Ans 1
        Answer One
        Question One

            -> "1"

        11
        Q11
        Question Eleven

            -> "11"

        11a
        11 a
        11A
        11(a)
        11 (a)
        Q11a
        Q.11(a)
        Question 11 A
        Answer 11(a)
        Eleven A

            -> "11 (a)"

        2001
        Q2001
        Question 2001
        Answer 2001

            -> "2001"
    """

    text = clean_label(value)

    if not text:
        return None

    # --------------------------------------------------------
    # Normalize punctuation
    # --------------------------------------------------------

    text = re.sub(r"[,;]+$", "", text)
    text = re.sub(r"[.:]+$", "", text)
    text = text.strip()

    # --------------------------------------------------------
    # Remove prefixes
    # --------------------------------------------------------

    prefix_pattern = re.compile(
        r"^(?:"
        r"question|questions|"
        r"answer|answers|"
        r"ans|"
        r"que|"
        r"q|"
        r"no|"
        r"number"
        r")"
        r"\s*[:.]?\s*",
        re.IGNORECASE,
    )

    for _ in range(4):
        new_text = prefix_pattern.sub(
            "",
            text,
            count=1,
        ).strip()

        if new_text == text:
            break

        text = new_text

    # --------------------------------------------------------
    # Handle "eleven (a)"
    # --------------------------------------------------------

    word_subpart = re.fullmatch(
        r"(.+?)\s*[\(\[]?\s*([a-z])\s*[\)\]]?",
        text,
    )

    if word_subpart:

        possible_number = word_subpart.group(1).strip()
        letter = word_subpart.group(2).lower()

        number_value = number_word_to_int(
            possible_number
        )

        if number_value is not None:
            return f"{number_value} ({letter})"

    # --------------------------------------------------------
    # Numeric sub-question
    # --------------------------------------------------------

    match = re.fullmatch(
        r"0*(\d+)\s*[\(\[]\s*([a-z])\s*[\)\]]",
        text,
    )

    if match:

        number = int(match.group(1))
        letter = match.group(2).lower()

        return f"{number} ({letter})"

    # --------------------------------------------------------
    # 11 a
    # --------------------------------------------------------

    match = re.fullmatch(
        r"0*(\d+)\s+([a-z])",
        text,
    )

    if match:

        number = int(match.group(1))
        letter = match.group(2).lower()

        return f"{number} ({letter})"

    # --------------------------------------------------------
    # 11a
    # --------------------------------------------------------

    match = re.fullmatch(
        r"0*(\d+)([a-z])",
        text,
    )

    if match:

        number = int(match.group(1))
        letter = match.group(2).lower()

        return f"{number} ({letter})"

    # --------------------------------------------------------
    # Word number + letter
    #
    # Eleven A
    # Twenty One B
    # --------------------------------------------------------

    match = re.fullmatch(
        r"(.+?)\s+([a-z])",
        text,
    )

    if match:

        number_text = match.group(1).strip()
        letter = match.group(2).lower()

        number_value = number_word_to_int(
            number_text
        )

        if number_value is not None:
            return f"{number_value} ({letter})"

    # --------------------------------------------------------
    # Pure numeric number
    #
    # IMPORTANT:
    # 1 stays 1
    # 11 stays 11
    # 2001 stays 2001
    # --------------------------------------------------------

    match = re.fullmatch(
        r"0*(\d+)",
        text,
    )

    if match:

        return str(
            int(match.group(1))
        )

    # --------------------------------------------------------
    # Word number
    # --------------------------------------------------------

    number_value = number_word_to_int(text)

    if number_value is not None:
        return str(number_value)

    return None


# ============================================================
# BUILD QUESTION LOOKUP
# ============================================================

def build_question_lookup(questions):

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

        if normalized is None:
            continue

        lookup[normalized] = original

    return lookup


# ============================================================
# BOX CLEANING
# ============================================================

def clean_box(box):

    if not isinstance(box, dict):
        return None

    try:
        x = float(box.get("x", 0))
        y = float(box.get("y", 0))
        w = float(box.get("w", 0))
        h = float(box.get("h", 0))

    except (
        TypeError,
        ValueError,
    ):
        return None

    x = max(
        0.0,
        min(1.0, x)
    )

    y = max(
        0.0,
        min(1.0, y)
    )

    w = max(
        0.0,
        min(1.0 - x, w)
    )

    h = max(
        0.0,
        min(1.0 - y, h)
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

    if not isinstance(boxes, list):
        return []

    result = []

    for box in boxes:

        cleaned = clean_box(box)

        if cleaned:
            result.append(cleaned)

    return result


# ============================================================
# FINAL DETERMINISTIC MAPPING
# ============================================================

def build_final_mapping(
    questions,
    per_page_results,
):

    question_lookup = build_question_lookup(
        questions
    )

    # --------------------------------------------------------
    # Initialize every question
    # --------------------------------------------------------

    mapping = {}

    for question in questions:

        original = str(
            question["number"]
        ).strip()

        mapping[original] = {
            "answered": False,
            "boxes_by_page": {},
            "answer_text_by_page": {},
            "confidence_by_page": {},
            "continues_by_page": {},
        }

    unmatched = []

    # --------------------------------------------------------
    # Process answer pages
    # --------------------------------------------------------

    for page_number, result in per_page_results.items():

        if not isinstance(result, dict):
            continue

        matches = result.get(
            "matches",
            [],
        )

        if not isinstance(matches, list):
            matches = []

        for match in matches:

            if not isinstance(match, dict):
                continue

            raw_number = match.get(
                "question_number",
                "",
            )

            # =================================================
            # AI DETECTED LABEL
            # =================================================

            normalized = normalize_question_number(
                raw_number
            )

            # =================================================
            # EXACT LOOKUP
            # =================================================

            real_question = question_lookup.get(
                normalized
            )

            # =================================================
            # NO EXACT QUESTION
            # =================================================

            if real_question is None:

                unmatched.append({
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
                        "Detected answer label "
                        "does not exactly match "
                        "a question."
                    ),
                })

                continue

            # =================================================
            # CONFIDENCE
            # =================================================

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
                confidence = 0.0

            if confidence < 0.70:

                unmatched.append({
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
                    "reason": "Low mapping confidence.",
                })

                continue

            # =================================================
            # BOXES
            # =================================================

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

            # =================================================
            # ANSWER TEXT
            # =================================================

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

            # =================================================
            # CONFIDENCE
            # =================================================

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

            # =================================================
            # CONTINUATION
            # =================================================

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

            # =================================================
            # ANSWERED
            # =================================================

            mapping[
                real_question
            ][
                "answered"
            ] = True

        # ====================================================
        # UNMATCHED REGIONS FROM AI
        # ====================================================

        unmatched_regions = result.get(
            "unmatched_regions",
            [],
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

            unmatched.append({
                "page": page_number,
                **region,
                "boxes": clean_boxes(
                    region.get(
                        "boxes",
                        [],
                    )
                ),
            })

    return mapping, unmatched