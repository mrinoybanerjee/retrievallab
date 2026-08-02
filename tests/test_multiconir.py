from scripts.prepare_multiconir import build_case, extract_conditions


def test_numbered_condition_parser_ignores_decimal_values() -> None:
    query = " ".join(
        [
            "Find a book with",
            "1. rating above 2.5 stars",
            "2. published after 2010",
            "3. hardcover",
            "4. under 400 pages",
            "5. science fiction",
            "6. English",
            "7. award winning",
            "8. available digitally",
            "9. female protagonist",
            "10. standalone novel",
        ]
    )

    conditions = extract_conditions(query)

    assert len(conditions) == 10
    assert conditions[0] == "rating above 2.5 stars"
    assert conditions[-1] == "standalone novel"


def test_bullet_condition_parser_accepts_source_rows_with_fewer_than_ten_items() -> None:
    query = "Find a legal document:\n" + "\n".join(f"- condition {index}" for index in range(1, 10))

    assert extract_conditions(query) == [f"condition {index}" for index in range(1, 10)]


def test_adapter_preserves_positive_and_ordered_hard_negative_labels() -> None:
    row = {
        "Query10": " ".join(f"{index}. condition {index}" for index in range(1, 11)),
        "Natural_Query10": "Find the item satisfying every requested condition.",
        "Positive": "complete document",
        **{f"HN{index}": f"hard negative {index}" for index in range(1, 11)},
    }

    case = build_case("Books", 3, row, query_format="structured")

    assert case["complete_document_ids"] == ["multiconir-books-0003-structured-positive"]
    assert case["partial_document_ids"][0].endswith("hn1")
    assert case["partial_document_ids"][-1].endswith("hn10")
    assert len(case["required"]) == 10
