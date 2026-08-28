import json
import re

from django.conf import settings
from google import genai
from google.genai import types


# ============================================================
# GEMINI
# ============================================================

MODEL = "gemini-3.5-flash"

client = genai.Client(
    api_key=settings.GEMINI_API_KEY
)


# ============================================================
# JSON PARSER
# ============================================================

def parse_json(text):

    if not text:
        raise ValueError(
            "Empty Gemini response"
        )

    text = text.strip()

    # Remove ```json
    text = re.sub(
        r"^```(?:json)?\s*",
        "",
        text,
        flags=re.IGNORECASE,
    )

    # Remove ```
    text = re.sub(
        r"\s*```$",
        "",
        text,
    )

    text = text.strip()

    # Normal JSON
    try:
        return json.loads(text)

    except json.JSONDecodeError:
        pass

    # Try extracting JSON object
    start = text.find("{")
    end = text.rfind("}")

    if start >= 0 and end > start:

        try:
            return json.loads(
                text[start:end + 1]
            )

        except json.JSONDecodeError:
            pass

    raise ValueError(
        f"Invalid Gemini JSON:\n{text[:2000]}"
    )


# ============================================================
# IMAGE
# ============================================================

def image_part(png_bytes):

    return types.Part.from_bytes(
        data=png_bytes,
        mime_type="image/png",
    )


# ============================================================
# QUESTION EXTRACTION
# ============================================================

QUESTION_PROMPT = r"""
You are an expert examination paper parser.

Analyze ALL supplied pages.

Extract EVERY actual question.

RULES:

1. Preserve printed order.
2. Do not skip questions.
3. Do not invent questions.
4. Preserve the printed question number.
5. Subquestions are separate questions.
6. 11(a), 11(b), and 11(c) MUST be separate.
7. Do not confuse marks with question numbers.
8. Include complete visible question text.
9. If marks are visible, extract them.
10. If marks cannot be determined, use 0.

IMPORTANT:

Do not merge subquestions.

For example:

11.
(a) Explain photosynthesis.
(b) Explain respiration.
(c) Explain transpiration.

Must become:

11 (a)
11 (b)
11 (c)

Return ONLY JSON.

{
  "questions": [
    {
      "number": "1",
      "text": "What is photosynthesis?",
      "max_marks": 2
    }
  ]
}
"""


def extract_questions(pages):

    contents = []

    for page in pages:

        contents.append(
            image_part(
                page["png_bytes"]
            )
        )

    contents.append(
        QUESTION_PROMPT
    )

    response = client.models.generate_content(
        model=MODEL,
        contents=contents,
        config=types.GenerateContentConfig(
            temperature=0,
            response_mime_type="application/json",
        ),
    )

    data = parse_json(
        response.text
    )

    questions = []

    for item in data.get(
        "questions",
        [],
    ):

        number = str(
            item.get(
                "number",
                "",
            )
        ).strip()

        text = str(
            item.get(
                "text",
                "",
            )
        ).strip()

        if not number or not text:
            continue

        try:

            marks = float(
                item.get(
                    "max_marks",
                    0,
                )
            )

        except (
            ValueError,
            TypeError,
        ):

            marks = 0

        questions.append(
            {
                "number": number,
                "text": text,
                "max_marks": marks,
            }
        )

    return questions


# ============================================================
# ANSWER DETECTION
# ============================================================

ANSWER_PROMPT = r"""
You are an expert handwritten examination answer-sheet analyzer.

Analyze ONE page of a student's handwritten answer sheet.

Your job is ONLY to detect answer blocks and READ THE QUESTION
REFERENCE written by the student.

Python will perform the final mapping.

DO NOT map answers yourself.

DO NOT use answer position.

DO NOT assume sequential order.

============================================================
QUESTION REFERENCES
============================================================

These mean question 1:

1
Q1
Q.1
Q 1
Question 1
Question: 1
Answer 1
Answer: 1
Ans 1
Ans. 1
One
Question One
Answer One

============================================================
SUBQUESTIONS
============================================================

These mean 11(a):

11a
11A
11 a
11 A
11(a)
11 (a)
11. (a)
Q11a
Q11(a)
Q.11(a)
Question 11(a)
Question 11 A
Answer 11 A
Ans 11(a)
Eleven A
Eleven (a)
Question Eleven A

These mean 11(b):

11b
11B
11 b
11 B
11(b)
11 (b)
Q11b
Q11(b)
Question 11 B
Answer 11 B
Eleven B

These mean 11(c):

11c
11C
11 c
11 C
11(c)
11 (c)
Q11c
Q11(c)
Question 11 C
Answer 11 C
Eleven C

IMPORTANT:

11 is NOT 11(a).

11(a) is NOT 11(b).

11(b) is NOT 11(c).

============================================================
LARGE NUMBERS
============================================================

Read the COMPLETE number.

Examples:

1
10
11
20
100
200
1000
2001

If the student writes:

2001

return:

"2001"

NEVER shorten it.

Do not turn 2001 into:

2
20
201
1

============================================================
OUT OF ORDER
============================================================

Answers may occur in ANY ORDER.

Example:

Answer 5
Answer 2
Answer 11 B
Answer 1

Return them in the order visible on this page.

============================================================
BOUNDING BOXES
============================================================

Return tight bounding boxes around the student's actual
handwriting.

Do NOT include:

- printed question text
- printed instructions
- headers
- page numbers
- margins
- unrelated handwriting

Coordinates:

x = left
y = top
w = width
h = height

All coordinates must be between 0 and 1.

If the answer continues to another page:

continues = true

Otherwise:

continues = false.

============================================================
UNCLEAR LABEL
============================================================

If the question reference cannot be read reliably:

Return the best visual reading with low confidence.

Do not invent a number.

============================================================
OUTPUT
============================================================

Return ONLY JSON.

{
  "matches": [
    {
      "question_number": "11 B",
      "confidence": 0.97,
      "boxes": [
        {
          "x": 0.10,
          "y": 0.25,
          "w": 0.80,
          "h": 0.20
        }
      ],
      "answer_text": "student answer",
      "continues": false
    }
  ],
  "unmatched_regions": []
}
"""


def extract_answer_mapping(
    page,
    questions,
    total_pages,
):

    prompt = (
        ANSWER_PROMPT
        + "\n\n"
        + f"This is answer-sheet page "
        f"{page['page_number']} of "
        f"{total_pages}."
    )

    contents = [
        image_part(
            page["png_bytes"]
        ),
        prompt,
    ]

    response = client.models.generate_content(
        model=MODEL,
        contents=contents,
        config=types.GenerateContentConfig(
            temperature=0,
            response_mime_type="application/json",
        ),
    )

    data = parse_json(
        response.text
    )

    matches = data.get(
        "matches",
        [],
    )

    unmatched_regions = data.get(
        "unmatched_regions",
        [],
    )

    if not isinstance(
        matches,
        list,
    ):
        matches = []

    if not isinstance(
        unmatched_regions,
        list,
    ):
        unmatched_regions = []

    return {
        "matches": matches,
        "unmatched_regions": unmatched_regions,
    }


# ============================================================
# GRADING PROMPT
# ============================================================

# IMPORTANT:
#
# Because this prompt uses .format(), literal JSON braces
# MUST be written as {{ and }}.
#
# {question_text} and {max_marks} are actual variables.

GRADE_PROMPT = r"""
You are an experienced examination grader.

QUESTION:

{question_text}

MAXIMUM MARKS:

{max_marks}

The supplied image(s) contain the student's handwritten answer.

Grade ONLY what the student actually wrote.

RULES:

- Award 0 to maximum marks.
- Give partial marks when appropriate.
- Evaluate correctness.
- Evaluate reasoning where relevant.
- Do not penalize handwriting style.
- Do not invent missing information.
- Keep feedback concise.
- Never award more than the maximum marks.

Return ONLY JSON in this exact structure:

{{
  "marks": 2,
  "feedback": "Correct answer with appropriate explanation."
}}
"""


# ============================================================
# GRADING
# ============================================================

def grade_answer(
    question,
    crop_png_list,
):

    # --------------------------------------------------------
    # No answer
    # --------------------------------------------------------

    if not crop_png_list:

        return {
            "marks": 0,
            "feedback": "No answer region found.",
        }

    # --------------------------------------------------------
    # Build Gemini contents
    # --------------------------------------------------------

    contents = []

    for crop in crop_png_list:

        contents.append(
            image_part(crop)
        )

    # --------------------------------------------------------
    # Add grading prompt
    # --------------------------------------------------------

    try:

        grading_prompt = GRADE_PROMPT.format(
            question_text=question["text"],
            max_marks=question["max_marks"],
        )

    except KeyError as exc:

        raise ValueError(
            f"Invalid GRADE_PROMPT format variable: {exc}"
        )

    contents.append(
        grading_prompt
    )

    # --------------------------------------------------------
    # Gemini request
    # --------------------------------------------------------

    response = client.models.generate_content(
        model=MODEL,
        contents=contents,
        config=types.GenerateContentConfig(
            temperature=0,
            response_mime_type="application/json",
        ),
    )

    # --------------------------------------------------------
    # Parse response
    # --------------------------------------------------------

    data = parse_json(
        response.text
    )

    # --------------------------------------------------------
    # Marks
    # --------------------------------------------------------

    try:

        marks = float(
            data.get(
                "marks",
                0,
            )
        )

    except (
        ValueError,
        TypeError,
    ):

        marks = 0

    # --------------------------------------------------------
    # Maximum marks
    # --------------------------------------------------------

    try:

        maximum = float(
            question.get(
                "max_marks",
                0,
            )
        )

    except (
        ValueError,
        TypeError,
    ):

        maximum = 0

    # --------------------------------------------------------
    # Clamp marks
    # --------------------------------------------------------

    marks = max(
        0,
        min(
            marks,
            maximum,
        ),
    )

    # --------------------------------------------------------
    # Feedback
    # --------------------------------------------------------

    feedback = str(
        data.get(
            "feedback",
            "",
        )
    ).strip()

    # --------------------------------------------------------
    # Return
    # --------------------------------------------------------

    return {
        "marks": marks,
        "feedback": feedback,
    }