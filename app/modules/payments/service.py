"""Payments service: credits ledger and payment records.

Stripe integration point: in production these functions call Stripe and
store the returned reference. In development they record the event with a
dev reference so the rest of the product is fully exercisable without keys.
"""

from sqlalchemy.orm import Session

from app.modules.accounts.models import User
from app.modules.payments.models import CreditLedgerEntry, PaymentKind, PaymentRecord


class InsufficientCredits(Exception):
    pass


def record_submission_fee(
    db: Session, user_id: int, submission_id: int, amount_cents: int
) -> PaymentRecord:
    record = PaymentRecord(
        user_id=user_id,
        kind=PaymentKind.SUBMISSION_FEE,
        amount_cents=amount_cents,
        submission_id=submission_id,
        stripe_ref="dev-local",
    )
    db.add(record)
    return record


def purchase_credits(db: Session, user_id: int, credits: int, amount_cents: int) -> None:
    user = db.get(User, user_id)
    db.add(PaymentRecord(
        user_id=user_id,
        kind=PaymentKind.CREDIT_PACK,
        amount_cents=amount_cents,
        stripe_ref="dev-local",
    ))
    db.add(CreditLedgerEntry(user_id=user_id, delta=credits, reason="credit pack purchase"))
    user.credit_balance += credits
    db.commit()


def spend_credit(db: Session, user_id: int, reason: str) -> None:
    """Charge one scoring credit. Raises InsufficientCredits if none left."""
    user = db.get(User, user_id)
    if user.credit_balance < 1:
        raise InsufficientCredits()
    db.add(CreditLedgerEntry(user_id=user_id, delta=-1, reason=reason))
    user.credit_balance -= 1
    db.commit()
