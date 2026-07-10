from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel

from app.api.deps import DbDep, FilmmakerDep
from app.api.routes_festivals import edition_payload, tier_payload
from app.api.routes_films import own_film
from app.modules.accounts import service as accounts
from app.modules.certificates import service as certificates
from app.modules.festivals import service as festivals
from app.modules.notifications import service as notifications
from app.modules.reviews import service as reviews
from app.modules.submissions import service as submissions
from app.modules.submissions.models import SELECTED_STATUSES
from app.modules.submissions.service import SubmissionError

router = APIRouter(prefix="/api/submissions", tags=["submissions"])


class SubmissionIn(BaseModel):
    film_id: int
    festival_id: int
    category_id: int
    discount_code: str = ""
    cover_letter: str = ""
    answers: dict[int, str] = {}
    source: str = "direct"


def own_submission(db, user, submission_id: int):
    film_ids = [f.id for f in accounts.list_films(db, user.id)]
    for sub in submissions.submissions_for_films(db, film_ids):
        if sub.id == submission_id:
            return sub
    raise HTTPException(404, "Submission not found")


@router.get("")
def my_submissions(db: DbDep, user: FilmmakerDep):
    films = accounts.list_films(db, user.id)
    films_by_id = {f.id: f for f in films}
    subs = submissions.submissions_for_films(db, list(films_by_id))
    reviewed = reviews.reviewed_submission_ids(db, user.id)
    notes = notifications.for_user(db, user.id)
    return {
        "submissions": [
            {
                "id": s.id,
                "tracking_number": s.tracking_number,
                "film_id": s.film_id,
                "film_title": films_by_id[s.film_id].title,
                "festival_id": s.festival_id,
                "festival_name": festivals.get_festival(db, s.festival_id).name,
                "status": s.status.value,
                "fee_paid_cents": s.fee_paid_cents,
                "discount_code": s.discount_code,
                "relay_revoked": s.relay_revoked,
                "reviewed": s.id in reviewed,
                "created_at": s.created_at.isoformat(),
            }
            for s in subs
        ],
        "notifications": [
            {
                "id": n.id,
                "subject": n.subject,
                "body": n.body,
                "read": n.read,
                "created_at": n.created_at.isoformat(),
            }
            for n in notes
        ],
    }


@router.get("/options")
def submission_options(db: DbDep, user: FilmmakerDep, film: int, festival: int):
    """Eligible categories + fees for a film × festival — powers the submit form."""
    film_obj = own_film(db, user, film)
    fest = festivals.get_festival(db, festival)
    if fest is None:
        raise HTTPException(404, "Festival not found")
    edition = festivals.current_edition(db, fest.id)
    waiver_required = False
    if edition is None:
        # Past the final deadline but inside the deadline-waiver window: the
        # form still works, with a waiver code required.
        edition = festivals.waiver_window_edition(db, fest.id)
        waiver_required = edition is not None
    categories = festivals.categories_for_edition(db, edition.id) if edition else []
    tier = festivals.active_deadline_tier(db, edition.id) if edition else None
    if tier is None and waiver_required:
        all_tiers = festivals.all_deadline_tiers(db, edition.id)
        tier = all_tiers[-1] if all_tiers else None
    eligible = [
        c for c in categories
        if festivals.eligible_category(
            c, film_obj.kind.value, film_obj.runtime_minutes, film_obj.year
        )
    ]
    return {
        "festival": {"id": fest.id, "name": fest.name, "slug": fest.slug},
        "film": {"id": film_obj.id, "title": film_obj.title},
        "edition": edition_payload(edition),
        "tier": tier_payload(tier),
        "waiver_required": waiver_required,
        # Custom submission form questions; the client filters by the chosen
        # category (category_id null = applies to all).
        "questions": [
            {
                "id": q.id,
                "field_type": q.field_type.value,
                "question": q.question,
                "options": q.options_list(),
                "category_id": q.category_id,
            }
            for q in festivals.list_questions(db, fest.id)
        ],
        "categories": [
            {
                "id": c.id,
                "name": c.name,
                "fee_cents": festivals.category_fee_cents(c, tier),
            }
            for c in eligible
        ],
    }


@router.post("", status_code=201)
def create_submission(db: DbDep, user: FilmmakerDep, body: SubmissionIn):
    film = own_film(db, user, body.film_id)
    try:
        sub = submissions.create_submission(
            db,
            filmmaker_id=user.id,
            film_id=film.id,
            film_kind=film.kind.value,
            film_runtime=film.runtime_minutes,
            film_year=film.year,
            film_title=film.title,
            festival_id=body.festival_id,
            category_id=body.category_id,
            discount_code=body.discount_code,
            cover_letter=body.cover_letter,
            answers=body.answers,
            source=body.source,
        )
    except SubmissionError as exc:
        raise HTTPException(400, str(exc))
    notifications.fire_event(
        db, body.festival_id, "submission.received",
        {
            "tracking_number": sub.tracking_number,
            "film_title": film.title,
            "category_id": body.category_id,
        },
    )
    return {"submission": {"id": sub.id, "fee_paid_cents": sub.fee_paid_cents}}


@router.post("/{submission_id}/revoke-relay")
def revoke_relay(db: DbDep, user: FilmmakerDep, submission_id: int):
    own_submission(db, user, submission_id)
    submissions.revoke_relay(db, submission_id, user.id)
    return {"ok": True}


@router.get("/{submission_id}/certificate.svg")
def certificate_svg(db: DbDep, user: FilmmakerDep, submission_id: int):
    sub = own_submission(db, user, submission_id)
    if sub.status not in SELECTED_STATUSES:
        raise HTTPException(403, "Certificates are available once a film is selected.")
    fest = festivals.get_festival(db, sub.festival_id)
    edition = next((e for e in fest.editions if e.id == sub.edition_id), None)
    certificates.issue_certificate(db, sub.id)
    svg = certificates.render_laurel_svg(fest.name, edition.label if edition else "")
    return Response(content=svg, media_type="image/svg+xml")
