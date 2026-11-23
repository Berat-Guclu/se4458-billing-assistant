from __future__ import annotations

import json
import logging
import os

from openai import OpenAI

from .executor import ToolContext, execute_tool
from .pending import get_pending
from .tool_schema import TOOLS
from .confirmation import user_confirmed

logger = logging.getLogger("agent")

SYSTEM_PROMPT = """You are the Mobile Provider Billing Assistant for one authenticated subscriber.
The subscriber number is {subscriber_no} and the name is {full_name}.
You can use only that subscriber. If the user types a different subscriber number, refuse the private lookup and say you can only use the logged-in subscriber.
You do not have a tool that accepts a subscriber number. Never invent one.

Choose tools yourself:
- Policy, pricing, allowances, extra data, disputes, late fees, or payment rules: search_billing_documentation.
- Bill total, paid amount, remaining balance, or status: query_bill.
- Why a bill is high, minutes, megabytes, gigabytes, or the charge breakdown: query_bill_detailed and, when the reason depends on a rule, search_billing_documentation too.
- A request to pay: query_bill if needed, then propose_bill_payment. Do not call confirm_bill_payment in that same turn.
- The user replies CONFIRM and a payment is pending: call confirm_bill_payment before saying the payment succeeded.

Use tool results only. Do not invent balances, usage, or fees. The billing guide says a late reminder does not add a fee. Do not add one on top of the API total.
Cite the policy section number when you used the documentation tool.
Amounts are USD. If the user names a month without a year, assume 2025 and say so.
Reply in the user's language.
"""


async def answer_question(
    *,
    token: str,
    subscriber_no: str,
    full_name: str,
    message: str,
    history: list[dict],
) -> dict:
    client = _client()
    if client is None:
        raise RuntimeError(
            "OPENAI_API_KEY is not set. The agent uses real LLM tool calling and does not fall back to keyword routing."
        )

    messages: list[dict] = [
        {
            "role": "system",
            "content": SYSTEM_PROMPT.format(subscriber_no=subscriber_no, full_name=full_name),
        }
    ]
    for item in history[-12:]:
        role = item.get("role")
        content = str(item.get("content", "")).strip()
        if role in {"user", "assistant"} and content:
            messages.append({"role": role, "content": content[:4000]})
    messages.append({"role": "user", "content": message})

    ctx = ToolContext(token=token, subscriber_no=subscriber_no, user_message=message)
    trace: list[dict] = []
    nudged = False
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    for _ in range(6):
        completion = client.chat.completions.create(
            model=model,
            messages=messages,
            tools=TOOLS,
            tool_choice="auto",
            temperature=0.2,
        )
        choice = completion.choices[0].message
        tool_calls = choice.tool_calls or []
        if not tool_calls:
            if not nudged and user_confirmed(message) and get_pending(subscriber_no):
                nudged = True
                messages.append({"role": "assistant", "content": choice.content or ""})
                messages.append(
                    {
                        "role": "system",
                        "content": (
                            "A payment is pending and the user explicitly confirmed. "
                            "Call confirm_bill_payment now. Do not claim success until that tool returns."
                        ),
                    }
                )
                continue
            answer = (choice.content or "").strip() or "I could not produce an answer from the tool results."
            return {
                "answer": answer,
                "trace": trace,
                "pendingPayment": get_pending(subscriber_no),
                "model": model,
            }

        names = [call.function.name for call in tool_calls]
        trace.append(
            {
                "via": "llm",
                "tool": "llm",
                "input": {"selected": names},
                "result": "Selected " + ", ".join(names),
            }
        )
        logger.info("LLM selected tools: %s", ", ".join(names))
        messages.append(_assistant_message(choice))
        for call in tool_calls:
            try:
                arguments = json.loads(call.function.arguments or "{}")
            except json.JSONDecodeError:
                arguments = {}
            result = await execute_tool(call.function.name, arguments, ctx)
            logger.info("Tool %s completed", call.function.name)
            trace.append(
                {
                    "via": "mcp" if call.function.name == "search_billing_documentation" else "gateway",
                    "tool": call.function.name,
                    "input": arguments,
                    "result": result,
                }
            )
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": call.id,
                    "content": result[:8000],
                }
            )

    return {
        "answer": "I stopped after several tool calls without a final answer. Please try a more specific question.",
        "trace": trace,
        "pendingPayment": get_pending(subscriber_no),
        "model": model,
    }


def _client() -> OpenAI | None:
    key = os.getenv("OPENAI_API_KEY", "").strip()
    if not key:
        return None
    return OpenAI(api_key=key, base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"))


def _assistant_message(message) -> dict:
    payload: dict = {
        "role": "assistant",
        "tool_calls": [
            {
                "id": call.id,
                "type": "function",
                "function": {
                    "name": call.function.name,
                    "arguments": call.function.arguments or "{}",
                },
            }
            for call in (message.tool_calls or [])
        ],
    }
    if message.content:
        payload["content"] = message.content
    return payload
