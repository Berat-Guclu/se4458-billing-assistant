from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Subscriber(Base):
    __tablename__ = "subscribers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    subscriber_no: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, index=True)
    full_name: Mapped[str] = mapped_column(String(120), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(200), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False, default="SUBSCRIBER")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    usage_events: Mapped[list["UsageEvent"]] = relationship(back_populates="subscriber")
    bills: Mapped[list["Bill"]] = relationship(back_populates="subscriber")


class UsageEvent(Base):
    __tablename__ = "usage_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    subscriber_no: Mapped[str] = mapped_column(
        String(32), ForeignKey("subscribers.subscriber_no"), nullable=False, index=True
    )
    month: Mapped[int] = mapped_column(Integer, nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    usage_type: Mapped[str] = mapped_column(String(16), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    subscriber: Mapped[Subscriber] = relationship(back_populates="usage_events")


class Bill(Base):
    __tablename__ = "bills"
    __table_args__ = (UniqueConstraint("subscriber_no", "month", "year", name="uq_bill_period"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    subscriber_no: Mapped[str] = mapped_column(
        String(32), ForeignKey("subscribers.subscriber_no"), nullable=False, index=True
    )
    month: Mapped[int] = mapped_column(Integer, nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    phone_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    internet_mb: Mapped[int] = mapped_column(Integer, nullable=False)
    phone_charge: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    internet_charge: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    total_amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    paid_amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    calculated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    subscriber: Mapped[Subscriber] = relationship(back_populates="bills")
    payments: Mapped[list["Payment"]] = relationship(back_populates="bill")


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    bill_id: Mapped[int] = mapped_column(ForeignKey("bills.id"), nullable=False, index=True)
    subscriber_no: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    month: Mapped[int] = mapped_column(Integer, nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    transaction_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    bill: Mapped[Bill] = relationship(back_populates="payments")
