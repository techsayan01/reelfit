"""Jury service: reviewer assignment, queues, and rubric scoring."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.jury.models import (
    AssignmentStatus,
    InternalNote,
    JuryAssignment,
    JuryScore,
    RubricCriterion,
)


def assign(db: Session, submission_id: int, juror_user_id: int) -> JuryAssignment:
    existing = db.scalar(
        select(JuryAssignment).where(
            JuryAssignment.submission_id == submission_id,
            JuryAssignment.juror_user_id == juror_user_id,
        )
    )
    if existing:
        return existing
    assignment = JuryAssignment(submission_id=submission_id, juror_user_id=juror_user_id)
    db.add(assignment)
    db.commit()
    return assignment


def queue_for_juror(db: Session, juror_user_id: int) -> list[JuryAssignment]:
    return list(
        db.scalars(
            select(JuryAssignment)
            .where(
                JuryAssignment.juror_user_id == juror_user_id,
                JuryAssignment.status != AssignmentStatus.DONE,
            )
            .order_by(JuryAssignment.created_at)
        )
    )


def record_score(db: Session, assignment_id: int, criterion_id: int, score: int) -> JuryScore:
    row = JuryScore(assignment_id=assignment_id, criterion_id=criterion_id, score=score)
    db.add(row)
    db.commit()
    return row


def criteria_for_festival(db: Session, festival_id: int) -> list[RubricCriterion]:
    return list(
        db.scalars(select(RubricCriterion).where(RubricCriterion.festival_id == festival_id))
    )


def add_internal_note(
    db: Session, submission_id: int, author_user_id: int, text: str
) -> InternalNote:
    note = InternalNote(submission_id=submission_id, author_user_id=author_user_id, text=text)
    db.add(note)
    db.commit()
    return note


def notes_for_submission(db: Session, submission_id: int) -> list[InternalNote]:
    return list(
        db.scalars(
            select(InternalNote)
            .where(InternalNote.submission_id == submission_id)
            .order_by(InternalNote.created_at.desc())
        )
    )
