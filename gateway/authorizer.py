"""HTTP API Lambda authorizer for the billing JWT.

Paste this file into a Python 3.12 Lambda. Set the authorizer payload
format to 2.0 and enable simple responses. Environment:

    JWT_SECRET=billing-demo-secret-key-please-change
    JWT_ISSUER=billing-key

The function uses only the Python standard library.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time


def handler(event, context):
    headers = {str(key).lower(): value for key, value in (event.get("headers") or {}).items()}
    raw = str(headers.get("authorization") or "")
    token = raw[7:].strip() if raw.lower().startswith("bearer ") else ""
    return {"isAuthorized": _valid(token)}


def _valid(token: str) -> bool:
    secret = os.environ.get("JWT_SECRET", "")
    issuer = os.environ.get("JWT_ISSUER", "billing-key")
    if not secret or token.count(".") != 2:
        return False
    try:
        header_b, payload_b, sig_b = token.split(".")
        header = json.loads(_b64url(header_b))
        if header.get("alg") != "HS256":
            return False
        expected = hmac.new(
            secret.encode(),
            f"{header_b}.{payload_b}".encode(),
            hashlib.sha256,
        ).digest()
        if not hmac.compare_digest(expected, _b64url(sig_b)):
            return False
        payload = json.loads(_b64url(payload_b))
        if payload.get("iss") != issuer or not payload.get("sub"):
            return False
        return int(payload["exp"]) > int(time.time())
    except (ValueError, TypeError, json.JSONDecodeError, KeyError):
        return False


def _b64url(data: str) -> bytes:
    return base64.urlsafe_b64decode(data + "=" * (-len(data) % 4))
