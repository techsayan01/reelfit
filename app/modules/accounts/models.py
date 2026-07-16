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


class FilmmakerProfile(Base):
    """Public-facing filmmaker profile (BRD §5.2.1 filmmaker presence).

    One-to-one with a filmmaker User, kept in its own table so the auth-critical
    User row stays lean. The profile is private until the filmmaker publishes it
    with a chosen handle. Awards shown on the public page are drawn from real
    submission outcomes, never self-reported — Reelfit's honest-by-default stance
    (unlike incumbents' free-text award lists).
    """

    __tablename__ = "filmmaker_profiles"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"), unique=True, index=True
    )
    # Public URL handle, e.g. /f/priya-sharma. None until the profile is published.
    handle: Mapped[str | None] = mapped_column(
        String(80), unique=True, index=True, nullable=True
    )
    is_public: Mapped[bool] = mapped_column(default=False)
    # Role line under the name, e.g. "Writer/Director".
    title: Mapped[str] = mapped_column(String(120), default="")
    tagline: Mapped[str] = mapped_column(String(200), default="")
    location: Mapped[str] = mapped_column(String(120), default="")
    hometown: Mapped[str] = mapped_column(String(120), default="")
    education: Mapped[str] = mapped_column(Text, default="")
    # Image URLs (object storage comes later in Phase 1; opaque URLs for now).
    headshot_url: Mapped[str] = mapped_column(String(512), default="")
    cover_url: Mapped[str] = mapped_column(String(512), default="")
    # Contact / social links.
    website_url: Mapped[str] = mapped_column(String(512), default="")
    instagram: Mapped[str] = mapped_column(String(120), default="")
    facebook: Mapped[str] = mapped_column(String(120), default="")
    twitter: Mapped[str] = mapped_column(String(120), default="")
    linkedin: Mapped[str] = mapped_column(String(120), default="")
    imdb_url: Mapped[str] = mapped_column(String(512), default="")
    # Show the account email publicly (off by default — contact stays masked).
    public_email: Mapped[bool] = mapped_column(default=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    user: Mapped[User] = relationship()


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
    synopsis: Mapped[str] = mapped_column(Text, default="")
    genre: Mapped[str] = mapped_column(String(80), index=True)
    runtime_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    year: Mapped[int] = mapped_column(Integer)
    country: Mapped[str] = mapped_column(String(80), default="")
    language: Mapped[str] = mapped_column(String(80), default="")
    # Freeform credits, one "Name — Role" per line.
    credits: Mapped[str] = mapped_column(Text, default="")
    # Screener/trailer links (YouTube/Vimeo). Uploaded media comes later via
    # object storage (BRD §7.2).
    screener_url: Mapped[str] = mapped_column(String(512), default="")
    trailer_url: Mapped[str] = mapped_column(String(512), default="")
    first_time_filmmaker: Mapped[bool] = mapped_column(default=False)
    student_project: Mapped[bool] = mapped_column(default=False)
    # Reference into S3-compatible object storage (screener/trailer). Phase 1
    # stores an opaque ref, not the media itself.
    media_ref: Mapped[str] = mapped_column(String(512), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    filmmaker: Mapped[User] = relationship(back_populates="films")
    # Extended project page media (FilmFreeway-style). Child tables so they can
    # be added without altering the films table (Phase 1 has no migrations yet).
    photos: Mapped[list["FilmPhoto"]] = relationship(
        back_populates="film", cascade="all, delete-orphan", order_by="FilmPhoto.position"
    )
    links: Mapped[list["FilmLink"]] = relationship(
        back_populates="film", cascade="all, delete-orphan", order_by="FilmLink.id"
    )
    screenings: Mapped[list["FilmScreening"]] = relationship(
        back_populates="film", cascade="all, delete-orphan", order_by="FilmScreening.id"
    )
    press: Mapped[list["FilmPress"]] = relationship(
        back_populates="film", cascade="all, delete-orphan", order_by="FilmPress.id"
    )


class FilmPhoto(Base):
    """A still photo for a film's project page (BRD §5.2.1)."""

    __tablename__ = "film_photos"

    id: Mapped[int] = mapped_column(primary_key=True)
    film_id: Mapped[int] = mapped_column(ForeignKey("films.id"), index=True)
    url: Mapped[str] = mapped_column(String(512))
    caption: Mapped[str] = mapped_column(String(200), default="")
    position: Mapped[int] = mapped_column(Integer, default=0)

    film: Mapped[Film] = relationship(back_populates="photos")


class FilmLinkKind(str, enum.Enum):
    WEBSITE = "website"
    INSTAGRAM = "instagram"
    BLUESKY = "bluesky"
    OTHER = "other"


class FilmLink(Base):
    """An external link tied to a project (website, Instagram, Bluesky…)."""

    __tablename__ = "film_links"

    id: Mapped[int] = mapped_column(primary_key=True)
    film_id: Mapped[int] = mapped_column(ForeignKey("films.id"), index=True)
    kind: Mapped[FilmLinkKind] = mapped_column(Enum(FilmLinkKind), default=FilmLinkKind.OTHER)
    url: Mapped[str] = mapped_column(String(512))

    film: Mapped[Film] = relationship(back_populates="links")


class FilmScreening(Base):
    """A festival screening / award not captured by a Reelfit submission —
    a public festival run, external award, or past screening the filmmaker adds
    themselves. Reelfit-verified selections are computed separately and never
    stored here, so the two never blur together."""

    __tablename__ = "film_screenings"

    id: Mapped[int] = mapped_column(primary_key=True)
    film_id: Mapped[int] = mapped_column(ForeignKey("films.id"), index=True)
    festival_name: Mapped[str] = mapped_column(String(200))
    location: Mapped[str] = mapped_column(String(120), default="")
    happened_on: Mapped[str] = mapped_column(String(40), default="")  # freeform date/year
    award: Mapped[str] = mapped_column(String(120), default="")  # e.g. "Best Documentary"

    film: Mapped[Film] = relationship(back_populates="screenings")


class FilmPress(Base):
    """A news article or review about the project (News & Reviews)."""

    __tablename__ = "film_press"

    id: Mapped[int] = mapped_column(primary_key=True)
    film_id: Mapped[int] = mapped_column(ForeignKey("films.id"), index=True)
    title: Mapped[str] = mapped_column(String(255))
    outlet: Mapped[str] = mapped_column(String(120), default="")
    url: Mapped[str] = mapped_column(String(512), default="")

    film: Mapped[Film] = relationship(back_populates="press")
