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


def unassign(db: Session, submission_id: int, juror_user_id: int) -> None:
    assignment = db.scalar(
        select(JuryAssignment).where(
            JuryAssignment.submission_id == submission_id,
            JuryAssignment.juror_user_id == juror_user_id,
        )
    )
    if assignment is None:
        return
    for score in db.scalars(
        select(JuryScore).where(JuryScore.assignment_id == assignment.id)
    ):
        db.delete(score)
    db.delete(assignment)
    db.commit()


def assignments_for_submission(db: Session, submission_id: int) -> list[JuryAssignment]:
    return list(
        db.scalars(
            select(JuryAssignment).where(JuryAssignment.submission_id == submission_id)
        )
    )


def record_scores(
    db: Session, assignment_id: int, scores: dict[int, int]
) -> None:
    """Upsert a juror's rubric scores and mark the assignment done."""
    existing = {
        s.criterion_id: s
        for s in db.scalars(
            select(JuryScore).where(JuryScore.assignment_id == assignment_id)
        )
    }
    for criterion_id, score in scores.items():
        if criterion_id in existing:
            existing[criterion_id].score = score
        else:
            db.add(JuryScore(
                assignment_id=assignment_id, criterion_id=criterion_id, score=score
            ))
    assignment = db.get(JuryAssignment, assignment_id)
    assignment.status = AssignmentStatus.DONE
    db.commit()


def scores_for_assignment(db: Session, assignment_id: int) -> dict[int, int]:
    return {
        s.criterion_id: s.score
        for s in db.scalars(
            select(JuryScore).where(JuryScore.assignment_id == assignment_id)
        )
    }


def rating_summary(
    db: Session, submission_id: int, criteria: list[RubricCriterion]
) -> tuple[float | None, int]:
    """Weighted average rating across jurors who scored: (average, judge count)."""
    weights = {c.id: c.weight for c in criteria}
    per_juror: list[float] = []
    for assignment in assignments_for_submission(db, submission_id):
        scores = scores_for_assignment(db, assignment.id)
        scored = {cid: s for cid, s in scores.items() if cid in weights}
        if not scored:
            continue
        total_weight = sum(weights[cid] for cid in scored)
        if total_weight == 0:
            continue
        per_juror.append(
            sum(s * weights[cid] for cid, s in scored.items()) / total_weight
        )
    if not per_juror:
        return None, 0
    return round(sum(per_juror) / len(per_juror), 1), len(per_juror)


def criteria_for_festival(db: Session, festival_id: int) -> list[RubricCriterion]:
    return list(
        db.scalars(select(RubricCriterion).where(RubricCriterion.festival_id == festival_id))
    )


def add_criterion(db: Session, festival_id: int, name: str, weight: float) -> RubricCriterion:
    criterion = RubricCriterion(festival_id=festival_id, name=name.strip(), weight=weight)
    db.add(criterion)
    db.commit()
    return criterion


def delete_criterion(db: Session, criterion_id: int, festival_id: int) -> None:
    criterion = db.get(RubricCriterion, criterion_id)
    if criterion is None or criterion.festival_id != festival_id:
        raise ValueError("Criterion not found")
    for score in db.scalars(
        select(JuryScore).where(JuryScore.criterion_id == criterion_id)
    ):
        db.delete(score)
    db.delete(criterion)
    db.commit()


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
