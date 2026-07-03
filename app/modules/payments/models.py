import enum
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class PaymentKind(str, enum.Enum):
    SUBMISSION_FEE = "submission_fee"
    CREDIT_PACK = "credit_pack"
    FESTIVAL_LICENSE = "festival_license"
    REFUND = "refund"


class PaymentRecord(Base):
    """A payment event. Phase 1 records Stripe references; the Stripe call
    itself lives behind the payments service so a dev/fake provider can be
    swapped in locally."""

    __tablename__ = "payment_records"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    kind: Mapped[PaymentKind] = mapped_column(Enum(PaymentKind))
    amount_cents: Mapped[int] = mapped_column(Integer)
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    stripe_ref: Mapped[str] = mapped_column(String(255), default="")
    submission_id: Mapped[int | None] = mapped_column(
        ForeignKey("submissions.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class CreditLedgerEntry(Base):
    """Append-only ledger of scoring-credit changes; balance on User is a
    cached sum maintained by the payments service."""

    __tablename__ = "credit_ledger"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    delta: Mapped[int] = mapped_column(Integer)  # +N purchase, -1 per film scored
    reason: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
