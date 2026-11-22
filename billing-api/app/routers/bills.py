from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_subscriber
from ..models import Subscriber
from ..schemas import CalculateIn, CalculateOut, DetailedOut, PayIn, PayOut, QueryBillOut
from ..service import calculate_bill, pay_bill, query_bill, query_bill_detailed

router = APIRouter(tags=["Bills"])


@router.get("/bills", response_model=QueryBillOut)
def get_bill(
    subscriberNo: str = Query(min_length=1, max_length=32),
    month: int = Query(ge=1, le=12),
    year: int = Query(ge=2000, le=2100),
    db: Session = Depends(get_db),
) -> dict:
    """Return the calculated bill summary. Authentication is not required for this operation."""
    return query_bill(db, subscriberNo, month, year)


@router.get("/bills/detailed", response_model=DetailedOut)
def get_bill_detailed(
    subscriberNo: str = Query(min_length=1, max_length=32),
    month: int = Query(ge=1, le=12),
    year: int = Query(ge=2000, le=2100),
    page: int = Query(default=1, ge=1),
    pageSize: int = Query(default=10, ge=1, le=100),
    actor: Subscriber = Depends(get_current_subscriber),
    db: Session = Depends(get_db),
) -> dict:
    """Return usage and the charge breakdown. Requires a JWT and is paged."""
    return query_bill_detailed(db, actor, subscriberNo, month, year, page, pageSize)


@router.post("/bills/calculate", response_model=CalculateOut)
def post_calculate(
    body: CalculateIn,
    actor: Subscriber = Depends(get_current_subscriber),
    db: Session = Depends(get_db),
) -> dict:
    """Price the stored usage for a month and save the bill. Requires a JWT."""
    return calculate_bill(db, actor, body.subscriber_no, body.month, body.year)


@router.post("/bills/pay", response_model=PayOut)
def post_pay(
    body: PayIn,
    actor: Subscriber = Depends(get_current_subscriber),
    db: Session = Depends(get_db),
) -> dict:
    """Record a simulated partial or full payment. Requires a JWT. No card is charged."""
    return pay_bill(
        db,
        actor,
        body.subscriber_no,
        body.month,
        body.year,
        body.amount,
        body.transaction_id,
    )
