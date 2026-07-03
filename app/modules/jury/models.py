import enum
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class AssignmentStatus(str, enum.Enum):
    PENDING = "pending"
    IN_REVIEW = "in_review"
    DONE = "done"


class RubricCriterion(Base):
    """Festival-configured scoring criterion with weighting (BRD §5.1.3)."""

    __tablename__ = "rubric_criteria"

    id: Mapped[int] = mapped_column(primary_key=True)
    festival_id: Mapped[int] = mapped_column(ForeignKey("festivals.id"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    weight: Mapped[float] = mapped_column(Float, default=1.0)


class JuryAssignment(Base):
    """A submission assigned to a juror for review (workload distribution)."""

    __tablename__ = "jury_assignments"
    __table_args__ = (UniqueConstraint("submission_id", "juror_user_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    submission_id: Mapped[int] = mapped_column(ForeignKey("submissions.id"), index=True)
    juror_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    status: Mapped[AssignmentStatus] = mapped_column(
        Enum(AssignmentStatus), default=AssignmentStatus.PENDING
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class JuryScore(Base):
    """A juror's score against one rubric criterion for one submission."""

    __tablename__ = "jury_scores"
    __table_args__ = (UniqueConstraint("assignment_id", "criterion_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    assignment_id: Mapped[int] = mapped_column(ForeignKey("jury_assignments.id"), index=True)
    criterion_id: Mapped[int] = mapped_column(ForeignKey("rubric_criteria.id"))
    score: Mapped[int] = mapped_column(Integer)  # 1-10


class InternalNote(Base):
    """Jury-only note on a submission; never visible to the filmmaker (BRD §5.1.3)."""

    __tablename__ = "internal_notes"

    id: Mapped[int] = mapped_column(primary_key=True)
    submission_id: Mapped[int] = mapped_column(ForeignKey("submissions.id"), index=True)
    author_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    text: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
