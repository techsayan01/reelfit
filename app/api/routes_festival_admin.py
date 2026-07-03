from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import select

from app.api.deps import DbDep, OrganizerDep
from app.api.routes_festivals import festival_payload
from app.modules.accounts import service as accounts
from app.modules.accounts.models import FestivalMembership, OrgRole
from app.modules.certificates import service as certificates
from app.modules.dashboards import service as dashboards
from app.modules.festivals import service as festivals
from app.modules.notifications import service as notifications
from app.modules.notifications.models import NotificationKind
from app.modules.reviews import service as reviews
from app.modules.submissions import service as submissions
from app.modules.submissions.models import SELECTED_STATUSES, SubmissionStatus

router = APIRouter(prefix="/api/festival", tags=["festival-admin"])

# Roles allowed to change judging status (viewer is read-only; BRD §5.1.1).
STATUS_ROLES = {OrgRole.OWNER, OrgRole.PROGRAMMER}


class StatusIn(BaseModel):
    status: SubmissionStatus


class ReplyIn(BaseModel):
    reply_text: str


class ProfileIn(BaseModel):
    """Editable public-profile fields (BRD §5.1.7). All optional — only sent
    fields change."""

    description: str | None = None
    country: str | None = None
    region: str | None = None
    logo_url: str | None = None
    cover_url: str | None = None
    rules: str | None = None
    awards_and_prizes: str | None = None
    contact_email: str | None = None
    phone: str | None = None
    tracking_prefix: str | None = None
    website: str | None = None
    twitter: str | None = None
    instagram: str | None = None
    venue_name: str | None = None
    venue_address: str | None = None
    founded_year: int | None = None
    is_public: bool | None = None


def _membership(db, user) -> FestivalMembership:
    membership = db.scalar(
        select(FestivalMembership).where(FestivalMembership.user_id == user.id)
    )
    if membership is None:
        raise HTTPException(403, "Your account isn't linked to a festival yet.")
    return membership


@router.get("/dashboard")
def festival_dashboard(db: DbDep, user: OrganizerDep):
    membership = _membership(db, user)
    festival = festivals.get_festival(db, membership.festival_id)
    overview = dashboards.festival_overview(db, festival.id)
    subs = submissions.submissions_for_festival(db, festival.id)
    festival_reviews = reviews.reviews_for_festival(db, festival.id)

    categories = {
        c.id: c.name
        for e in festivals.get_festival(db, membership.festival_id).editions
        for c in festivals.categories_for_edition(db, e.id)
    }
    sub_rows = []
    for s in subs:
        film = accounts.get_film(db, s.film_id)
        sub_rows.append({
            "id": s.id,
            "tracking_number": s.tracking_number,
            "film_title": film.title,
            "film_kind": film.kind.value,
            "film_genre": film.genre,
            "film_runtime_minutes": film.runtime_minutes,
            "film_country": film.country,
            "category": categories.get(s.category_id, ""),
            # Masked contact: festivals see the relay handle, never an email
            # (BRD §5.2.1), unless the filmmaker revoked access entirely.
            "contact": "access revoked" if s.relay_revoked else s.relay_contact_id,
            "fee_paid_cents": s.fee_paid_cents,
            "status": s.status.value,
            # Status changes always notify the filmmaker automatically.
            "notified": s.status != SubmissionStatus.RECEIVED,
            "created_at": s.created_at.isoformat(),
        })

    return {
        "festival": {**festival_payload(festival), "rules": festival.rules},
        "role": membership.role.value,
        "can_edit_profile": membership.role == OrgRole.OWNER,
        "can_update": membership.role in STATUS_ROLES,
        "overview": {
            "total_submissions": overview.total_submissions,
            "by_status": overview.by_status,
            "gross_revenue_cents": overview.gross_revenue_cents,
            "discounted_count": overview.discounted_count,
        },
        "submissions": sub_rows,
        "reviews": [
            {
                "id": r.id,
                "rating": r.rating,
                "text": r.text,
                "festival_reply": r.festival_reply,
                "created_at": r.created_at.isoformat(),
            }
            for r in festival_reviews
        ],
        "statuses": [s.value for s in SubmissionStatus],
    }


@router.patch("/profile")
def update_profile(db: DbDep, user: OrganizerDep, body: ProfileIn):
    membership = _membership(db, user)
    if membership.role != OrgRole.OWNER:
        raise HTTPException(403, "Only the festival owner can edit the public profile.")
    festival = festivals.update_profile(
        db, membership.festival_id, body.model_dump(exclude_unset=True)
    )
    return {"festival": {**festival_payload(festival), "rules": festival.rules}}


@router.post("/submissions/{submission_id}/status")
def update_status(db: DbDep, user: OrganizerDep, submission_id: int, body: StatusIn):
    membership = _membership(db, user)
    if membership.role not in STATUS_ROLES:
        raise HTTPException(403, "Your role can't change judging status.")
    sub = next(
        (s for s in submissions.submissions_for_festival(db, membership.festival_id)
         if s.id == submission_id),
        None,
    )
    if sub is None:
        raise HTTPException(404, "Submission not found")
    submissions.update_status(db, submission_id, body.status)

    film = accounts.get_film(db, sub.film_id)
    festival = festivals.get_festival(db, membership.festival_id)
    friendly = {
        SubmissionStatus.IN_REVIEW: "is now in review",
        SubmissionStatus.SHORTLISTED: "has been shortlisted",
        SubmissionStatus.FINALIST: "is a FINALIST",
        SubmissionStatus.SELECTED: "has been SELECTED 🎉",
        SubmissionStatus.AWARD_WINNER: "is an AWARD WINNER 🏆",
        SubmissionStatus.HONORABLE_MENTION: "received an honorable mention",
        SubmissionStatus.REJECTED: "was not selected this time",
        SubmissionStatus.RECEIVED: "was received",
    }[body.status]
    notifications.notify(
        db,
        user_id=film.filmmaker_id,
        kind=NotificationKind.STATUS_CHANGE,
        subject=f"“{film.title}” {friendly} at {festival.name}",
    )
    if body.status in SELECTED_STATUSES:
        certificates.issue_certificate(db, sub.id)
    db.commit()
    return {"ok": True}


@router.post("/reviews/{review_id}/reply")
def reply_to_review(db: DbDep, user: OrganizerDep, review_id: int, body: ReplyIn):
    membership = _membership(db, user)
    review = next(
        (r for r in reviews.reviews_for_festival(db, membership.festival_id)
         if r.id == review_id),
        None,
    )
    if review is None:
        raise HTTPException(404, "Review not found")
    reviews.reply(db, review_id, body.reply_text)
    return {"ok": True}
