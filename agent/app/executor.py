from __future__ import annotations

import json
import os
import uuid
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP

import httpx

from .confirmation import payment_allowed
from .mcp_client import search_billing_documentation
from .pending import clear_pending, get_pending, set_pending

CENT = Decimal("0.01")


@dataclass
class ToolContext:
    token: str
    subscriber_no: str
    user_message: str


def gateway_base() -> str:
    return os.getenv("GATEWAY_BASE_URL", "http://localhost:8088").rstrip("/")


async def execute_tool(name: str, arguments: dict | None, ctx: ToolContext) -> str:
    arguments = arguments or {}
    try:
        if name == "search_billing_documentation":
            query = str(arguments.get("query", "")).strip()
            if not query:
                return "Error: query is required"
            return await search_billing_documentation(query)
        if name == "query_bill":
            month, year = _period(arguments)
            return await _gateway(
                "GET",
                "/api/v1/bills",
                ctx.token,
                params={"subscriberNo": ctx.subscriber_no, "month": month, "year": year},
            )
        if name == "query_bill_detailed":
            month, year = _period(arguments)
            page = int(arguments.get("page") or 1)
            page_size = int(arguments.get("pageSize") or 10)
            return await _gateway(
                "GET",
                "/api/v1/bills/detailed",
                ctx.token,
                params={
                    "subscriberNo": ctx.subscriber_no,
                    "month": month,
                    "year": year,
                    "page": page,
                    "pageSize": page_size,
                },
            )
        if name == "propose_bill_payment":
            return await _propose(arguments, ctx)
        if name == "confirm_bill_payment":
            return await _confirm(ctx)
        return f"Error: unknown tool {name}"
    except ValueError as exc:
        return f"Error: {exc}"
    except httpx.HTTPError as exc:
        return f"Error: gateway request failed: {exc}"
    except Exception as exc:
        return f"Error: {exc}"


async def _propose(arguments: dict, ctx: ToolContext) -> str:
    month, year = _period(arguments)
    if "amount" not in arguments:
        return "Error: amount is required"
    amount = Decimal(str(arguments["amount"])).quantize(CENT, rounding=ROUND_HALF_UP)
    if amount <= 0:
        return "Error: amount must be greater than zero"
    raw = await _gateway(
        "GET",
        "/api/v1/bills",
        ctx.token,
        params={"subscriberNo": ctx.subscriber_no, "month": month, "year": year},
    )
    if raw.startswith("Error"):
        return raw
    bill = json.loads(raw)
    remaining = Decimal(str(bill["remainingBalance"])).quantize(CENT)
    if amount > remaining:
        return f"Error: amount {amount} exceeds the remaining balance {remaining}"
    set_pending(
        ctx.subscriber_no,
        {"month": month, "year": year, "amount": f"{amount:.2f}", "currency": "USD"},
    )
    return (
        f"Pending payment prepared: {amount:.2f} USD for {month:02d}/{year}. "
        "No payment has been recorded. Ask the user to reply CONFIRM. "
        "Do not say the payment succeeded."
    )


async def _confirm(ctx: ToolContext) -> str:
    pending = get_pending(ctx.subscriber_no)
    if not payment_allowed(ctx.user_message, pending):
        return (
            "Error: payment was not sent. The latest user message must explicitly say CONFIRM, "
            "and a payment must already be pending."
        )
    assert pending is not None
    transaction_id = "AGT-" + uuid.uuid4().hex[:16]
    raw = await _gateway(
        "POST",
        "/api/v1/bills/pay",
        ctx.token,
        json_body={
            "subscriberNo": ctx.subscriber_no,
            "month": pending["month"],
            "year": pending["year"],
            "amount": pending["amount"],
            "transactionId": transaction_id,
        },
    )
    if not raw.startswith("Error"):
        clear_pending(ctx.subscriber_no)
    return raw


async def _gateway(
    method: str,
    path: str,
    token: str | None,
    *,
    params: dict | None = None,
    json_body: dict | None = None,
) -> str:
    headers = {"Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.request(
            method,
            gateway_base() + path,
            headers=headers,
            params=params,
            json=json_body,
        )
    if response.status_code >= 400:
        return f"Error {response.status_code}: {response.text}"
    return response.text


def _period(arguments: dict) -> tuple[int, int]:
    try:
        month = int(arguments["month"])
        year = int(arguments["year"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("month and year are required integers") from exc
    if not 1 <= month <= 12 or not 2000 <= year <= 2100:
        raise ValueError("month must be 1-12 and year must be 2000-2100")
    return month, year
