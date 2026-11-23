import json
from pathlib import Path

from billing_mcp.indexer import BillingIndex

GUIDE = Path(__file__).resolve().parents[1] / "docs" / "Mobile_Provider_Billing_Guide.md"


def index() -> BillingIndex:
    built = BillingIndex.from_file(GUIDE)
    assert built.chunk_count >= 8
    return built


def test_index_is_reused_for_later_queries() -> None:
    built = index()
    first = {hit["section"] for hit in built.search("extra internet cost")}
    second = {hit["section"] for hit in built.search("late payment")}
    assert "3.2" in first
    assert "6.2" in second
    assert built.chunk_count == index().chunk_count


def test_extra_internet_query_returns_section_3_2() -> None:
    hits = index().search("How much does extra internet cost?")
    sections = {hit["section"] for hit in hits}
    assert "3.2" in sections
    block = next(hit for hit in hits if hit["section"] == "3.2")
    assert block["heading"] == "Additional internet blocks"
    assert "70" in block["excerpt"]
    body = json.loads(index().search_text("How much does extra internet cost?"))
    assert body["document"] == "Mobile_Provider_Billing_Guide.md"
    match = next(item for item in body["matches"] if item["section"] == "3.2")
    assert match["heading"] == "Additional internet blocks"
    assert "text" in match


def test_partial_payment_query_returns_section_5() -> None:
    hits = index().search("partial payment")
    assert hits[0]["section"] == "5.1"
    assert "partial" in hits[0]["excerpt"].lower()


def test_late_payment_query_returns_section_6() -> None:
    hits = index().search("late payment")
    assert hits[0]["section"] == "6.2"
    assert "does not add a fee" in hits[0]["excerpt"]


def test_unknown_query_returns_no_section() -> None:
    assert index().search("rocket ships and volcanoes") == []
    body = json.loads(index().search_text("rocket ships and volcanoes"))
    assert body["matches"] == []
    assert "No matching" in body["message"]


def test_blank_query() -> None:
    assert index().search("   ") == []
    assert index().search_text("  ") == "No query was provided."
