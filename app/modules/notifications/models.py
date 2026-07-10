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


class BulkMessage(Base):
    """A bulk email sent by a festival to submitters or staff (BRD §5.1.4).
    Kept as a log; individual copies land as Notifications (and email in
    production)."""

    __tablename__ = "bulk_messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    festival_id: Mapped[int] = mapped_column(index=True)
    audience: Mapped[str] = mapped_column(String(20))  # "submitters" | "staff"
    subject: Mapped[str] = mapped_column(String(255))
    body: Mapped[str] = mapped_column(Text, default="")
    recipient_count: Mapped[int] = mapped_column(default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class WebhookEndpoint(Base):
    """Festival-configured webhook: Reelfit POSTs event JSON to the URL."""

    __tablename__ = "webhook_endpoints"

    id: Mapped[int] = mapped_column(primary_key=True)
    festival_id: Mapped[int] = mapped_column(index=True)
    url: Mapped[str] = mapped_column(String(512))
    # Comma-separated event names, e.g. "submission.received,submission.status_changed"
    events: Mapped[str] = mapped_column(String(255))
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class WebhookDelivery(Base):
    """Log of webhook delivery attempts."""

    __tablename__ = "webhook_deliveries"

    id: Mapped[int] = mapped_column(primary_key=True)
    endpoint_id: Mapped[int] = mapped_column(index=True)
    event: Mapped[str] = mapped_column(String(60))
    status_code: Mapped[int | None] = mapped_column(nullable=True)
    ok: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


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
