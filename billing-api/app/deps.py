from __future__ import annotations

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from .database import get_db
from .models import Subscriber
from .security import decode_token

bearer_scheme = HTTPBearer(auto_error=False)


def get_current_subscriber(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> Subscriber:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="Missing bearer token")
    try:
        payload = decode_token(credentials.credentials)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    subscriber = (
        db.query(Subscriber).filter(Subscriber.subscriber_no == payload.get("sub")).one_or_none()
    )
    if subscriber is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return subscriber
