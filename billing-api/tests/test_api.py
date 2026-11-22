from __future__ import annotations

import os
from datetime import datetime, timezone

os.environ["SEED_ON_STARTUP"] = "false"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import get_db
from app.main import app
from app.models import Base, Subscriber, UsageEvent
from app.security import hash_password


@pytest.fixture()
def session_factory():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    db = factory()
    now = datetime.now(timezone.utc)
    for subscriber_no, full_name, password, role in (
        ("5551001", "Ece Yilmaz", "demo123", "SUBSCRIBER"),
        ("5551002", "Kerem Acar", "demo123", "SUBSCRIBER"),
        ("5551999", "Billing Admin", "admin123", "ADMIN"),
    ):
        db.add(
            Subscriber(
                subscriber_no=subscriber_no,
                full_name=full_name,
                password_hash=hash_password(password),
                role=role,
                created_at=now,
            )
        )
    db.commit()
    db.close()

    def override_db():
        db = factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_db
    yield factory
    app.dependency_overrides.clear()
    Base.metadata.drop_all(engine)


@pytest.fixture()
def client(session_factory):
    with TestClient(app) as test_client:
        yield test_client


def login(client: TestClient, subscriber_no: str = "5551001", password: str = "demo123") -> str:
    response = client.post(
        "/api/v1/auth/login",
        json={"subscriberNo": subscriber_no, "password": password},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["tokenType"] == "Bearer"
    assert body["subscriberNo"] == subscriber_no
    return body["accessToken"]


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def add_ledger(factory, subscriber_no: str, month: int, year: int, usage_type: str, quantity: int) -> None:
    db = factory()
    db.add(
        UsageEvent(
            subscriber_no=subscriber_no,
            month=month,
            year=year,
            usage_type=usage_type,
            quantity=quantity,
            created_at=datetime.now(timezone.utc),
        )
    )
    db.commit()
    db.close()


def test_health(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_login_failure(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/login",
        json={"subscriberNo": "5551001", "password": "wrong"},
    )
    assert response.status_code == 401


def test_add_usage_success_and_validation(client: TestClient) -> None:
    token = login(client)
    phone = client.post(
        "/api/v1/usage",
        headers=auth(token),
        json={"subscriberNo": "5551001", "month": 11, "year": 2025, "usageType": "PHONE"},
    )
    assert phone.status_code == 200, phone.text
    assert phone.json()["transactionStatus"] == "RECORDED"
    assert phone.json()["addedQuantity"] == 10
    assert phone.json()["unit"] == "minutes"
    assert phone.json()["periodPhoneMinutes"] == 10

    internet = client.post(
        "/api/v1/usage",
        headers=auth(token),
        json={"subscriberNo": "5551001", "month": 11, "year": 2025, "usageType": "internet"},
    )
    assert internet.status_code == 200, internet.text
    assert internet.json()["addedQuantity"] == 1
    assert internet.json()["periodInternetMb"] == 1

    second_phone = client.post(
        "/api/v1/usage",
        headers=auth(token),
        json={"subscriberNo": "5551001", "month": 11, "year": 2025, "usageType": "PHONE"},
    )
    assert second_phone.json()["periodPhoneMinutes"] == 20

    rejected = client.post(
        "/api/v1/usage",
        headers=auth(token),
        json={"subscriberNo": "5551001", "month": 11, "year": 2025, "usageType": "SMS"},
    )
    assert rejected.status_code == 400

    missing = client.post("/api/v1/usage", json={"subscriberNo": "5551001", "month": 11, "year": 2025, "usageType": "PHONE"})
    assert missing.status_code == 401

    other = client.post(
        "/api/v1/usage",
        headers=auth(token),
        json={"subscriberNo": "5551002", "month": 11, "year": 2025, "usageType": "PHONE"},
    )
    assert other.status_code == 403

    invalid_month = client.post(
        "/api/v1/usage",
        headers=auth(token),
        json={"subscriberNo": "5551001", "month": 13, "year": 2025, "usageType": "PHONE"},
    )
    assert invalid_month.status_code == 422


def test_calculate_query_and_boundaries(client: TestClient, session_factory) -> None:
    add_ledger(session_factory, "5551001", 10, 2025, "PHONE", 800)
    add_ledger(session_factory, "5551001", 10, 2025, "INTERNET", 35000)
    token = login(client)

    missing_token = client.post(
        "/api/v1/bills/calculate",
        json={"subscriberNo": "5551001", "month": 10, "year": 2025},
    )
    assert missing_token.status_code == 401

    hidden_subscriber = client.post(
        "/api/v1/bills/calculate",
        headers=auth(token),
        json={"subscriberNo": "0000000", "month": 10, "year": 2025},
    )
    assert hidden_subscriber.status_code == 403

    admin = login(client, "5551999", "admin123")
    unknown = client.post(
        "/api/v1/bills/calculate",
        headers=auth(admin),
        json={"subscriberNo": "0000000", "month": 10, "year": 2025},
    )
    assert unknown.status_code == 404

    forbidden = client.post(
        "/api/v1/bills/calculate",
        headers=auth(token),
        json={"subscriberNo": "5551002", "month": 10, "year": 2025},
    )
    assert forbidden.status_code == 403

    calculated = client.post(
        "/api/v1/bills/calculate",
        headers=auth(token),
        json={"subscriberNo": "5551001", "month": 10, "year": 2025},
    )
    assert calculated.status_code == 200, calculated.text
    body = calculated.json()
    assert body["transactionStatus"] == "CALCULATED"
    assert body["billTotal"] == 70
    assert body["paidAmount"] == 0
    assert body["remainingBalance"] == 70
    assert body["status"] == "UNPAID"
    assert body["charges"]["phoneMinutes"] == 800
    assert body["charges"]["phoneCharge"] == 0
    assert body["charges"]["internetMb"] == 35000
    assert body["charges"]["internetGb"] == 35
    assert body["charges"]["internetExtraBlocks"] == 2
    assert body["charges"]["internetCharge"] == 70

    queried = client.get("/api/v1/bills", params={"subscriberNo": "5551001", "month": 10, "year": 2025})
    assert queried.status_code == 200
    assert queried.json()["billTotal"] == 70
    assert queried.json()["status"] == "UNPAID"

    not_found = client.get("/api/v1/bills", params={"subscriberNo": "5551001", "month": 1, "year": 2024})
    assert not_found.status_code == 404

    bad_query = client.get("/api/v1/bills", params={"subscriberNo": "5551001", "month": 0, "year": 2025})
    assert bad_query.status_code == 422


def test_zero_usage_still_includes_internet_plan(client: TestClient) -> None:
    token = login(client)
    response = client.post(
        "/api/v1/bills/calculate",
        headers=auth(token),
        json={"subscriberNo": "5551001", "month": 8, "year": 2025},
    )
    assert response.status_code == 200, response.text
    assert response.json()["charges"]["phoneCharge"] == 0
    assert response.json()["charges"]["internetCharge"] == 50
    assert response.json()["billTotal"] == 50
    assert response.json()["status"] == "UNPAID"


def test_detailed_bill_requires_auth_and_pages(client: TestClient, session_factory) -> None:
    for quantity in (500, 300, 20000, 10000, 5000):
        usage_type = "PHONE" if quantity < 1000 else "INTERNET"
        add_ledger(session_factory, "5551001", 10, 2025, usage_type, quantity)
    token = login(client)
    client.post(
        "/api/v1/bills/calculate",
        headers=auth(token),
        json={"subscriberNo": "5551001", "month": 10, "year": 2025},
    )

    hidden = client.get(
        "/api/v1/bills/detailed",
        params={"subscriberNo": "5551001", "month": 10, "year": 2025},
    )
    assert hidden.status_code == 401

    other = login(client, "5551002")
    forbidden = client.get(
        "/api/v1/bills/detailed",
        headers=auth(other),
        params={"subscriberNo": "5551001", "month": 10, "year": 2025},
    )
    assert forbidden.status_code == 403

    page = client.get(
        "/api/v1/bills/detailed",
        headers=auth(token),
        params={"subscriberNo": "5551001", "month": 10, "year": 2025, "page": 2, "pageSize": 2},
    )
    assert page.status_code == 200, page.text
    body = page.json()
    assert body["usage"]["totalItems"] == 5
    assert body["usage"]["totalPages"] == 3
    assert body["usage"]["page"] == 2
    assert len(body["usage"]["items"]) == 2
    assert body["charges"]["internetCharge"] == 70

    admin = login(client, "5551999", "admin123")
    allowed = client.get(
        "/api/v1/bills/detailed",
        headers=auth(admin),
        params={"subscriberNo": "5551001", "month": 10, "year": 2025, "pageSize": 10},
    )
    assert allowed.status_code == 200
    assert len(allowed.json()["usage"]["items"]) == 5


def test_pay_success_duplicate_and_overpay(client: TestClient, session_factory) -> None:
    add_ledger(session_factory, "5551001", 10, 2025, "INTERNET", 35000)
    token = login(client)
    client.post(
        "/api/v1/bills/calculate",
        headers=auth(token),
        json={"subscriberNo": "5551001", "month": 10, "year": 2025},
    )

    unauthenticated = client.post(
        "/api/v1/bills/pay",
        json={
            "subscriberNo": "5551001",
            "month": 10,
            "year": 2025,
            "amount": 20,
            "transactionId": "txn-unauth",
        },
    )
    assert unauthenticated.status_code == 401

    not_ready = client.post(
        "/api/v1/bills/pay",
        headers=auth(token),
        json={
            "subscriberNo": "5551001",
            "month": 3,
            "year": 2025,
            "amount": 10,
            "transactionId": "txn-missing-bill",
        },
    )
    assert not_ready.status_code == 404

    too_much = client.post(
        "/api/v1/bills/pay",
        headers=auth(token),
        json={
            "subscriberNo": "5551001",
            "month": 10,
            "year": 2025,
            "amount": 70.01,
            "transactionId": "txn-over",
        },
    )
    assert too_much.status_code == 400

    cents = client.post(
        "/api/v1/bills/pay",
        headers=auth(token),
        json={
            "subscriberNo": "5551001",
            "month": 10,
            "year": 2025,
            "amount": 10.999,
            "transactionId": "txn-cents",
        },
    )
    assert cents.status_code == 400

    zero = client.post(
        "/api/v1/bills/pay",
        headers=auth(token),
        json={
            "subscriberNo": "5551001",
            "month": 10,
            "year": 2025,
            "amount": 0,
            "transactionId": "txn-zero",
        },
    )
    assert zero.status_code == 422

    partial = client.post(
        "/api/v1/bills/pay",
        headers=auth(token),
        json={
            "subscriberNo": "5551001",
            "month": 10,
            "year": 2025,
            "amount": 20,
            "transactionId": "txn-partial",
        },
    )
    assert partial.status_code == 200, partial.text
    assert partial.json()["paymentStatus"] == "ACCEPTED"
    assert partial.json()["billStatus"] == "PARTIAL"
    assert partial.json()["amountApplied"] == 20
    assert partial.json()["paidAmount"] == 20
    assert partial.json()["remainingBalance"] == 50

    duplicate = client.post(
        "/api/v1/bills/pay",
        headers=auth(token),
        json={
            "subscriberNo": "5551001",
            "month": 10,
            "year": 2025,
            "amount": 20,
            "transactionId": "txn-partial",
        },
    )
    assert duplicate.status_code == 409

    other = login(client, "5551002")
    stolen = client.post(
        "/api/v1/bills/pay",
        headers=auth(other),
        json={
            "subscriberNo": "5551001",
            "month": 10,
            "year": 2025,
            "amount": 10,
            "transactionId": "txn-stolen",
        },
    )
    assert stolen.status_code == 403

    final = client.post(
        "/api/v1/bills/pay",
        headers=auth(token),
        json={
            "subscriberNo": "5551001",
            "month": 10,
            "year": 2025,
            "amount": 50,
            "transactionId": "txn-final",
        },
    )
    assert final.status_code == 200, final.text
    assert final.json()["billStatus"] == "PAID"
    assert final.json()["remainingBalance"] == 0

    again = client.post(
        "/api/v1/bills/pay",
        headers=auth(token),
        json={
            "subscriberNo": "5551001",
            "month": 10,
            "year": 2025,
            "amount": 1,
            "transactionId": "txn-after-paid",
        },
    )
    assert again.status_code == 400

    summary = client.get("/api/v1/bills", params={"subscriberNo": "5551001", "month": 10, "year": 2025})
    assert summary.json()["status"] == "PAID"
    assert summary.json()["paidAmount"] == 70


def test_recalculate_cannot_drop_below_payments(client: TestClient, session_factory) -> None:
    add_ledger(session_factory, "5551001", 6, 2025, "INTERNET", 35000)
    token = login(client)
    created = client.post(
        "/api/v1/bills/calculate",
        headers=auth(token),
        json={"subscriberNo": "5551001", "month": 6, "year": 2025},
    )
    assert created.json()["billTotal"] == 70
    paid = client.post(
        "/api/v1/bills/pay",
        headers=auth(token),
        json={
            "subscriberNo": "5551001",
            "month": 6,
            "year": 2025,
            "amount": 70,
            "transactionId": "txn-full-june",
        },
    )
    assert paid.status_code == 200

    db = session_factory()
    db.query(UsageEvent).filter(UsageEvent.month == 6).delete()
    db.commit()
    db.close()

    recalculated = client.post(
        "/api/v1/bills/calculate",
        headers=auth(token),
        json={"subscriberNo": "5551001", "month": 6, "year": 2025},
    )
    assert recalculated.status_code == 409


def test_openapi_lists_versioned_operations(client: TestClient) -> None:
    spec = client.get("/openapi.json")
    assert spec.status_code == 200
    paths = spec.json()["paths"]
    for path in (
        "/api/v1/auth/login",
        "/api/v1/usage",
        "/api/v1/bills",
        "/api/v1/bills/detailed",
        "/api/v1/bills/calculate",
        "/api/v1/bills/pay",
    ):
        assert path in paths
    assert "bearer" in spec.json()["components"]["securitySchemes"]["HTTPBearer"]["scheme"]
