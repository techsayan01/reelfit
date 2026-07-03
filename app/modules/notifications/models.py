import enum
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class NotificationKind(str, enum.Enum):
    SUBMISSION_RECEIVED = "submission_received"
    STATUS_CHANGE = "status_change"
    DEADLINE_REMINDER = "deadline_reminder"
    BULK_MESSAGE = "bulk_message"


class Notification(Base):
    """In-app notification. Email dispatch mirrors these via the notifications
    service (Postmark/SES relay in production; logged locally in Phase 1 dev)."""

    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    kind: Mapped[NotificationKind] = mapped_column(Enum(NotificationKind))
    subject: Mapped[str] = mapped_column(String(255))
    body: Mapped[str] = mapped_column(Text, default="")
    read: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
