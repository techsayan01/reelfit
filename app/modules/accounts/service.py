"""Accounts service: registration, authentication, film library.

Password hashing uses stdlib scrypt — no external crypto dependency needed
at founding-cohort scale.
"""

import hashlib
import hmac
import secrets

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.accounts.models import Film, User, UserKind

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
    runtime_minutes: int,
    year: int,
    logline: str = "",
    country: str = "",
) -> Film:
    film = Film(
        filmmaker_id=filmmaker_id,
        title=title.strip(),
        genre=genre.strip().lower(),
        runtime_minutes=runtime_minutes,
        year=year,
        logline=logline.strip(),
        country=country.strip(),
    )
    db.add(film)
    db.commit()
    return film


def get_film(db: Session, film_id: int) -> Film | None:
    return db.get(Film, film_id)
