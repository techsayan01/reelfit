from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class FitScore(Base):
    """A computed fit score for one film against one festival.

    Every score carries its calibration status so no score is ever presented
    as more certain than the underlying data supports (BRD §7.5).
    """

    __tablename__ = "fit_scores"

    id: Mapped[int] = mapped_column(primary_key=True)
    film_id: Mapped[int] = mapped_column(ForeignKey("films.id"), index=True)
    festival_id: Mapped[int] = mapped_column(ForeignKey("festivals.id"), index=True)
    score: Mapped[int] = mapped_column(Integer)  # 0-100
    confidence: Mapped[float] = mapped_column(Float)  # 0.0-1.0
    calibration_status: Mapped[str] = mapped_column(String(20))  # snapshot at scoring time
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
