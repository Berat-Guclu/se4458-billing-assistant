from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_subscriber
from ..models import Subscriber
from ..schemas import UsageIn, UsageOut
from ..service import add_usage

router = APIRouter(tags=["Usage"])


@router.post("/usage", response_model=UsageOut)
def create_usage(
    body: UsageIn,
    actor: Subscriber = Depends(get_current_subscriber),
    db: Session = Depends(get_db),
) -> dict:
    """Add 10 phone minutes or 1 MB of internet for one month. Requires a JWT."""
    return add_usage(db, actor, body.subscriber_no, body.month, body.year, body.usage_type)
