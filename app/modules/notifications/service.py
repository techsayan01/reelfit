"""Notifications service: in-app notifications now; email dispatch (Postmark/
SES via Celery) attaches here without changing callers."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.notifications.models import BulkMessage, Notification, NotificationKind


def send_bulk(
    db: Session,
    *,
    festival_id: int,
    festival_name: str,
    audience: str,
    subject: str,
    body: str,
    recipient_user_ids: list[int],
) -> BulkMessage:
    """Deliver a bulk message to each recipient and log it."""
    for user_id in recipient_user_ids:
        notify(
            db,
            user_id=user_id,
            kind=NotificationKind.BULK_MESSAGE,
            subject=f"[{festival_name}] {subject}",
            body=body,
        )
    message = BulkMessage(
        festival_id=festival_id,
        audience=audience,
        subject=subject,
        body=body,
        recipient_count=len(recipient_user_ids),
    )
    db.add(message)
    db.commit()
    return message


def bulk_messages(db: Session, festival_id: int) -> list[BulkMessage]:
    return list(
        db.scalars(
            select(BulkMessage)
            .where(BulkMessage.festival_id == festival_id)
            .order_by(BulkMessage.created_at.desc())
        )
    )


def notify(
    db: Session, *, user_id: int, kind: NotificationKind, subject: str, body: str = ""
) -> Notification:
    n = Notification(user_id=user_id, kind=kind, subject=subject, body=body)
    db.add(n)
    return n


def for_user(db: Session, user_id: int, limit: int = 20) -> list[Notification]:
    return list(
        db.scalars(
            select(Notification)
            .where(Notification.user_id == user_id)
            .order_by(Notification.created_at.desc())
            .limit(limit)
        )
    )


def unread_count(db: Session, user_id: int) -> int:
    return len(
        list(
            db.scalars(
                select(Notification).where(
                    Notification.user_id == user_id, Notification.read.is_(False)
                )
            )
        )
    )


def mark_all_read(db: Session, user_id: int) -> None:
    for n in db.scalars(
        select(Notification).where(
            Notification.user_id == user_id, Notification.read.is_(False)
        )
    ):
        n.read = True
    db.commit()
