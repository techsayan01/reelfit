import enum
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class UserKind(str, enum.Enum):
    FILMMAKER = "filmmaker"
    ORGANIZER = "organizer"


class OrgRole(str, enum.Enum):
    """Role of a staff member within a festival organization (BRD §5.1.1)."""

    OWNER = "owner"
    PROGRAMMER = "programmer"
    JURY = "jury"
    VIEWER = "viewer"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    display_name: Mapped[str] = mapped_column(String(120))
    kind: Mapped[UserKind] = mapped_column(Enum(UserKind))
    bio: Mapped[str] = mapped_column(Text, default="")
    # Scoring credits (filmmakers). One credit = one film evaluated (BRD §5.2.2).
    credit_balance: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    films: Mapped[list["Film"]] = relationship(back_populates="filmmaker")


class FestivalMembership(Base):
    """Staff account under a festival organization, with role-based access."""

    __tablename__ = "festival_memberships"
    __table_args__ = (UniqueConstraint("user_id", "festival_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    festival_id: Mapped[int] = mapped_column(ForeignKey("festivals.id"), index=True)
    role: Mapped[OrgRole] = mapped_column(Enum(OrgRole), default=OrgRole.VIEWER)


class ProjectKind(str, enum.Enum):
    FILM = "film"
    SCREENPLAY = "screenplay"


class Film(Base):
    """Filmmaker's project library entry: upload once, submit to many (BRD §5.2.1).

    Covers both finished films and screenplays; runtime applies to films only.
    """

    __tablename__ = "films"

    id: Mapped[int] = mapped_column(primary_key=True)
    filmmaker_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    title: Mapped[str] = mapped_column(String(255))
    kind: Mapped[ProjectKind] = mapped_column(Enum(ProjectKind), default=ProjectKind.FILM)
    logline: Mapped[str] = mapped_column(Text, default="")
    genre: Mapped[str] = mapped_column(String(80), index=True)
    runtime_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    year: Mapped[int] = mapped_column(Integer)
    country: Mapped[str] = mapped_column(String(80), default="")
    # Reference into S3-compatible object storage (screener/trailer). Phase 1
    # stores an opaque ref, not the media itself.
    media_ref: Mapped[str] = mapped_column(String(512), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    filmmaker: Mapped[User] = relationship(back_populates="films")
