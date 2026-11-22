from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .models import Bill, Payment, Subscriber, UsageEvent
from .pricing import price_usage
from .security import verify_password

ZERO = Decimal("0.00")
CENT = Decimal("0.01")
CURRENCY = "USD"


def money(value: Decimal | int | float | str) -> Decimal:
    return Decimal(str(value)).quantize(CENT)


def as_float(value: Decimal) -> float:
    return float(money(value))


def bill_status(total: Decimal, paid: Decimal) -> str:
    total = money(total)
    paid = money(paid)
    if paid <= 0:
        return "UNPAID" if total > 0 else "PAID"
    if paid >= total:
        return "PAID"
    return "PARTIAL"


def authenticate(db: Session, subscriber_no: str, password: str) -> Subscriber:
    subscriber = db.query(Subscriber).filter(Subscriber.subscriber_no == subscriber_no).one_or_none()
    if subscriber is None or not verify_password(password, subscriber.password_hash):
        raise HTTPException(status_code=401, detail="Invalid subscriber number or password")
    return subscriber


def require_subscriber(db: Session, subscriber_no: str) -> Subscriber:
    subscriber = db.query(Subscriber).filter(Subscriber.subscriber_no == subscriber_no).one_or_none()
    if subscriber is None:
        raise HTTPException(status_code=404, detail="Subscriber was not found")
    return subscriber


def assert_owner(actor: Subscriber, subscriber_no: str) -> None:
    if actor.role != "ADMIN" and actor.subscriber_no != subscriber_no:
        raise HTTPException(status_code=403, detail="You can only access your own subscriber records")


def period_totals(db: Session, subscriber_no: str, month: int, year: int) -> tuple[int, int]:
    rows = (
        db.query(UsageEvent.usage_type, func.coalesce(func.sum(UsageEvent.quantity), 0))
        .filter(
            UsageEvent.subscriber_no == subscriber_no,
            UsageEvent.month == month,
            UsageEvent.year == year,
        )
        .group_by(UsageEvent.usage_type)
        .all()
    )
    phone = 0
    internet = 0
    for usage_type, quantity in rows:
        if usage_type == "PHONE":
            phone = int(quantity)
        elif usage_type == "INTERNET":
            internet = int(quantity)
    return phone, internet


def _get_bill(db: Session, subscriber_no: str, month: int, year: int, lock: bool) -> Bill | None:
    query = db.query(Bill).filter(
        Bill.subscriber_no == subscriber_no,
        Bill.month == month,
        Bill.year == year,
    )
    if lock and db.bind is not None and db.bind.dialect.name == "postgresql":
        query = query.with_for_update()
    return query.one_or_none()


def _charges(phone_minutes: int, internet_mb: int) -> dict:
    priced = price_usage(phone_minutes, internet_mb)
    internet_gb = (Decimal(internet_mb) / Decimal(1000)).quantize(Decimal("0.001"))
    return {
        "phoneMinutes": phone_minutes,
        "phoneBlocks": priced.phone_blocks,
        "phoneCharge": as_float(priced.phone_charge),
        "internetMb": internet_mb,
        "internetGb": float(internet_gb),
        "internetBaseCharge": as_float(priced.internet_base_charge),
        "internetExtraBlocks": priced.internet_extra_blocks,
        "internetExtraCharge": as_float(priced.internet_extra_charge),
        "internetCharge": as_float(priced.internet_charge),
    }


def _summary(bill: Bill) -> dict:
    total = money(bill.total_amount)
    paid = money(bill.paid_amount)
    remaining = money(total - paid)
    return {
        "subscriberNo": bill.subscriber_no,
        "month": bill.month,
        "year": bill.year,
        "currency": CURRENCY,
        "billTotal": as_float(total),
        "paidAmount": as_float(paid),
        "remainingBalance": as_float(remaining),
        "status": bill.status,
    }


def add_usage(
    db: Session,
    actor: Subscriber,
    subscriber_no: str,
    month: int,
    year: int,
    usage_type: str,
) -> dict:
    assert_owner(actor, subscriber_no)
    require_subscriber(db, subscriber_no)
    normalized = usage_type.strip().upper()
    if normalized == "PHONE":
        quantity, unit = 10, "minutes"
    elif normalized == "INTERNET":
        quantity, unit = 1, "MB"
    else:
        raise HTTPException(status_code=400, detail="usageType must be PHONE or INTERNET")

    db.add(
        UsageEvent(
            subscriber_no=subscriber_no,
            month=month,
            year=year,
            usage_type=normalized,
            quantity=quantity,
            created_at=datetime.now(timezone.utc),
        )
    )
    db.commit()
    phone, internet = period_totals(db, subscriber_no, month, year)
    return {
        "transactionStatus": "RECORDED",
        "subscriberNo": subscriber_no,
        "month": month,
        "year": year,
        "usageType": normalized,
        "addedQuantity": quantity,
        "unit": unit,
        "periodPhoneMinutes": phone,
        "periodInternetMb": internet,
    }


def calculate_bill(db: Session, actor: Subscriber, subscriber_no: str, month: int, year: int) -> dict:
    assert_owner(actor, subscriber_no)
    require_subscriber(db, subscriber_no)
    phone, internet = period_totals(db, subscriber_no, month, year)
    priced = price_usage(phone, internet)
    bill = _get_bill(db, subscriber_no, month, year, lock=True)
    paid = money(bill.paid_amount) if bill is not None else ZERO
    if priced.total < paid:
        raise HTTPException(
            status_code=409,
            detail="Calculated total is below the amount already paid for this period",
        )

    now = datetime.now(timezone.utc)
    if bill is None:
        bill = Bill(
            subscriber_no=subscriber_no,
            month=month,
            year=year,
            phone_minutes=phone,
            internet_mb=internet,
            phone_charge=priced.phone_charge,
            internet_charge=priced.internet_charge,
            total_amount=priced.total,
            paid_amount=paid,
            status=bill_status(priced.total, paid),
            calculated_at=now,
        )
        db.add(bill)
    else:
        bill.phone_minutes = phone
        bill.internet_mb = internet
        bill.phone_charge = priced.phone_charge
        bill.internet_charge = priced.internet_charge
        bill.total_amount = priced.total
        bill.paid_amount = paid
        bill.status = bill_status(priced.total, paid)
        bill.calculated_at = now
    db.commit()
    db.refresh(bill)
    return {
        "transactionStatus": "CALCULATED",
        **_summary(bill),
        "charges": _charges(bill.phone_minutes, bill.internet_mb),
    }


def query_bill(db: Session, subscriber_no: str, month: int, year: int) -> dict:
    bill = _get_bill(db, subscriber_no, month, year, lock=False)
    if bill is None:
        raise HTTPException(status_code=404, detail="Bill has not been calculated for this period")
    return _summary(bill)


def query_bill_detailed(
    db: Session,
    actor: Subscriber,
    subscriber_no: str,
    month: int,
    year: int,
    page: int,
    page_size: int,
) -> dict:
    assert_owner(actor, subscriber_no)
    bill = _get_bill(db, subscriber_no, month, year, lock=False)
    if bill is None:
        raise HTTPException(status_code=404, detail="Bill has not been calculated for this period")

    total_items = (
        db.query(func.count(UsageEvent.id))
        .filter(
            UsageEvent.subscriber_no == subscriber_no,
            UsageEvent.month == month,
            UsageEvent.year == year,
        )
        .scalar()
        or 0
    )
    items = (
        db.query(UsageEvent)
        .filter(
            UsageEvent.subscriber_no == subscriber_no,
            UsageEvent.month == month,
            UsageEvent.year == year,
        )
        .order_by(UsageEvent.id)
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    total_pages = (total_items + page_size - 1) // page_size if total_items else 0
    return {
        **_summary(bill),
        "charges": _charges(bill.phone_minutes, bill.internet_mb),
        "usage": {
            "page": page,
            "pageSize": page_size,
            "totalItems": int(total_items),
            "totalPages": int(total_pages),
            "items": [
                {
                    "id": item.id,
                    "usageType": item.usage_type,
                    "quantity": item.quantity,
                    "unit": "minutes" if item.usage_type == "PHONE" else "MB",
                    "createdAt": item.created_at.isoformat(),
                }
                for item in items
            ],
        },
    }


def pay_bill(
    db: Session,
    actor: Subscriber,
    subscriber_no: str,
    month: int,
    year: int,
    amount: Decimal,
    transaction_id: str,
) -> dict:
    assert_owner(actor, subscriber_no)
    require_subscriber(db, subscriber_no)
    if amount != amount.quantize(CENT):
        raise HTTPException(status_code=400, detail="Amount must have at most 2 decimal places")
    applied = money(amount)
    if applied <= 0:
        raise HTTPException(status_code=400, detail="Amount must be greater than zero")

    transaction_id = transaction_id.strip()
    existing = db.query(Payment).filter(Payment.transaction_id == transaction_id).one_or_none()
    if existing is not None:
        raise HTTPException(status_code=409, detail="Duplicate transaction ID")

    bill = _get_bill(db, subscriber_no, month, year, lock=True)
    if bill is None:
        raise HTTPException(status_code=404, detail="Bill has not been calculated for this period")

    total = money(bill.total_amount)
    paid = money(bill.paid_amount)
    remaining = money(total - paid)
    if remaining <= 0:
        raise HTTPException(status_code=400, detail="Nothing left to pay for this period")
    if applied > remaining:
        raise HTTPException(status_code=400, detail="Amount exceeds the remaining balance")

    now = datetime.now(timezone.utc)
    db.add(
        Payment(
            bill_id=bill.id,
            subscriber_no=subscriber_no,
            month=month,
            year=year,
            amount=applied,
            transaction_id=transaction_id,
            created_at=now,
        )
    )
    bill.paid_amount = money(paid + applied)
    bill.status = bill_status(total, money(bill.paid_amount))
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Duplicate transaction ID") from exc
    db.refresh(bill)
    summary = _summary(bill)
    return {
        "paymentStatus": "ACCEPTED",
        "billStatus": bill.status,
        "subscriberNo": summary["subscriberNo"],
        "month": summary["month"],
        "year": summary["year"],
        "currency": CURRENCY,
        "amountApplied": as_float(applied),
        "paidAmount": summary["paidAmount"],
        "remainingBalance": summary["remainingBalance"],
        "transactionId": transaction_id,
    }
