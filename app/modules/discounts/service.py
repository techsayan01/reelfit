"""Discount service: fee computation with promo codes and waivers."""

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.discounts.models import DiscountCode, DiscountKind, FeeWaiver


def find_valid_code(
    db: Session, festival_id: int, code: str, category_id: int | None = None
) -> DiscountCode | None:
    dc = db.scalar(
        select(DiscountCode).where(
            DiscountCode.festival_id == festival_id,
            DiscountCode.code == code.strip().upper(),
        )
    )
    if dc is None:
        return None
    today = date.today()
    if dc.valid_from and today < dc.valid_from:
        return None
    if dc.valid_to and today > dc.valid_to:
        return None
    if dc.redemption_limit is not None and dc.redemptions >= dc.redemption_limit:
        return None
    if dc.category_id is not None and dc.category_id != category_id:
        return None
    return dc


def apply_discount(fee_cents: int, dc: DiscountCode) -> int:
    if dc.kind == DiscountKind.PERCENT:
        return max(0, fee_cents - (fee_cents * dc.amount) // 100)
    return max(0, fee_cents - dc.amount)


def redeem(db: Session, dc: DiscountCode) -> None:
    dc.redemptions += 1
    db.commit()


def find_waiver(db: Session, festival_id: int, filmmaker_id: int) -> FeeWaiver | None:
    return db.scalar(
        select(FeeWaiver).where(
            FeeWaiver.festival_id == festival_id,
            FeeWaiver.filmmaker_id == filmmaker_id,
            FeeWaiver.used == 0,
        )
    )
