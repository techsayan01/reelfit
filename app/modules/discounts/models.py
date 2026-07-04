import enum
from datetime import date, datetime, timezone

from sqlalchemy import Boolean, Date, DateTime, Enum, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class DiscountKind(str, enum.Enum):
    PERCENT = "percent"
    FLAT = "flat"


class CodeType(str, enum.Enum):
    """What a code grants (BRD §5.1.2 discount/waiver configuration)."""

    DISCOUNT = "discount"            # reduced entry fee
    FEE_WAIVER = "fee_waiver"        # free entry
    DEADLINE_WAIVER = "deadline_waiver"  # late entry after the final deadline


class DiscountCode(Base):
    """Promo code: percentage or flat discount, full fee waiver, or deadline
    waiver. Time-limited, optionally category-scoped, optionally capped."""

    __tablename__ = "discount_codes"

    id: Mapped[int] = mapped_column(primary_key=True)
    festival_id: Mapped[int] = mapped_column(ForeignKey("festivals.id"), index=True)
    code: Mapped[str] = mapped_column(String(60), index=True)
    code_type: Mapped[CodeType] = mapped_column(Enum(CodeType), default=CodeType.DISCOUNT)
    # Internal label, never shown to filmmakers.
    label: Mapped[str] = mapped_column(String(120), default="")
    kind: Mapped[DiscountKind] = mapped_column(Enum(DiscountKind), default=DiscountKind.PERCENT)
    # Percent (0-100) for PERCENT, cents for FLAT. Unused for waiver types.
    amount: Mapped[int] = mapped_column(Integer, default=0)
    category_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id"), nullable=True)
    valid_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    valid_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    redemption_limit: Mapped[int | None] = mapped_column(Integer, nullable=True)
    redemptions: Mapped[int] = mapped_column(Integer, default=0)
    # A discount code that also lets the holder submit past the final deadline.
    also_deadline_waiver: Mapped[bool] = mapped_column(Boolean, default=False)
    one_use_per_submitter: Mapped[bool] = mapped_column(Boolean, default=False)


class CodeRedemption(Base):
    """Who redeemed which code — powers one-use-per-submitter enforcement."""

    __tablename__ = "code_redemptions"

    id: Mapped[int] = mapped_column(primary_key=True)
    code_id: Mapped[int] = mapped_column(ForeignKey("discount_codes.id"), index=True)
    filmmaker_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class FeeWaiver(Base):
    """Full fee waiver granted to a specific filmmaker (outreach, diversity,
    partners) — person-scoped, unlike code-based waivers."""

    __tablename__ = "fee_waivers"

    id: Mapped[int] = mapped_column(primary_key=True)
    festival_id: Mapped[int] = mapped_column(ForeignKey("festivals.id"), index=True)
    filmmaker_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    reason: Mapped[str] = mapped_column(String(255), default="")
    used: Mapped[int] = mapped_column(Integer, default=0)
