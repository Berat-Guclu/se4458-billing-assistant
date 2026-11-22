from __future__ import annotations

import os
from pathlib import Path

import httpx
import jwt
from fastapi import FastAPI, Header, HTTPException
from fastapi.staticfiles import StaticFiles
from jwt import InvalidTokenError
from pydantic import BaseModel, Field

from .orchestrator import answer_question

app = FastAPI(title="Mobile Provider Billing Assistant", version="1.0.0")
STATIC = Path(__file__).resolve().parent / "static"


class LoginIn(BaseModel):
    subscriberNo: str = Field(min_length=1, max_length=32)
    password: str = Field(min_length=1, max_length=200)


class HistoryItem(BaseModel):
    role: str
    content: str = ""


class ChatIn(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    history: list[HistoryItem] = Field(default_factory=list)


def gateway_base() -> str:
    return os.getenv("GATEWAY_BASE_URL", "http://localhost:8088").rstrip("/")


def decode_identity(authorization: str | None) -> dict:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    token = authorization.split(" ", 1)[1].strip()
    try:
        payload = jwt.decode(
            token,
            os.getenv("JWT_SECRET", "billing-demo-secret-key-please-change"),
            algorithms=["HS256"],
            issuer=os.getenv("JWT_ISSUER", "billing-key"),
            options={"require": ["exp", "sub", "iss"]},
        )
    except InvalidTokenError as exc:
        raise HTTPException(status_code=401, detail="Invalid or expired token") from exc
    return {"token": token, "subscriberNo": payload["sub"], "fullName": payload.get("name", payload["sub"]), "role": payload.get("role", "SUBSCRIBER")}


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "service": "agent"}


@app.post("/api/login")
async def login(body: LoginIn) -> dict:
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(
                gateway_base() + "/api/v1/auth/login",
                json={"subscriberNo": body.subscriberNo, "password": body.password},
            )
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail="API gateway is unavailable") from exc
    if response.status_code >= 400:
        detail: object
        try:
            detail = response.json().get("detail", response.text)
        except Exception:
            detail = response.text
        raise HTTPException(status_code=response.status_code, detail=detail)
    return response.json()


@app.post("/api/chat")
async def chat(body: ChatIn, authorization: str | None = Header(default=None)) -> dict:
    identity = decode_identity(authorization)
    try:
        return await answer_question(
            token=identity["token"],
            subscriber_no=identity["subscriberNo"],
            full_name=identity["fullName"],
            message=body.message.strip(),
            history=[item.model_dump() for item in body.history],
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


app.mount("/", StaticFiles(directory=str(STATIC), html=True), name="ui")
