from app.confirmation import payment_allowed, user_confirmed
from app.tool_schema import TOOLS


def test_confirm_word_is_explicit() -> None:
    assert user_confirmed("CONFIRM")
    assert user_confirmed("Please CONFIRM the payment")
    assert user_confirmed("onaylıyorum")
    assert not user_confirmed("yes")
    assert not user_confirmed("I want confirmation later")
    assert not user_confirmed("pay my bill")


def test_payment_requires_pending_and_confirm() -> None:
    pending = {"month": 10, "year": 2025, "amount": "70.00"}
    assert payment_allowed("CONFIRM", pending)
    assert not payment_allowed("CONFIRM", None)
    assert not payment_allowed("pay it", pending)


def test_tool_schema_cannot_target_another_subscriber() -> None:
    names = []
    for tool in TOOLS:
        function = tool["function"]
        names.append(function["name"])
        properties = function["parameters"]["properties"]
        assert "subscriberNo" not in properties
        assert "subscriber_no" not in properties
        assert function["parameters"]["additionalProperties"] is False
    assert names == [
        "search_billing_documentation",
        "query_bill",
        "query_bill_detailed",
        "propose_bill_payment",
        "confirm_bill_payment",
    ]
