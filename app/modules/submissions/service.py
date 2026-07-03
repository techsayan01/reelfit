"""Submissions service: the submission workflow.

Fee = category base fee + active deadline-tier delta, minus any waiver or
promo code, computed through the discounts service. Payment capture goes
through the payments service; notification through notifications.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.discounts import service as discounts
from app.modules.festivals import service as festivals
from app.modules.notifications import service as notifications
from app.modules.notifications.models import NotificationKind
from app.modules.payments import service as payments
from app.modules.submissions.models import Submission, SubmissionStatus


class SubmissionError(Exception):
    pass


def create_submission(
    db: Session,
    *,
    filmmaker_id: int,
    film_id: int,
    film_kind: str,
    film_runtime: int | None,
    film_year: int,
    film_title: str,
    festival_id: int,
    category_id: int,
    discount_code: str = "",
) -> Submission:
    festival = festivals.get_festival(db, festival_id)
    if festival is None:
        raise SubmissionError("Festival not found.")
    edition = festivals.current_edition(db, festival_id)
    if edition is None:
        raise SubmissionError(f"{festival.name} is not currently open for submissions.")

    category = next(
        (c for c in festivals.categories_for_edition(db, edition.id) if c.id == category_id),
        None,
    )
    if category is None:
        raise SubmissionError("That category does not exist for this edition.")
    if not festivals.eligible_category(category, film_kind, film_runtime, film_year):
        raise SubmissionError(
            f"“{film_title}” doesn't meet the {category.name} rules "
            f"({category.kind.value} category, runtime "
            f"{category.min_runtime_minutes}–{category.max_runtime_minutes} min"
            + (f", produced {category.min_production_year} or later" if category.min_production_year else "")
            + ")."
        )

    existing = db.scalar(
        select(Submission).where(
            Submission.film_id == film_id,
            Submission.edition_id == edition.id,
            Submission.category_id == category_id,
        )
    )
    if existing:
        raise SubmissionError("This film is already submitted to that category.")

    tier = festivals.active_deadline_tier(db, edition.id)
    fee = festivals.category_fee_cents(category, tier)

    applied_code = ""
    waiver = discounts.find_waiver(db, festival_id, filmmaker_id)
    if waiver:
        fee = 0
        waiver.used = 1
        applied_code = f"waiver:{waiver.reason}" if waiver.reason else "waiver"
    elif discount_code.strip():
        dc = discounts.find_valid_code(db, festival_id, discount_code, category_id)
        if dc is None:
            raise SubmissionError("That promo code isn't valid for this submission.")
        fee = discounts.apply_discount(fee, dc)
        discounts.redeem(db, dc)
        applied_code = dc.code

    submission = Submission(
        film_id=film_id,
        festival_id=festival_id,
        edition_id=edition.id,
        category_id=category_id,
        fee_paid_cents=fee,
        discount_code=applied_code,
        tracking_number=festivals.assign_tracking_number(db, festival_id),
    )
    db.add(submission)
    db.flush()

    if fee > 0:
        payments.record_submission_fee(db, filmmaker_id, submission.id, fee)

    notifications.notify(
        db,
        user_id=filmmaker_id,
        kind=NotificationKind.SUBMISSION_RECEIVED,
        subject=f"Your film “{film_title}” was sent to {festival.name}",
        body=f"Fee paid: ${fee / 100:.2f}. You'll hear back by the festival's notification date.",
    )
    db.commit()
    return submission


def submissions_for_films(db: Session, film_ids: list[int]) -> list[Submission]:
    if not film_ids:
        return []
    return list(
        db.scalars(
            select(Submission)
            .where(Submission.film_id.in_(film_ids))
            .order_by(Submission.created_at.desc())
        )
    )


def submissions_for_festival(db: Session, festival_id: int) -> list[Submission]:
    return list(
        db.scalars(
            select(Submission)
            .where(Submission.festival_id == festival_id)
            .order_by(Submission.created_at.desc())
        )
    )


def update_status(db: Session, submission_id: int, status: SubmissionStatus) -> Submission:
    submission = db.get(Submission, submission_id)
    if submission is None:
        raise SubmissionError("Submission not found.")
    submission.status = status
    db.commit()
    return submission


def revoke_relay(db: Session, submission_id: int, filmmaker_id: int) -> None:
    """Filmmaker revokes the festival's masked-contact access — no support
    intervention needed (BRD §5.2.1)."""
    submission = db.get(Submission, submission_id)
    if submission is None:
        raise SubmissionError("Submission not found.")
    submission.relay_revoked = True
    db.commit()
