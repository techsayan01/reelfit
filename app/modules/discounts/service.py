"""Discount service: code management, validation, and fee computation."""

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.discounts.models import (
    CodeRedemption,
    CodeType,
    DiscountCode,
    DiscountKind,
    FeeWaiver,
)


def find_valid_code(
    db: Session,
    festival_id: int,
    code: str,
    category_id: int | None = None,
    filmmaker_id: int | None = None,
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
    if dc.one_use_per_submitter and filmmaker_id is not None:
        already = db.scalar(
            select(CodeRedemption).where(
                CodeRedemption.code_id == dc.id,
                CodeRedemption.filmmaker_id == filmmaker_id,
            )
        )
        if already:
            return None
    return dc


def apply_code(fee_cents: int, dc: DiscountCode) -> int:
    if dc.code_type == CodeType.FEE_WAIVER:
        return 0
    if dc.code_type == CodeType.DEADLINE_WAIVER:
        return fee_cents  # grants late entry, not a price change
    if dc.kind == DiscountKind.PERCENT:
        return max(0, fee_cents - (fee_cents * dc.amount) // 100)
    return max(0, fee_cents - dc.amount)


def allows_late_entry(dc: DiscountCode) -> bool:
    return dc.code_type == CodeType.DEADLINE_WAIVER or dc.also_deadline_waiver


def redeem(db: Session, dc: DiscountCode, filmmaker_id: int | None = None) -> None:
    dc.redemptions += 1
    if filmmaker_id is not None:
        db.add(CodeRedemption(code_id=dc.id, filmmaker_id=filmmaker_id))
    db.commit()


def list_codes(db: Session, festival_id: int) -> list[DiscountCode]:
    return list(
        db.scalars(
            select(DiscountCode)
            .where(DiscountCode.festival_id == festival_id)
            .order_by(DiscountCode.id.desc())
        )
    )


def create_code(
    db: Session,
    festival_id: int,
    *,
    code: str,
    code_type: CodeType,
    label: str = "",
    kind: DiscountKind = DiscountKind.PERCENT,
    amount: int = 0,
    category_id: int | None = None,
    valid_from: date | None = None,
    valid_to: date | None = None,
    redemption_limit: int | None = None,
    also_deadline_waiver: bool = False,
    one_use_per_submitter: bool = False,
) -> DiscountCode:
    code = "".join(c for c in code.strip().upper() if c.isalnum())
    if not code:
        raise ValueError("Codes use letters and numbers only.")
    existing = db.scalar(
        select(DiscountCode).where(
            DiscountCode.festival_id == festival_id, DiscountCode.code == code
        )
    )
    if existing:
        raise ValueError(f"The code {code} already exists for this festival.")
    if code_type == CodeType.DISCOUNT:
        if kind == DiscountKind.PERCENT and not 1 <= amount <= 100:
            raise ValueError("Percentage discounts are 1–100%.")
        if kind == DiscountKind.FLAT and amount < 1:
            raise ValueError("Flat discounts need an amount.")
    dc = DiscountCode(
        festival_id=festival_id,
        code=code,
        code_type=code_type,
        label=label.strip(),
        kind=kind,
        amount=amount,
        category_id=category_id,
        valid_from=valid_from,
        valid_to=valid_to,
        redemption_limit=redemption_limit,
        also_deadline_waiver=also_deadline_waiver,
        one_use_per_submitter=one_use_per_submitter,
    )
    db.add(dc)
    db.commit()
    return dc


def delete_code(db: Session, code_id: int, festival_id: int) -> None:
    dc = db.get(DiscountCode, code_id)
    if dc is None or dc.festival_id != festival_id:
        raise ValueError("Code not found.")
    for r in db.scalars(select(CodeRedemption).where(CodeRedemption.code_id == code_id)):
        db.delete(r)
    db.delete(dc)
    db.commit()


def find_waiver(db: Session, festival_id: int, filmmaker_id: int) -> FeeWaiver | None:
    return db.scalar(
        select(FeeWaiver).where(
            FeeWaiver.festival_id == festival_id,
            FeeWaiver.filmmaker_id == filmmaker_id,
            FeeWaiver.used == 0,
        )
    )
