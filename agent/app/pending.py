from __future__ import annotations

import threading

_pending: dict[str, dict] = {}
_lock = threading.Lock()


def get_pending(subscriber_no: str) -> dict | None:
    with _lock:
        item = _pending.get(subscriber_no)
        return dict(item) if item else None


def set_pending(subscriber_no: str, payment: dict) -> None:
    with _lock:
        _pending[subscriber_no] = dict(payment)


def clear_pending(subscriber_no: str) -> None:
    with _lock:
        _pending.pop(subscriber_no, None)
