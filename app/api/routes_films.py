from datetime import date

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.api.deps import DbDep, FilmmakerDep
from app.api.routes_festivals import festival_payload
from app.modules.accounts import service as accounts
from app.modules.accounts.models import FilmLinkKind, ProjectKind
from app.modules.payments import service as payments
from app.modules.recommendations import service as recommendations
from app.modules.scoring import service as scoring
from app.modules.scoring.engine import FilmProfile
from app.modules.submissions import service as submissions
from app.modules.submissions.models import SELECTED_STATUSES

router = APIRouter(prefix="/api/films", tags=["films"])


class FilmIn(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    kind: ProjectKind = ProjectKind.FILM
    genre: str = Field(min_length=1, max_length=80)
    runtime_minutes: int | None = Field(default=None, ge=1, le=600)
    year: int = Field(ge=1990, le=2030)
    logline: str = ""
    country: str = ""
    synopsis: str = ""
    language: str = ""
    credits: str = ""
    screener_url: str = ""
    trailer_url: str = ""
    first_time_filmmaker: bool = False
    student_project: bool = False


def film_payload(f) -> dict:
    return {
        "id": f.id,
        "title": f.title,
        "kind": f.kind.value,
        "genre": f.genre,
        "runtime_minutes": f.runtime_minutes,
        "year": f.year,
        "country": f.country,
        "logline": f.logline,
        "synopsis": f.synopsis,
        "language": f.language,
        "credits": f.credits,
        "screener_url": f.screener_url,
        "trailer_url": f.trailer_url,
        "first_time_filmmaker": f.first_time_filmmaker,
        "student_project": f.student_project,
    }


def own_film(db, user, film_id: int):
    film = accounts.get_film(db, film_id)
    if film is None or film.filmmaker_id != user.id:
        raise HTTPException(404, "Film not found")
    return film


def film_media_payload(film) -> dict:
    """Extended project-page media: still photos, links, screenings, press."""
    return {
        "photos": [
            {"id": p.id, "url": p.url, "caption": p.caption}
            for p in film.photos
        ],
        "links": [
            {"id": l.id, "kind": l.kind.value, "url": l.url}
            for l in film.links
        ],
        "screenings": [
            {
                "id": s.id, "festival_name": s.festival_name, "location": s.location,
                "happened_on": s.happened_on, "award": s.award,
            }
            for s in film.screenings
        ],
        "press": [
            {"id": pr.id, "title": pr.title, "outlet": pr.outlet, "url": pr.url}
            for pr in film.press
        ],
    }


class PhotoIn(BaseModel):
    url: str = Field(min_length=1, max_length=512)
    caption: str = Field(default="", max_length=200)


class LinkIn(BaseModel):
    kind: FilmLinkKind = FilmLinkKind.OTHER
    url: str = Field(min_length=1, max_length=512)


class ScreeningIn(BaseModel):
    festival_name: str = Field(min_length=1, max_length=200)
    location: str = Field(default="", max_length=120)
    happened_on: str = Field(default="", max_length=40)
    award: str = Field(default="", max_length=120)


class PressIn(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    outlet: str = Field(default="", max_length=120)
    url: str = Field(default="", max_length=512)


@router.get("")
def list_films(db: DbDep, user: FilmmakerDep):
    return {"films": [film_payload(f) for f in accounts.list_films(db, user.id)]}


@router.get("/{film_id}")
def get_film_detail(db: DbDep, user: FilmmakerDep, film_id: int):
    """A single film with its extended project-page media — powers the editor."""
    film = own_film(db, user, film_id)
    return {"film": film_payload(film), **film_media_payload(film)}


@router.post("/{film_id}/photos", status_code=201)
def add_photo(db: DbDep, user: FilmmakerDep, film_id: int, body: PhotoIn):
    own_film(db, user, film_id)
    accounts.add_photo(db, film_id, body.url, body.caption)
    return film_media_payload(own_film(db, user, film_id))


@router.delete("/{film_id}/photos/{photo_id}")
def remove_photo(db: DbDep, user: FilmmakerDep, film_id: int, photo_id: int):
    own_film(db, user, film_id)
    try:
        accounts.delete_photo(db, photo_id, film_id)
    except ValueError as exc:
        raise HTTPException(404, str(exc))
    return film_media_payload(own_film(db, user, film_id))


@router.post("/{film_id}/links", status_code=201)
def add_link(db: DbDep, user: FilmmakerDep, film_id: int, body: LinkIn):
    own_film(db, user, film_id)
    accounts.add_link(db, film_id, body.kind, body.url)
    return film_media_payload(own_film(db, user, film_id))


@router.delete("/{film_id}/links/{link_id}")
def remove_link(db: DbDep, user: FilmmakerDep, film_id: int, link_id: int):
    own_film(db, user, film_id)
    try:
        accounts.delete_link(db, link_id, film_id)
    except ValueError as exc:
        raise HTTPException(404, str(exc))
    return film_media_payload(own_film(db, user, film_id))


@router.post("/{film_id}/screenings", status_code=201)
def add_screening(db: DbDep, user: FilmmakerDep, film_id: int, body: ScreeningIn):
    own_film(db, user, film_id)
    accounts.add_screening(
        db, film_id, body.festival_name, body.location, body.happened_on, body.award
    )
    return film_media_payload(own_film(db, user, film_id))


@router.delete("/{film_id}/screenings/{screening_id}")
def remove_screening(db: DbDep, user: FilmmakerDep, film_id: int, screening_id: int):
    own_film(db, user, film_id)
    try:
        accounts.delete_screening(db, screening_id, film_id)
    except ValueError as exc:
        raise HTTPException(404, str(exc))
    return film_media_payload(own_film(db, user, film_id))


@router.post("/{film_id}/press", status_code=201)
def add_press(db: DbDep, user: FilmmakerDep, film_id: int, body: PressIn):
    own_film(db, user, film_id)
    accounts.add_press(db, film_id, body.title, body.outlet, body.url)
    return film_media_payload(own_film(db, user, film_id))


@router.delete("/{film_id}/press/{press_id}")
def remove_press(db: DbDep, user: FilmmakerDep, film_id: int, press_id: int):
    own_film(db, user, film_id)
    try:
        accounts.delete_press(db, press_id, film_id)
    except ValueError as exc:
        raise HTTPException(404, str(exc))
    return film_media_payload(own_film(db, user, film_id))


@router.post("", status_code=201)
def create_film(db: DbDep, user: FilmmakerDep, body: FilmIn):
    try:
        film = accounts.create_film(
            db, user.id, body.title, body.genre, body.runtime_minutes, body.year,
            logline=body.logline, country=body.country, kind=body.kind,
            synopsis=body.synopsis, language=body.language, credits=body.credits,
            screener_url=body.screener_url, trailer_url=body.trailer_url,
            first_time_filmmaker=body.first_time_filmmaker,
            student_project=body.student_project,
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    return {"film": film_payload(film)}


@router.post("/{film_id}/score")
def score_film(db: DbDep, user: FilmmakerDep, film_id: int):
    film = own_film(db, user, film_id)
    try:
        payments.spend_credit(db, user.id, f"fit score: {film.title}")
    except payments.InsufficientCredits:
        raise HTTPException(
            402, "You're out of scoring credits — one credit scores a film "
                 "against every listed festival."
        )
    profile = FilmProfile(
        genre=film.genre, runtime_minutes=film.runtime_minutes,
        year=film.year, country=film.country,
    )
    scoring.score_film_everywhere(db, film.id, profile)
    return {"ok": True, "credit_balance": user.credit_balance}


def _submission_context(db, festivals, film, festival_id: int) -> dict:
    """Whether this film can be submitted to a festival right now, plus the
    cheapest eligible fee and days until the active deadline — the practical
    facts a fit score alone can't tell you (BRD §7.4)."""
    edition = festivals.current_edition(db, festival_id)
    tier = festivals.active_deadline_tier(db, edition.id) if edition else None
    eligible = []
    if edition:
        eligible = [
            c for c in festivals.categories_for_edition(db, edition.id)
            if festivals.eligible_category(
                c, film.kind.value, film.runtime_minutes, film.year
            )
        ]
    is_open = edition is not None
    fee_cents = (
        min(festivals.category_fee_cents(c, tier) for c in eligible)
        if eligible else None
    )
    deadline = tier.deadline if tier else (edition.closes_on if edition else None)
    days_to_deadline = (deadline - date.today()).days if deadline else None
    return {
        "open": is_open,
        "eligible": bool(eligible),
        "fee_cents": fee_cents,
        "deadline": deadline.isoformat() if deadline else None,
        "days_to_deadline": days_to_deadline,
    }


@router.get("/{film_id}/scores")
def film_scores(db: DbDep, user: FilmmakerDep, film_id: int):
    film = own_film(db, user, film_id)
    latest = scoring.latest_scores_for_film(db, film.id)
    from app.modules.festivals import service as festivals

    contexts = {}
    rows_by_festival = {}
    for s in latest:
        fest = festivals.get_festival(db, s.festival_id)
        ctx = _submission_context(db, festivals, film, s.festival_id)
        contexts[s.festival_id] = ctx
        rows_by_festival[s.festival_id] = {
            "festival": festival_payload(fest),
            "score": s.score,
            "confidence": s.confidence,
            "calibration_status": s.calibration_status,
            "created_at": s.created_at.isoformat(),
            **ctx,
        }

    ranked = recommendations.rank_festivals([
        {"festival_id": fid, "score": row["score"], **contexts[fid]}
        for fid, row in rows_by_festival.items()
    ])
    # Present festivals in ranked order, each carrying its recommendation.
    rows = []
    for match in ranked:
        row = rows_by_festival[match.festival_id]
        row["recommendation"] = {
            "reason": match.reason,
            "tier": match.tier,
            "closing_soon": match.closing_soon,
            "submittable": match.submittable,
        }
        rows.append(row)

    selected_count = sum(
        1
        for sub in submissions.submissions_for_films(db, [film.id])
        if sub.status in SELECTED_STATUSES
    )
    guidance = recommendations.distribution_guidance(
        film.genre, film.runtime_minutes, selected_count
    )
    return {
        "film": film_payload(film),
        "scores": rows,
        "guidance": [
            {"path": g.path, "title": g.title, "rationale": g.rationale}
            for g in guidance
        ],
    }
