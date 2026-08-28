from .mapping import normalize_question_number


tests = {
    "1": "1",
    "Q1": "1",
    "Q.1": "1",
    "Question 1": "1",
    "question one": "1",
    "Answer 1": "1",
    "Answer One": "1",
    "Ans 1": "1",
    "Ans. One": "1",

    "2": "2",
    "Question Two": "2",
    "Answer Two": "2",

    "11": "11",
    "Q11": "11",
    "Question 11": "11",
    "Answer 11": "11",

    "11a": "11 (a)",
    "11 a": "11 (a)",
    "11(a)": "11 (a)",
    "11 (a)": "11 (a)",
    "11. (a)": "11 (a)",
    "Q11(a)": "11 (a)",
    "Q.11(a)": "11 (a)",
    "Question 11(a)": "11 (a)",
    "Answer 11 A": "11 (a)",

    "11b": "11 (b)",
    "11 b": "11 (b)",
    "11(b)": "11 (b)",
    "11 (b)": "11 (b)",
    "Q11(b)": "11 (b)",
    "Question 11 B": "11 (b)",
    "Answer 11 B": "11 (b)",
}


for source, expected in tests.items():

    actual = normalize_question_number(
        source
    )

    print(
        f"{source:25} "
        f"-> {actual:10} "
        f"expected={expected}"
    )

    assert actual == expected


print()
print("ALL MAPPING TESTS PASSED")