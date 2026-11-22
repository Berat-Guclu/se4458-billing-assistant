from __future__ import annotations

from calendar import monthrange
from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy.orm import Session

from .models import Bill, Payment, Subscriber, UsageEvent
from .pricing import price_usage
from .security import hash_password
from .service import bill_status

DEMO_SUBSCRIBERS = (
    ("5551001", "Ece Yilmaz", "demo123", "SUBSCRIBER"),
    ("5551002", "Kerem Acar", "demo123", "SUBSCRIBER"),
    ("5551999", "Billing Admin", "admin123", "ADMIN"),
)
HISTORY_SUBSCRIBERS = ("5551001", "5551002")
HISTORY_MONTHS = 36

# Months the written scenarios name exactly. Everything else is filled around these.
SIGNATURE_EVENTS: dict[tuple[str, int, int], tuple[tuple[str, int], ...]] = {
    # 800 minutes (free) and 35 GB → internet $70, unpaid.
    ("5551001", 2025, 10): (
        ("PHONE", 500),
        ("PHONE", 300),
        ("INTERNET", 20000),
        ("INTERNET", 10000),
        ("INTERNET", 5000),
    ),
    # 400 minutes and 8 GB → $50, paid in full.
    ("5551001", 2025, 9): (
        ("PHONE", 400),
        ("INTERNET", 8000),
    ),
    # 2,500 minutes ($20) and 20 GB ($50) → $70, $20 paid.
    ("5551002", 2025, 4): (
        ("PHONE", 2500),
        ("INTERNET", 20000),
    ),
}


@dataclass(frozen=True)
class SeedMonth:
    subscriber_no: str
    year: int
    month: int
    events: tuple[tuple[str, int], ...]
    phone_minutes: int
    internet_mb: int
    total: Decimal
    paid: Decimal
    transaction_id: str | None


def history_months(today: date) -> list[tuple[int, int]]:
    """36 calendar months ending with the month of `today`, oldest first."""
    year, month = today.year, today.month
    found: list[tuple[int, int]] = []
    for _ in range(HISTORY_MONTHS):
        found.append((year, month))
        month -= 1
        if month == 0:
            year -= 1
            month = 12
    found.reverse()
    return found


def _varied_events(subscriber_no: str, year: int, month: int) -> tuple[tuple[str, int], ...]:
    salt = 0 if subscriber_no == "5551001" else 19
    key = year * 12 + month + salt
    phone = 220 + (key * 53) % 1600
    internet = 3000 + (key * 997) % 32000
    events: list[tuple[str, int]] = []
    if phone > 900:
        half = phone // 2
        events.append(("PHONE", half))
        events.append(("PHONE", phone - half))
    else:
        events.append(("PHONE", phone))
    remaining = internet
    while remaining:
        chunk = min(10000, remaining)
        events.append(("INTERNET", chunk))
        remaining -= chunk
    return tuple(events)


def _paid_amount(
    subscriber_no: str,
    year: int,
    month: int,
    total: Decimal,
    current: tuple[int, int],
) -> Decimal:
    if (year, month) == current:
        return Decimal("0.00")
    if (subscriber_no, year, month) == ("5551001", 2025, 10):
        return Decimal("0.00")
    if (subscriber_no, year, month) == ("5551002", 2025, 4):
        return Decimal("20.00")
    return total


def build_seed_plan(today: date) -> list[SeedMonth]:
    months = history_months(today)
    current = months[-1]
    plan: list[SeedMonth] = []
    for subscriber_no in HISTORY_SUBSCRIBERS:
        for year, month in months:
            events = SIGNATURE_EVENTS.get((subscriber_no, year, month)) or _varied_events(
                subscriber_no, year, month
            )
            phone = sum(quantity for kind, quantity in events if kind == "PHONE")
            internet = sum(quantity for kind, quantity in events if kind == "INTERNET")
            total = price_usage(phone, internet).total
            paid = _paid_amount(subscriber_no, year, month, total, current)
            transaction_id = None
            if paid > 0:
                transaction_id = f"SEED-{subscriber_no}-{year}-{month:02d}"
            plan.append(
                SeedMonth(
                    subscriber_no=subscriber_no,
                    year=year,
                    month=month,
                    events=events,
                    phone_minutes=phone,
                    internet_mb=internet,
                    total=total,
                    paid=paid,
                    transaction_id=transaction_id,
                )
            )
    return plan


def _at(year: int, month: int, day: int, hour: int, ceiling: datetime) -> datetime:
    last = monthrange(year, month)[1]
    moment = datetime(year, month, min(day, last), hour, 15, tzinfo=timezone.utc)
    if moment > ceiling:
        return ceiling
    return moment


def seed_if_empty(db: Session) -> None:
    if db.query(Subscriber).first() is not None:
        return

    now = datetime.now(timezone.utc)
    plan = build_seed_plan(now.date())
    first_year, first_month = plan[0].year, plan[0].month
    opened = _at(first_year, first_month, 1, 8, now)
    for subscriber_no, full_name, password, role in DEMO_SUBSCRIBERS:
        db.add(
            Subscriber(
                subscriber_no=subscriber_no,
                full_name=full_name,
                password_hash=hash_password(password),
                role=role,
                created_at=opened,
            )
        )
    db.flush()

    for item in plan:
        for index, (usage_type, quantity) in enumerate(item.events):
            db.add(
                UsageEvent(
                    subscriber_no=item.subscriber_no,
                    month=item.month,
                    year=item.year,
                    usage_type=usage_type,
                    quantity=quantity,
                    created_at=_at(item.year, item.month, 3 + index * 5, 9 + index, now),
                )
            )
    db.flush()

    for item in plan:
        calculated_at = _at(item.year, item.month, 28, 16, now)
        bill = Bill(
            subscriber_no=item.subscriber_no,
            month=item.month,
            year=item.year,
            phone_minutes=item.phone_minutes,
            internet_mb=item.internet_mb,
            phone_charge=price_usage(item.phone_minutes, item.internet_mb).phone_charge,
            internet_charge=price_usage(item.phone_minutes, item.internet_mb).internet_charge,
            total_amount=item.total,
            paid_amount=item.paid,
            status=bill_status(item.total, item.paid),
            calculated_at=calculated_at,
        )
        db.add(bill)
        db.flush()
        if item.transaction_id is not None:
            paid_on = _at(item.year, item.month, 28, 18, now)
            db.add(
                Payment(
                    bill_id=bill.id,
                    subscriber_no=item.subscriber_no,
                    month=item.month,
                    year=item.year,
                    amount=item.paid,
                    transaction_id=item.transaction_id,
                    created_at=paid_on,
                )
            )
    db.commit()
