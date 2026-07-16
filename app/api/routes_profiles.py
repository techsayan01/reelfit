"""Public filmmaker profiles (BRD §5.2.1).

A filmmaker's public presence: bio, filmography, verified festival selections,
and contact links. Composes the accounts, submissions and festivals services —
awards are drawn from real submission outcomes, never self-reported.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.api.deps import DbDep, FilmmakerDep
from app.modules.accounts import service as accounts
from app.modules.festivals import service as festivals
from app.modules.submissions import service as submissions
from app.modules.submissions.models import SELECTED_STATUSES, SubmissionStatus

router = APIRouter(tags=["profiles"])

# Statuses worth showing on a public profile as a festival "selection",
# ordered strongest-first for display and sorting.
_ACHIEVEMENT_ORDER = [
    SubmissionStatus.AWARD_WINNER,
    SubmissionStatus.HONORABLE_MENTION,
    SubmissionStatus.SELECTED,
    SubmissionStatus.FINALIST,
    SubmissionStatus.SHORTLISTED,
]
_ACHIEVEMENT_LABELS = {
    SubmissionStatus.AWARD_WINNER: "Award Winner",
    SubmissionStatus.HONORABLE_MENTION: "Honorable Mention",
    SubmissionStatus.SELECTED: "Official Selection",
    SubmissionStatus.FINALIST: "Finalist",
    SubmissionStatus.SHORTLISTED: "Shortlisted",
}


class ProfileIn(BaseModel):
    # display_name and bio live on the User row; the rest on FilmmakerProfile.
    display_name: str = Field(default="", max_length=120)
    bio: str = ""
    title: str = Field(default="", max_length=120)
    tagline: str = Field(default="", max_length=200)
    location: str = Field(default="", max_length=120)
    hometown: str = Field(default="", max_length=120)
    education: str = ""
    headshot_url: str = Field(default="", max_length=512)
    cover_url: str = Field(default="", max_length=512)
    website_url: str = Field(default="", max_length=512)
    instagram: str = Field(default="", max_length=120)
    facebook: str = Field(default="", max_length=120)
    twitter: str = Field(default="", max_length=120)
    linkedin: str = Field(default="", max_length=120)
    imdb_url: str = Field(default="", max_length=512)
    public_email: bool = False


class HandleIn(BaseModel):
    handle: str = Field(min_length=2, max_length=80)


class PublishIn(BaseModel):
    is_public: bool


def _profile_payload(profile) -> dict:
    return {
        "handle": profile.handle,
        "is_public": profile.is_public,
        "title": profile.title,
        "tagline": profile.tagline,
        "location": profile.location,
        "hometown": profile.hometown,
        "education": profile.education,
        "headshot_url": profile.headshot_url,
        "cover_url": profile.cover_url,
        "website_url": profile.website_url,
        "instagram": profile.instagram,
        "facebook": profile.facebook,
        "twitter": profile.twitter,
        "linkedin": profile.linkedin,
        "imdb_url": profile.imdb_url,
        "public_email": profile.public_email,
    }


def _filmography(films) -> list[dict]:
    return [
        {
            "id": f.id,
            "title": f.title,
            "kind": f.kind.value,
            "genre": f.genre,
            "year": f.year,
            "runtime_minutes": f.runtime_minutes,
            "logline": f.logline,
            "links": [{"kind": l.kind.value, "url": l.url} for l in f.links],
        }
        for f in sorted(films, key=lambda f: (f.year or 0), reverse=True)
    ]


def _all_photos(films) -> list[dict]:
    """Every still across the filmmaker's projects, tagged with its film."""
    return [
        {"url": p.url, "caption": p.caption, "film_title": f.title}
        for f in sorted(films, key=lambda f: (f.year or 0), reverse=True)
        for p in f.photos
    ]


def _all_press(films) -> list[dict]:
    """Press across all projects for the profile's News & Reviews section."""
    return [
        {"title": pr.title, "outlet": pr.outlet, "url": pr.url, "film_title": f.title}
        for f in sorted(films, key=lambda f: (f.year or 0), reverse=True)
        for pr in f.press
    ]


def _selections(db, films) -> tuple[list[dict], dict]:
    """Verified festival selections from real submission outcomes.

    Returns the display list (strongest achievements first, most recent within)
    plus a summary count of awards vs. selections."""
    by_film = {f.id: f for f in films}
    rows = []
    awards = 0
    selections = 0
    for sub in submissions.submissions_for_films(db, list(by_film)):
        if sub.status not in _ACHIEVEMENT_LABELS:
            continue
        fest = festivals.get_festival(db, sub.festival_id)
        edition = festivals.get_edition(db, sub.edition_id)
        film = by_film[sub.film_id]
        if sub.status in SELECTED_STATUSES:
            selections += 1
        if sub.status == SubmissionStatus.AWARD_WINNER:
            awards += 1
        rows.append({
            "festival_name": fest.name if fest else "A festival",
            "festival_slug": fest.slug if fest else None,
            "edition_label": edition.label if edition else "",
            "status": sub.status.value,
            "achievement": _ACHIEVEMENT_LABELS[sub.status],
            "film_title": film.title,
            "film_id": film.id,
            "created_at": sub.created_at.isoformat(),
        })
    rows.sort(key=lambda r: (
        _ACHIEVEMENT_ORDER.index(SubmissionStatus(r["status"])),
        r["created_at"],
    ))
    return rows, {"awards": awards, "selections": selections}


@router.get("/api/filmmakers/{handle}")
def public_filmmaker(db: DbDep, handle: str):
    """Public filmmaker profile page data. 404 unless published."""
    profile = accounts.get_profile_by_handle(db, handle)
    if profile is None or not profile.is_public:
        raise HTTPException(404, "No published filmmaker profile at that handle.")
    user = accounts.get_user(db, profile.user_id)
    films = accounts.list_films(db, profile.user_id)
    selections, summary = _selections(db, films)
    payload = _profile_payload(profile)
    payload.update({
        "display_name": user.display_name,
        "bio": user.bio,
        "email": user.email if profile.public_email else None,
        "filmography": _filmography(films),
        "selections": selections,
        "summary": summary,
        "photos": _all_photos(films),
        "press": _all_press(films),
    })
    return payload


@router.get("/api/me/profile")
def my_profile(db: DbDep, user: FilmmakerDep):
    """The signed-in filmmaker's own editable profile."""
    profile = accounts.get_or_create_profile(db, user.id)
    payload = _profile_payload(profile)
    payload.update({"display_name": user.display_name, "bio": user.bio})
    return payload


@router.patch("/api/me/profile")
def update_my_profile(db: DbDep, user: FilmmakerDep, body: ProfileIn):
    changes = body.model_dump()
    # display_name / bio are User columns; the rest are allow-listed profile fields.
    display_name = changes.pop("display_name", "").strip()
    if display_name:
        user.display_name = display_name
    user.bio = changes.pop("bio", user.bio).strip()
    db.commit()
    profile = accounts.update_profile(db, user.id, changes)
    payload = _profile_payload(profile)
    payload.update({"display_name": user.display_name, "bio": user.bio})
    return payload


@router.put("/api/me/profile/handle")
def claim_handle(db: DbDep, user: FilmmakerDep, body: HandleIn):
    try:
        accounts.set_handle(db, user.id, body.handle)
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    return _profile_payload(accounts.get_or_create_profile(db, user.id))


@router.put("/api/me/profile/publish")
def set_publish(db: DbDep, user: FilmmakerDep, body: PublishIn):
    try:
        profile = accounts.set_public(db, user.id, body.is_public)
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    return _profile_payload(profile)
