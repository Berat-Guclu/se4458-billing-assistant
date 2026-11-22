from __future__ import annotations

import re

CONFIRM_RE = re.compile(r"\b(confirm|onaylıyorum|onayliyorum)\b", re.IGNORECASE)


def user_confirmed(message: str) -> bool:
    return bool(CONFIRM_RE.search(message or ""))


def payment_allowed(message: str, pending: dict | None) -> bool:
    return bool(pending) and user_confirmed(message)
