from __future__ import annotations

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_billing_documentation",
            "description": (
                "Search the indexed billing guide for policy, pricing, allowances, "
                "extra data charges, partial payments, disputes, late payments, and "
                "payment confirmation rules. Returns excerpts with section references. "
                "This is not the subscriber's live bill."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Natural-language search query.",
                    }
                },
                "required": ["query"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "query_bill",
            "description": (
                "Read the authenticated subscriber's calculated bill summary for one month "
                "through the API gateway. Returns total, paid amount, remaining balance, and status."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "month": {"type": "integer", "minimum": 1, "maximum": 12},
                    "year": {"type": "integer"},
                },
                "required": ["month", "year"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "query_bill_detailed",
            "description": (
                "Read the authenticated subscriber's usage and charge breakdown for one month "
                "through the API gateway. Use this when the user asks why a bill is high or wants minutes and data."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "month": {"type": "integer", "minimum": 1, "maximum": 12},
                    "year": {"type": "integer"},
                    "page": {"type": "integer", "minimum": 1},
                    "pageSize": {"type": "integer", "minimum": 1, "maximum": 100},
                },
                "required": ["month", "year"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "propose_bill_payment",
            "description": (
                "Prepare a simulated payment for the authenticated subscriber. "
                "Does not record the payment. After it succeeds, ask the user to reply CONFIRM. "
                "Use the remaining balance from query_bill when the user says to pay the bill."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "month": {"type": "integer", "minimum": 1, "maximum": 12},
                    "year": {"type": "integer"},
                    "amount": {"type": "number", "exclusiveMinimum": 0},
                },
                "required": ["month", "year", "amount"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "confirm_bill_payment",
            "description": (
                "Record the pending simulated payment through the API gateway. "
                "Call this only after the user's latest message explicitly says CONFIRM. "
                "Never call it in the same turn as the original pay request."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
                "additionalProperties": False,
            },
        },
    },
]
