"""Shared API dependencies: session-based current user and role guards.

Auth stays session-cookie based (BRD §7.2) — the React SPA sends
credentials-included fetches; no JWT/API keys are exposed to end users.
"""

from typing import Annotated

from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.db import get_db
from app.modules.accounts import service as accounts
from app.modules.accounts.models import User, UserKind

DbDep = Annotated[Session, Depends(get_db)]


def current_user(request: Request, db: DbDep) -> User | None:
    user_id = request.session.get("user_id")
    if user_id is None:
        return None
    return accounts.get_user(db, user_id)


UserDep = Annotated[User | None, Depends(current_user)]


def require_user(user: UserDep) -> User:
    if user is None:
        raise HTTPException(status_code=401, detail="Sign in to continue.")
    return user


AuthDep = Annotated[User, Depends(require_user)]


def require_filmmaker(user: AuthDep) -> User:
    if user.kind != UserKind.FILMMAKER:
        raise HTTPException(status_code=403, detail="Filmmaker account required.")
    return user


def require_organizer(user: AuthDep) -> User:
    if user.kind != UserKind.ORGANIZER:
        raise HTTPException(status_code=403, detail="Festival account required.")
    return user


FilmmakerDep = Annotated[User, Depends(require_filmmaker)]
OrganizerDep = Annotated[User, Depends(require_organizer)]


def user_payload(user: User | None) -> dict | None:
    if user is None:
        return None
    return {
        "id": user.id,
        "email": user.email,
        "display_name": user.display_name,
        "kind": user.kind.value,
        "credit_balance": user.credit_balance,
    }
