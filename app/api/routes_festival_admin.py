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
from app.modules.jury import service as jury
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


class NoteIn(BaseModel):
    text: str


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


def _own_submission(db, membership, submission_id: int):
    sub = submissions.get_submission(db, submission_id)
    if sub is None or sub.festival_id != membership.festival_id:
        raise HTTPException(404, "Submission not found")
    return sub


@router.get("/submissions/{submission_id}")
def submission_detail(db: DbDep, user: OrganizerDep, submission_id: int):
    """Everything a programmer needs to judge one entry. The filmmaker's
    public profile is shown; direct contact stays behind the masked relay."""
    membership = _membership(db, user)
    sub = _own_submission(db, membership, submission_id)
    film = accounts.get_film(db, sub.film_id)
    filmmaker = accounts.get_user(db, film.filmmaker_id)
    festival = festivals.get_festival(db, membership.festival_id)
    categories = {
        c.id: c.name
        for e in festival.editions
        for c in festivals.categories_for_edition(db, e.id)
    }

    # Prev/next within this festival's submissions, newest first.
    subs = submissions.submissions_for_festival(db, membership.festival_id)
    ids = [s.id for s in subs]
    idx = ids.index(sub.id)
    prev_id = ids[idx - 1] if idx > 0 else None
    next_id = ids[idx + 1] if idx < len(ids) - 1 else None

    def actor_name(user_id):
        if user_id is None:
            return "system"
        actor = accounts.get_user(db, user_id)
        return actor.display_name if actor else "unknown"

    return {
        "submission": {
            "id": sub.id,
            "tracking_number": sub.tracking_number,
            "status": sub.status.value,
            "notified": sub.status != SubmissionStatus.RECEIVED,
            "category": categories.get(sub.category_id, ""),
            "fee_paid_cents": sub.fee_paid_cents,
            "discount_code": sub.discount_code,
            "cover_letter": sub.cover_letter,
            "contact": "access revoked" if sub.relay_revoked else sub.relay_contact_id,
            "created_at": sub.created_at.isoformat(),
        },
        "film": {
            "title": film.title,
            "kind": film.kind.value,
            "genre": film.genre,
            "runtime_minutes": film.runtime_minutes,
            "year": film.year,
            "country": film.country,
            "language": film.language,
            "logline": film.logline,
            "synopsis": film.synopsis,
            "credits": film.credits,
            "screener_url": film.screener_url,
            "trailer_url": film.trailer_url,
            "first_time_filmmaker": film.first_time_filmmaker,
            "student_project": film.student_project,
        },
        "filmmaker": {
            "display_name": filmmaker.display_name,
            "bio": filmmaker.bio,
        },
        "status_log": [
            {
                "actor": actor_name(c.actor_user_id),
                "from_status": c.from_status,
                "to_status": c.to_status,
                "created_at": c.created_at.isoformat(),
            }
            for c in submissions.status_log(db, sub.id)
        ],
        "notes": [
            {
                "id": n.id,
                "author": actor_name(n.author_user_id),
                "text": n.text,
                "created_at": n.created_at.isoformat(),
            }
            for n in jury.notes_for_submission(db, sub.id)
        ],
        "statuses": [s.value for s in SubmissionStatus],
        "can_update": membership.role in STATUS_ROLES,
        "prev_id": prev_id,
        "next_id": next_id,
    }


@router.post("/submissions/{submission_id}/notes", status_code=201)
def add_note(db: DbDep, user: OrganizerDep, submission_id: int, body: NoteIn):
    """Internal jury note — never visible to the filmmaker (BRD §5.1.3)."""
    membership = _membership(db, user)
    _own_submission(db, membership, submission_id)
    if not body.text.strip():
        raise HTTPException(400, "Note can't be empty.")
    note = jury.add_internal_note(db, submission_id, user.id, body.text.strip())
    return {"note": {"id": note.id}}


@router.post("/submissions/{submission_id}/status")
def update_status(db: DbDep, user: OrganizerDep, submission_id: int, body: StatusIn):
    membership = _membership(db, user)
    if membership.role not in STATUS_ROLES:
        raise HTTPException(403, "Your role can't change judging status.")
    sub = _own_submission(db, membership, submission_id)
    submissions.update_status(db, submission_id, body.status, actor_user_id=user.id)

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
