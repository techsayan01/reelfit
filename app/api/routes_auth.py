import re

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select

from app.api.deps import DbDep, UserDep, user_payload
from app.modules.accounts import service as accounts
from app.modules.accounts.models import FestivalMembership, OrgRole, UserKind
from app.modules.festivals.models import Festival

router = APIRouter(prefix="/api/auth", tags=["auth"])


class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    display_name: str = Field(min_length=1, max_length=120)
    kind: UserKind
    festival_name: str = ""


class LoginIn(BaseModel):
    email: str
    password: str


def _slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


@router.post("/register")
def register(request: Request, db: DbDep, body: RegisterIn):
    try:
        user = accounts.register_user(
            db, body.email, body.password, body.display_name, body.kind
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc))

    # Organizers can set up their festival organization right away (BRD §5.1.1).
    if body.kind == UserKind.ORGANIZER and body.festival_name.strip():
        slug = _slugify(body.festival_name)
        if not db.scalar(select(Festival).where(Festival.slug == slug)):
            festival = Festival(name=body.festival_name.strip(), slug=slug)
            db.add(festival)
            db.flush()
            db.add(FestivalMembership(
                user_id=user.id, festival_id=festival.id, role=OrgRole.OWNER
            ))
            db.commit()

    request.session["user_id"] = user.id
    return {"user": user_payload(user)}


@router.post("/login")
def login(request: Request, db: DbDep, body: LoginIn):
    user = accounts.authenticate(db, body.email, body.password)
    if user is None:
        raise HTTPException(401, "That email and password don't match an account.")
    request.session["user_id"] = user.id
    return {"user": user_payload(user)}


@router.post("/logout")
def logout(request: Request):
    request.session.clear()
    return {"ok": True}


@router.get("/me")
def me(user: UserDep):
    return {"user": user_payload(user)}
