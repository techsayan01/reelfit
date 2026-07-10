"""Notifications service: in-app notifications now; email dispatch (Postmark/
SES via Celery) attaches here without changing callers. Also owns outbound
webhooks."""

import json
import threading
import urllib.request

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.notifications.models import WebhookDelivery, WebhookEndpoint

WEBHOOK_EVENTS = ("submission.received", "submission.status_changed")


def add_webhook(db: Session, festival_id: int, url: str, events: list[str]) -> WebhookEndpoint:
    url = url.strip()
    if not url.startswith(("http://", "https://")):
        raise ValueError("Webhook URLs start with http:// or https://")
    chosen = [e for e in events if e in WEBHOOK_EVENTS]
    if not chosen:
        raise ValueError("Pick at least one event.")
    endpoint = WebhookEndpoint(festival_id=festival_id, url=url, events=",".join(chosen))
    db.add(endpoint)
    db.commit()
    return endpoint


def list_webhooks(db: Session, festival_id: int) -> list[WebhookEndpoint]:
    return list(
        db.scalars(
            select(WebhookEndpoint).where(WebhookEndpoint.festival_id == festival_id)
        )
    )


def delete_webhook(db: Session, endpoint_id: int, festival_id: int) -> None:
    endpoint = db.get(WebhookEndpoint, endpoint_id)
    if endpoint is None or endpoint.festival_id != festival_id:
        raise ValueError("Webhook not found.")
    for d in db.scalars(
        select(WebhookDelivery).where(WebhookDelivery.endpoint_id == endpoint_id)
    ):
        db.delete(d)
    db.delete(endpoint)
    db.commit()


def recent_deliveries(db: Session, endpoint_id: int, limit: int = 5) -> list[WebhookDelivery]:
    return list(
        db.scalars(
            select(WebhookDelivery)
            .where(WebhookDelivery.endpoint_id == endpoint_id)
            .order_by(WebhookDelivery.created_at.desc())
            .limit(limit)
        )
    )


def _deliver(endpoint_id: int, url: str, event: str, payload: dict) -> None:
    """Best-effort webhook POST in a background thread; production moves this
    to Celery with retries without changing callers."""
    status = None
    try:
        req = urllib.request.Request(
            url,
            data=json.dumps({"event": event, "data": payload}).encode(),
            headers={"Content-Type": "application/json", "User-Agent": "Reelfit-Webhook/1.0"},
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            status = resp.status
    except Exception:
        pass
    from app.db import SessionLocal

    session = SessionLocal()
    try:
        session.add(WebhookDelivery(
            endpoint_id=endpoint_id, event=event,
            status_code=status, ok=status is not None and 200 <= status < 300,
        ))
        session.commit()
    finally:
        session.close()


def fire_event(db: Session, festival_id: int, event: str, payload: dict) -> None:
    for endpoint in list_webhooks(db, festival_id):
        if endpoint.active and event in endpoint.events.split(","):
            threading.Thread(
                target=_deliver,
                args=(endpoint.id, endpoint.url, event, payload),
                daemon=True,
            ).start()

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
