import enum
import secrets
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class SubmissionStatus(str, enum.Enum):
    """Judging status lifecycle (BRD §5.1.3), extended with the award tiers
    festivals actually use (finalist, award winner, honorable mention)."""

    RECEIVED = "received"
    IN_REVIEW = "in_review"
    SHORTLISTED = "shortlisted"
    FINALIST = "finalist"
    SELECTED = "selected"
    AWARD_WINNER = "award_winner"
    HONORABLE_MENTION = "honorable_mention"
    REJECTED = "rejected"


# Statuses that count as "the film made it in" — certificates and public
# selection stats key off these.
SELECTED_STATUSES = {
    SubmissionStatus.SELECTED,
    SubmissionStatus.AWARD_WINNER,
    SubmissionStatus.HONORABLE_MENTION,
}


def new_relay_id() -> str:
    """Masked-contact relay handle: festivals reach the filmmaker only through
    this revocable alias, never a raw email (BRD §5.2.1)."""
    return f"relay-{secrets.token_urlsafe(12)}"


class Submission(Base):
    __tablename__ = "submissions"

    id: Mapped[int] = mapped_column(primary_key=True)
    film_id: Mapped[int] = mapped_column(ForeignKey("films.id"), index=True)
    festival_id: Mapped[int] = mapped_column(ForeignKey("festivals.id"), index=True)
    edition_id: Mapped[int] = mapped_column(ForeignKey("festival_editions.id"))
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id"))
    status: Mapped[SubmissionStatus] = mapped_column(
        Enum(SubmissionStatus), default=SubmissionStatus.RECEIVED
    )
    fee_paid_cents: Mapped[int] = mapped_column(Integer, default=0)
    discount_code: Mapped[str] = mapped_column(String(60), default="")
    # Festival-facing reference number, e.g. HIL1001 (prefix + sequence).
    tracking_number: Mapped[str] = mapped_column(String(24), default="", index=True)
    relay_contact_id: Mapped[str] = mapped_column(String(60), default=new_relay_id)
    relay_revoked: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
