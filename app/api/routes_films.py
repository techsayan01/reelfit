from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.api.deps import DbDep, FilmmakerDep
from app.api.routes_festivals import festival_payload
from app.modules.accounts import service as accounts
from app.modules.accounts.models import ProjectKind
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


@router.get("")
def list_films(db: DbDep, user: FilmmakerDep):
    return {"films": [film_payload(f) for f in accounts.list_films(db, user.id)]}


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


@router.get("/{film_id}/scores")
def film_scores(db: DbDep, user: FilmmakerDep, film_id: int):
    film = own_film(db, user, film_id)
    latest = scoring.latest_scores_for_film(db, film.id)
    from app.modules.festivals import service as festivals

    rows = []
    for s in latest:
        fest = festivals.get_festival(db, s.festival_id)
        rows.append({
            "festival": festival_payload(fest),
            "score": s.score,
            "confidence": s.confidence,
            "calibration_status": s.calibration_status,
            "created_at": s.created_at.isoformat(),
        })
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
