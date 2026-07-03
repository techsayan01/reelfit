import enum
from datetime import date

from sqlalchemy import Date, Enum, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class DiscountKind(str, enum.Enum):
    PERCENT = "percent"
    FLAT = "flat"


class DiscountCode(Base):
    """Promo code: percentage or flat, time-limited, optionally category-scoped."""

    __tablename__ = "discount_codes"

    id: Mapped[int] = mapped_column(primary_key=True)
    festival_id: Mapped[int] = mapped_column(ForeignKey("festivals.id"), index=True)
    code: Mapped[str] = mapped_column(String(60), index=True)
    kind: Mapped[DiscountKind] = mapped_column(Enum(DiscountKind))
    # Percent (0-100) for PERCENT, cents for FLAT.
    amount: Mapped[int] = mapped_column(Integer)
    category_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id"), nullable=True)
    valid_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    valid_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    redemption_limit: Mapped[int | None] = mapped_column(Integer, nullable=True)
    redemptions: Mapped[int] = mapped_column(Integer, default=0)


class FeeWaiver(Base):
    """Full fee waiver granted to a specific filmmaker (outreach, diversity, partners)."""

    __tablename__ = "fee_waivers"

    id: Mapped[int] = mapped_column(primary_key=True)
    festival_id: Mapped[int] = mapped_column(ForeignKey("festivals.id"), index=True)
    filmmaker_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    reason: Mapped[str] = mapped_column(String(255), default="")
    used: Mapped[int] = mapped_column(Integer, default=0)
