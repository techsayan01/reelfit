from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Review(Base):
    """Filmmaker review of a festival, tied to a real submission record.

    Hard constraint (BRD §5.3): only filmmakers with a confirmed submission
    may review, one review per submission. Festivals retain a public
    right-of-reply on every review.
    """

    __tablename__ = "reviews"
    __table_args__ = (UniqueConstraint("submission_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    submission_id: Mapped[int] = mapped_column(ForeignKey("submissions.id"))
    festival_id: Mapped[int] = mapped_column(ForeignKey("festivals.id"), index=True)
    filmmaker_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    rating: Mapped[int] = mapped_column(Integer)  # 1-5
    text: Mapped[str] = mapped_column(Text, default="")
    festival_reply: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
