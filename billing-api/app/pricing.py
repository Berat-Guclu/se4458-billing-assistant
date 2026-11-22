from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

# Assignment rule: 1 GB = 1,000 MB.
MB_PER_GB = 1000
PHONE_FREE_MINUTES = 1000
PHONE_BLOCK_MINUTES = 1000
PHONE_BLOCK_PRICE = Decimal("10.00")
INTERNET_INCLUDED_MB = 20 * MB_PER_GB
INTERNET_BLOCK_MB = 10 * MB_PER_GB
INTERNET_BASE = Decimal("50.00")
INTERNET_BLOCK_PRICE = Decimal("10.00")
CENT = Decimal("0.01")


@dataclass(frozen=True)
class PriceBreakdown:
    phone_minutes: int
    internet_mb: int
    phone_blocks: int
    phone_charge: Decimal
    internet_extra_blocks: int
    internet_base_charge: Decimal
    internet_extra_charge: Decimal
    internet_charge: Decimal
    total: Decimal


def started_blocks(extra: int, block_size: int) -> int:
    """A started block is any partial block, rounded up."""
    if extra <= 0:
        return 0
    return (extra + block_size - 1) // block_size


def price_usage(phone_minutes: int, internet_mb: int) -> PriceBreakdown:
    if phone_minutes < 0 or internet_mb < 0:
        raise ValueError("usage cannot be negative")

    phone_blocks = started_blocks(phone_minutes - PHONE_FREE_MINUTES, PHONE_BLOCK_MINUTES)
    phone_charge = (PHONE_BLOCK_PRICE * phone_blocks).quantize(CENT)

    extra_blocks = started_blocks(internet_mb - INTERNET_INCLUDED_MB, INTERNET_BLOCK_MB)
    internet_extra = (INTERNET_BLOCK_PRICE * extra_blocks).quantize(CENT)
    internet_charge = (INTERNET_BASE + internet_extra).quantize(CENT)
    total = (phone_charge + internet_charge).quantize(CENT)

    return PriceBreakdown(
        phone_minutes=phone_minutes,
        internet_mb=internet_mb,
        phone_blocks=phone_blocks,
        phone_charge=phone_charge,
        internet_extra_blocks=extra_blocks,
        internet_base_charge=INTERNET_BASE,
        internet_extra_charge=internet_extra,
        internet_charge=internet_charge,
        total=total,
    )
