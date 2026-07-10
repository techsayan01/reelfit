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
from app.modules.festivals.models import QuestionType
from app.modules.submissions.models import (
    CustomAnswer,
    StatusChange,
    Submission,
    SubmissionStatus,
)


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
    cover_letter: str = "",
    answers: dict[int, str] | None = None,
    source: str = "direct",
) -> Submission:
    festival = festivals.get_festival(db, festival_id)
    if festival is None:
        raise SubmissionError("Festival not found.")
    edition = festivals.current_edition(db, festival_id)
    late_entry = False
    if edition is None:
        # Past the final deadline: a deadline-waiver code can still get the
        # film in during the festival's waiver window.
        edition = festivals.waiver_window_edition(db, festival_id)
        if edition is None:
            raise SubmissionError(f"{festival.name} is not currently open for submissions.")
        late_entry = True
        late_code = discounts.find_valid_code(
            db, festival_id, discount_code, category_id, filmmaker_id
        ) if discount_code.strip() else None
        if late_code is None or not discounts.allows_late_entry(late_code):
            raise SubmissionError(
                f"{festival.name}'s final deadline has passed — submitting now "
                "needs a valid deadline waiver code."
            )

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

    # Custom submission form: every applicable question needs an answer.
    answers = answers or {}
    questions = festivals.questions_for_category(db, festival_id, category_id)
    for q in questions:
        answer = (answers.get(q.id) or "").strip()
        if not answer:
            raise SubmissionError(f"Please answer: “{q.question}”")
        if q.field_type == QuestionType.DROPDOWN and answer not in q.options_list():
            raise SubmissionError(f"Pick one of the options for “{q.question}”.")
        if q.field_type == QuestionType.YES_NO and answer not in ("Yes", "No"):
            raise SubmissionError(f"Answer yes or no to “{q.question}”.")

    tier = festivals.active_deadline_tier(db, edition.id)
    if tier is None and late_entry:
        # Late entries pay the final (most expensive) tier.
        all_tiers = festivals.all_deadline_tiers(db, edition.id)
        tier = all_tiers[-1] if all_tiers else None
    fee = festivals.category_fee_cents(category, tier)

    applied_code = ""
    waiver = None if late_entry else discounts.find_waiver(db, festival_id, filmmaker_id)
    if waiver:
        fee = 0
        waiver.used = 1
        applied_code = f"waiver:{waiver.reason}" if waiver.reason else "waiver"
    elif discount_code.strip():
        dc = discounts.find_valid_code(
            db, festival_id, discount_code, category_id, filmmaker_id
        )
        if dc is None:
            raise SubmissionError("That promo code isn't valid for this submission.")
        fee = discounts.apply_code(fee, dc)
        discounts.redeem(db, dc, filmmaker_id)
        applied_code = dc.code

    submission = Submission(
        film_id=film_id,
        festival_id=festival_id,
        edition_id=edition.id,
        category_id=category_id,
        fee_paid_cents=fee,
        discount_code=applied_code,
        tracking_number=festivals.assign_tracking_number(db, festival_id),
        cover_letter=cover_letter.strip(),
        source="".join(c for c in source.strip().lower() if c.isalnum() or c in "-_")[:60] or "direct",
    )
    db.add(submission)
    db.flush()

    for q in questions:
        db.add(CustomAnswer(
            submission_id=submission.id,
            question_id=q.id,
            answer=answers[q.id].strip(),
        ))

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


def update_status(
    db: Session,
    submission_id: int,
    status: SubmissionStatus,
    actor_user_id: int | None = None,
) -> Submission:
    submission = db.get(Submission, submission_id)
    if submission is None:
        raise SubmissionError("Submission not found.")
    if submission.status != status:
        db.add(StatusChange(
            submission_id=submission_id,
            actor_user_id=actor_user_id,
            from_status=submission.status.value,
            to_status=status.value,
        ))
    submission.status = status
    db.commit()
    return submission


def status_log(db: Session, submission_id: int) -> list[StatusChange]:
    return list(
        db.scalars(
            select(StatusChange)
            .where(StatusChange.submission_id == submission_id)
            .order_by(StatusChange.created_at.desc())
        )
    )


def get_submission(db: Session, submission_id: int) -> Submission | None:
    return db.get(Submission, submission_id)


def answers_for_submission(db: Session, submission_id: int) -> list[CustomAnswer]:
    return list(
        db.scalars(
            select(CustomAnswer).where(CustomAnswer.submission_id == submission_id)
        )
    )


def delete_answers_for_question(db: Session, question_id: int) -> None:
    for a in db.scalars(
        select(CustomAnswer).where(CustomAnswer.question_id == question_id)
    ):
        db.delete(a)
    db.commit()


def set_flag(db: Session, submission_id: int, flag_id: int | None) -> None:
    submission = db.get(Submission, submission_id)
    if submission is None:
        raise SubmissionError("Submission not found.")
    submission.flag_id = flag_id
    db.commit()


def clear_flag(db: Session, flag_id: int) -> None:
    """Unset a flag from every submission before its definition is deleted."""
    for s in db.scalars(select(Submission).where(Submission.flag_id == flag_id)):
        s.flag_id = None
    db.commit()


def revoke_relay(db: Session, submission_id: int, filmmaker_id: int) -> None:
    """Filmmaker revokes the festival's masked-contact access — no support
    intervention needed (BRD §5.2.1)."""
    submission = db.get(Submission, submission_id)
    if submission is None:
        raise SubmissionError("Submission not found.")
    submission.relay_revoked = True
    db.commit()
