"""Accounts service: registration, authentication, film library.

Password hashing uses stdlib scrypt — no external crypto dependency needed
at founding-cohort scale.
"""

import hashlib
import hmac
import re
import secrets

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.accounts.models import (
    FestivalMembership,
    Film,
    FilmLink,
    FilmLinkKind,
    FilmmakerProfile,
    FilmPhoto,
    FilmPress,
    FilmScreening,
    OrgRole,
    ProjectKind,
    User,
    UserKind,
)

# Editable profile fields — the allow-list for update_profile so a client can
# never write server-managed columns (id, user_id, is_public, timestamps).
PROFILE_FIELDS = {
    "title", "tagline", "location", "hometown", "education",
    "headshot_url", "cover_url", "website_url", "instagram", "facebook",
    "twitter", "linkedin", "imdb_url", "public_email",
}

_SCRYPT_N, _SCRYPT_R, _SCRYPT_P = 2**14, 8, 1


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.scrypt(
        password.encode(), salt=salt.encode(), n=_SCRYPT_N, r=_SCRYPT_R, p=_SCRYPT_P
    )
    return f"scrypt${salt}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        _, salt, hex_digest = stored.split("$")
    except ValueError:
        return False
    digest = hashlib.scrypt(
        password.encode(), salt=salt.encode(), n=_SCRYPT_N, r=_SCRYPT_R, p=_SCRYPT_P
    )
    return hmac.compare_digest(digest.hex(), hex_digest)


def register_user(
    db: Session, email: str, password: str, display_name: str, kind: UserKind
) -> User:
    email = email.strip().lower()
    if db.scalar(select(User).where(User.email == email)):
        raise ValueError("An account with that email already exists.")
    user = User(
        email=email,
        password_hash=hash_password(password),
        display_name=display_name.strip(),
        kind=kind,
        # Founding-cohort welcome credit: one free fit-score check.
        credit_balance=1 if kind == UserKind.FILMMAKER else 0,
    )
    db.add(user)
    db.commit()
    return user


def authenticate(db: Session, email: str, password: str) -> User | None:
    user = db.scalar(select(User).where(User.email == email.strip().lower()))
    if user and verify_password(password, user.password_hash):
        return user
    return None


def get_user(db: Session, user_id: int) -> User | None:
    return db.get(User, user_id)


def festival_staff(db: Session, festival_id: int) -> list[tuple[FestivalMembership, User]]:
    memberships = db.scalars(
        select(FestivalMembership).where(FestivalMembership.festival_id == festival_id)
    )
    return [(m, db.get(User, m.user_id)) for m in memberships]


def add_staff(db: Session, festival_id: int, email: str, role: OrgRole) -> FestivalMembership:
    """Add an existing Reelfit account as festival staff (BRD §5.1.1)."""
    user = db.scalar(select(User).where(User.email == email.strip().lower()))
    if user is None:
        raise ValueError(
            "No Reelfit account with that email — ask them to register first."
        )
    existing = db.scalar(
        select(FestivalMembership).where(
            FestivalMembership.user_id == user.id,
            FestivalMembership.festival_id == festival_id,
        )
    )
    if existing:
        raise ValueError(f"{user.display_name} is already on this festival's staff.")
    membership = FestivalMembership(user_id=user.id, festival_id=festival_id, role=role)
    db.add(membership)
    db.commit()
    return membership


def remove_staff(db: Session, membership_id: int, festival_id: int) -> None:
    membership = db.get(FestivalMembership, membership_id)
    if membership is None or membership.festival_id != festival_id:
        raise ValueError("Staff member not found.")
    if membership.role == OrgRole.OWNER:
        raise ValueError("The festival owner can't be removed.")
    db.delete(membership)
    db.commit()


def list_films(db: Session, filmmaker_id: int) -> list[Film]:
    return list(
        db.scalars(
            select(Film).where(Film.filmmaker_id == filmmaker_id).order_by(Film.created_at.desc())
        )
    )


def create_film(
    db: Session,
    filmmaker_id: int,
    title: str,
    genre: str,
    runtime_minutes: int | None,
    year: int,
    logline: str = "",
    country: str = "",
    kind: ProjectKind = ProjectKind.FILM,
    synopsis: str = "",
    language: str = "",
    credits: str = "",
    screener_url: str = "",
    trailer_url: str = "",
    first_time_filmmaker: bool = False,
    student_project: bool = False,
) -> Film:
    if kind == ProjectKind.FILM and runtime_minutes is None:
        raise ValueError("Films need a runtime.")
    film = Film(
        filmmaker_id=filmmaker_id,
        title=title.strip(),
        kind=kind,
        genre=genre.strip().lower(),
        runtime_minutes=runtime_minutes if kind == ProjectKind.FILM else None,
        year=year,
        logline=logline.strip(),
        country=country.strip(),
        synopsis=synopsis.strip(),
        language=language.strip(),
        credits=credits.strip(),
        screener_url=screener_url.strip(),
        trailer_url=trailer_url.strip(),
        first_time_filmmaker=first_time_filmmaker,
        student_project=student_project,
    )
    db.add(film)
    db.commit()
    return film


def get_film(db: Session, film_id: int) -> Film | None:
    return db.get(Film, film_id)


# ---------------------------------------------------------------------------
# Extended project-page media (photos, links, screenings, press)
# ---------------------------------------------------------------------------

def _delete_child(db: Session, model, child_id: int, film_id: int) -> None:
    """Delete a film child row, verifying it belongs to the given film."""
    row = db.get(model, child_id)
    if row is None or row.film_id != film_id:
        raise ValueError("Item not found.")
    db.delete(row)
    db.commit()


def add_photo(db: Session, film_id: int, url: str, caption: str = "") -> FilmPhoto:
    next_pos = len(db.get(Film, film_id).photos)
    photo = FilmPhoto(
        film_id=film_id, url=url.strip(), caption=caption.strip(), position=next_pos
    )
    db.add(photo)
    db.commit()
    return photo


def delete_photo(db: Session, photo_id: int, film_id: int) -> None:
    _delete_child(db, FilmPhoto, photo_id, film_id)


def add_link(db: Session, film_id: int, kind: FilmLinkKind, url: str) -> FilmLink:
    link = FilmLink(film_id=film_id, kind=kind, url=url.strip())
    db.add(link)
    db.commit()
    return link


def delete_link(db: Session, link_id: int, film_id: int) -> None:
    _delete_child(db, FilmLink, link_id, film_id)


def add_screening(
    db: Session, film_id: int, festival_name: str,
    location: str = "", happened_on: str = "", award: str = "",
) -> FilmScreening:
    screening = FilmScreening(
        film_id=film_id, festival_name=festival_name.strip(),
        location=location.strip(), happened_on=happened_on.strip(), award=award.strip(),
    )
    db.add(screening)
    db.commit()
    return screening


def delete_screening(db: Session, screening_id: int, film_id: int) -> None:
    _delete_child(db, FilmScreening, screening_id, film_id)


def add_press(
    db: Session, film_id: int, title: str, outlet: str = "", url: str = ""
) -> FilmPress:
    press = FilmPress(
        film_id=film_id, title=title.strip(), outlet=outlet.strip(), url=url.strip()
    )
    db.add(press)
    db.commit()
    return press


def delete_press(db: Session, press_id: int, film_id: int) -> None:
    _delete_child(db, FilmPress, press_id, film_id)


# ---------------------------------------------------------------------------
# Filmmaker profiles (public presence)
# ---------------------------------------------------------------------------

_HANDLE_RE = re.compile(r"^[a-z0-9](?:[a-z0-9-]{1,78}[a-z0-9])?$")


def slugify_handle(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:80]


def get_or_create_profile(db: Session, user_id: int) -> FilmmakerProfile:
    """The filmmaker's own profile row, created lazily on first access."""
    profile = db.scalar(
        select(FilmmakerProfile).where(FilmmakerProfile.user_id == user_id)
    )
    if profile is None:
        profile = FilmmakerProfile(user_id=user_id)
        db.add(profile)
        db.commit()
    return profile


def get_profile_by_handle(db: Session, handle: str) -> FilmmakerProfile | None:
    return db.scalar(
        select(FilmmakerProfile).where(FilmmakerProfile.handle == handle.lower())
    )


def set_handle(db: Session, user_id: int, handle: str) -> None:
    """Claim a public handle. Enforces format and global uniqueness."""
    handle = handle.strip().lower()
    if not _HANDLE_RE.match(handle):
        raise ValueError(
            "Handles use letters, numbers and hyphens only (2–80 characters)."
        )
    existing = get_profile_by_handle(db, handle)
    if existing and existing.user_id != user_id:
        raise ValueError("That handle is already taken — try another.")
    profile = get_or_create_profile(db, user_id)
    profile.handle = handle
    db.commit()


def set_public(db: Session, user_id: int, is_public: bool) -> FilmmakerProfile:
    profile = get_or_create_profile(db, user_id)
    if is_public and not profile.handle:
        raise ValueError("Choose a handle before publishing your profile.")
    profile.is_public = is_public
    db.commit()
    return profile


def update_profile(db: Session, user_id: int, changes: dict) -> FilmmakerProfile:
    """Update editable profile fields (allow-listed). Handle and publish state
    have their own guarded setters."""
    profile = get_or_create_profile(db, user_id)
    for key, value in changes.items():
        if key not in PROFILE_FIELDS:
            continue
        if isinstance(value, str):
            value = value.strip()
        setattr(profile, key, value)
    db.commit()
    return profile
