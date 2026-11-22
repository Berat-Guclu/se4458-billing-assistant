from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field


class LoginIn(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    subscriber_no: Annotated[str, Field(alias="subscriberNo", min_length=1, max_length=32)]
    password: Annotated[str, Field(min_length=1, max_length=200)]


class TokenOut(BaseModel):
    accessToken: str
    tokenType: str
    expiresIn: int
    subscriberNo: str
    fullName: str
    role: str


class UsageIn(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    subscriber_no: Annotated[str, Field(alias="subscriberNo", min_length=1, max_length=32)]
    month: Annotated[int, Field(ge=1, le=12)]
    year: Annotated[int, Field(ge=2000, le=2100)]
    usage_type: Annotated[str, Field(alias="usageType", min_length=1, max_length=16)]


class UsageOut(BaseModel):
    transactionStatus: str
    subscriberNo: str
    month: int
    year: int
    usageType: str
    addedQuantity: int
    unit: str
    periodPhoneMinutes: int
    periodInternetMb: int


class CalculateIn(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    subscriber_no: Annotated[str, Field(alias="subscriberNo", min_length=1, max_length=32)]
    month: Annotated[int, Field(ge=1, le=12)]
    year: Annotated[int, Field(ge=2000, le=2100)]


class ChargeBreakdown(BaseModel):
    phoneMinutes: int
    phoneBlocks: int
    phoneCharge: float
    internetMb: int
    internetGb: float
    internetBaseCharge: float
    internetExtraBlocks: int
    internetExtraCharge: float
    internetCharge: float


class CalculateOut(BaseModel):
    transactionStatus: str
    subscriberNo: str
    month: int
    year: int
    currency: str
    billTotal: float
    paidAmount: float
    remainingBalance: float
    status: str
    charges: ChargeBreakdown


class QueryBillOut(BaseModel):
    subscriberNo: str
    month: int
    year: int
    currency: str
    billTotal: float
    paidAmount: float
    remainingBalance: float
    status: str


class UsageItem(BaseModel):
    id: int
    usageType: str
    quantity: int
    unit: str
    createdAt: str


class UsagePage(BaseModel):
    page: int
    pageSize: int
    totalItems: int
    totalPages: int
    items: list[UsageItem]


class DetailedOut(BaseModel):
    subscriberNo: str
    month: int
    year: int
    currency: str
    billTotal: float
    paidAmount: float
    remainingBalance: float
    status: str
    charges: ChargeBreakdown
    usage: UsagePage


class PayIn(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    subscriber_no: Annotated[str, Field(alias="subscriberNo", min_length=1, max_length=32)]
    month: Annotated[int, Field(ge=1, le=12)]
    year: Annotated[int, Field(ge=2000, le=2100)]
    amount: Annotated[Decimal, Field(gt=0, le=Decimal("1000000"))]
    transaction_id: Annotated[
        str,
        Field(alias="transactionId", min_length=1, max_length=64, pattern=r"^[A-Za-z0-9._:-]+$"),
    ]


class PayOut(BaseModel):
    paymentStatus: str
    billStatus: str
    subscriberNo: str
    month: int
    year: int
    currency: str
    amountApplied: float
    paidAmount: float
    remainingBalance: float
    transactionId: str
