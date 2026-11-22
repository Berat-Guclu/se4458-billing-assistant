from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..schemas import LoginIn, TokenOut
from ..security import create_token
from ..service import authenticate

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login", response_model=TokenOut)
def login(body: LoginIn, db: Session = Depends(get_db)) -> dict:
    """Issue a JWT for a subscriber or admin. The gateway does not require a token here."""
    user = authenticate(db, body.subscriber_no, body.password)
    token = create_token(subscriber_no=user.subscriber_no, role=user.role, full_name=user.full_name)
    return {
        "accessToken": token,
        "tokenType": "Bearer",
        "expiresIn": settings.jwt_ttl_seconds,
        "subscriberNo": user.subscriber_no,
        "fullName": user.full_name,
        "role": user.role,
    }
