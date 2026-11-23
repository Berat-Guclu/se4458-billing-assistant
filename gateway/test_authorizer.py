import os
import time

import jwt

os.environ["JWT_SECRET"] = "billing-demo-secret-key-please-change"
os.environ["JWT_ISSUER"] = "billing-key"

from authorizer import handler  # noqa: E402

SECRET = os.environ["JWT_SECRET"]


def _event(token: str) -> dict:
    return {"headers": {"authorization": f"Bearer {token}"}}


def _token(**extra) -> str:
    payload = {"iss": "billing-key", "sub": "5551001", "exp": int(time.time()) + 600}
    payload.update(extra)
    return jwt.encode(payload, SECRET, algorithm="HS256")


def test_valid_token_is_authorized() -> None:
    assert handler(_event(_token()), None) == {"isAuthorized": True}


def test_missing_token_is_rejected() -> None:
    assert handler({"headers": {}}, None)["isAuthorized"] is False


def test_wrong_issuer_is_rejected() -> None:
    assert handler(_event(_token(iss="other")), None)["isAuthorized"] is False


def test_expired_token_is_rejected() -> None:
    assert handler(_event(_token(exp=int(time.time()) - 10)), None)["isAuthorized"] is False
