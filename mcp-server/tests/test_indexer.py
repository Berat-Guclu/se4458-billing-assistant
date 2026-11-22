from pathlib import Path

from billing_mcp.indexer import BillingIndex

GUIDE = Path(__file__).resolve().parents[1] / "docs" / "Mobile_Provider_Billing_Guide.md"


def index() -> BillingIndex:
    built = BillingIndex.from_file(GUIDE)
    assert built.chunk_count >= 8
    return built


def test_index_is_reused_for_later_queries() -> None:
    built = index()
    first = built.search("extra internet cost")
    second = built.search("late payment fee")
    assert first[0]["section"] == "3.2"
    assert second[0]["section"] == "7"
    assert built.chunk_count == index().chunk_count


def test_extra_internet_query_returns_section_3_2() -> None:
    hits = index().search("How much does extra internet cost?")
    assert hits[0]["section"] == "3.2"
    assert "70" in hits[0]["excerpt"]
    text = index().search_text("How much does extra internet cost?")
    assert text.startswith("Section 3.2:")


def test_partial_payment_query_returns_section_5() -> None:
    hits = index().search("partial payment rules")
    assert hits[0]["section"] == "5"
    assert "transaction ID" in hits[0]["excerpt"]


def test_late_payment_query_returns_section_7() -> None:
    hits = index().search("late payment fee")
    assert hits[0]["section"] == "7"
    assert "5 percent" in hits[0]["excerpt"]


def test_unknown_query_returns_no_section() -> None:
    assert index().search("rocket ships and volcanoes") == []
    assert "No matching" in index().search_text("rocket ships and volcanoes")


def test_blank_query() -> None:
    assert index().search("   ") == []
    assert index().search_text("  ") == "No query was provided."
