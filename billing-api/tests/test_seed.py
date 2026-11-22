from __future__ import annotations

from datetime import date
from decimal import Decimal

from app.pricing import price_usage
from app.seed import HISTORY_MONTHS, build_seed_plan, history_months

AS_OF = date(2026, 11, 22)


def test_history_covers_three_years_ending_this_month() -> None:
    months = history_months(AS_OF)
    assert len(months) == HISTORY_MONTHS
    assert months[0] == (2023, 12)
    assert months[-1] == (2026, 11)
    assert len(set(months)) == HISTORY_MONTHS


def test_seed_keeps_the_written_scenarios_and_fills_both_subscribers() -> None:
    plan = build_seed_plan(AS_OF)
    by_key = {(item.subscriber_no, item.year, item.month): item for item in plan}

    assert len(plan) == HISTORY_MONTHS * 2
    assert len(by_key) == len(plan)

    ece_october = by_key[("5551001", 2025, 10)]
    assert ece_october.phone_minutes == 800
    assert ece_october.internet_mb == 35000
    assert ece_october.total == Decimal("70.00")
    assert ece_october.paid == Decimal("0.00")
    assert ece_october.transaction_id is None

    ece_september = by_key[("5551001", 2025, 9)]
    assert ece_september.phone_minutes == 400
    assert ece_september.internet_mb == 8000
    assert ece_september.total == Decimal("50.00")
    assert ece_september.paid == Decimal("50.00")
    assert ece_september.transaction_id == "SEED-5551001-2025-09"

    kerem_april = by_key[("5551002", 2025, 4)]
    assert kerem_april.phone_minutes == 2500
    assert kerem_april.internet_mb == 20000
    assert kerem_april.total == Decimal("70.00")
    assert kerem_april.paid == Decimal("20.00")
    assert kerem_april.transaction_id == "SEED-5551002-2025-04"

    transaction_ids = [item.transaction_id for item in plan if item.transaction_id]
    assert len(transaction_ids) == len(set(transaction_ids))

    for item in plan:
        assert item.paid <= item.total
        assert item.total == price_usage(item.phone_minutes, item.internet_mb).total
        current = (item.year, item.month) == (2026, 11)
        story_unpaid = (item.subscriber_no, item.year, item.month) == ("5551001", 2025, 10)
        story_partial = (item.subscriber_no, item.year, item.month) == ("5551002", 2025, 4)
        if current or story_unpaid:
            assert item.paid == Decimal("0.00")
        elif story_partial:
            assert item.paid == Decimal("20.00")
        else:
            assert item.paid == item.total
