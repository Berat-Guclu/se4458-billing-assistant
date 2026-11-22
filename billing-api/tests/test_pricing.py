from __future__ import annotations

from decimal import Decimal

import pytest

from app.pricing import price_usage
from app.service import bill_status


@pytest.mark.parametrize(
    ("minutes", "blocks", "charge"),
    [
        (0, 0, 0),
        (999, 0, 0),
        (1000, 0, 0),
        (1001, 1, 10),
        (2000, 1, 10),
        (2001, 2, 20),
        (3000, 2, 20),
    ],
)
def test_phone_blocks(minutes: int, blocks: int, charge: int) -> None:
    priced = price_usage(minutes, 0)
    assert priced.phone_blocks == blocks
    assert priced.phone_charge == Decimal(charge)
    assert priced.internet_charge == Decimal(50)
    assert priced.total == Decimal(charge) + Decimal(50)


@pytest.mark.parametrize(
    ("megabytes", "blocks", "charge"),
    [
        (0, 0, 50),
        (19999, 0, 50),
        (20000, 0, 50),
        (20001, 1, 60),
        (30000, 1, 60),
        (30001, 2, 70),
        (35000, 2, 70),
        (40000, 2, 70),
        (40001, 3, 80),
    ],
)
def test_internet_blocks(megabytes: int, blocks: int, charge: int) -> None:
    priced = price_usage(0, megabytes)
    assert priced.internet_extra_blocks == blocks
    assert priced.internet_base_charge == Decimal(50)
    assert priced.internet_charge == Decimal(charge)


def test_october_sample_is_seventy_dollars() -> None:
    priced = price_usage(800, 35000)
    assert priced.phone_charge == Decimal(0)
    assert priced.internet_charge == Decimal(70)
    assert priced.total == Decimal(70)
    assert priced.internet_mb / 1000 == 35


def test_negative_usage_is_rejected() -> None:
    with pytest.raises(ValueError):
        price_usage(-1, 0)


def test_bill_status_values() -> None:
    assert bill_status(Decimal("50"), Decimal("0")) == "UNPAID"
    assert bill_status(Decimal("70"), Decimal("20")) == "PARTIAL"
    assert bill_status(Decimal("70"), Decimal("70")) == "PAID"
    assert bill_status(Decimal("0"), Decimal("0")) == "PAID"
