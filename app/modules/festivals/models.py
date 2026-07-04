import enum
from datetime import date, datetime, timezone

from sqlalchemy import Boolean, Date, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class CalibrationStatus(str, enum.Enum):
    """Score reliability label, always shown next to scores (BRD §5.1.3, §7.5)."""

    VALIDATED = "validated"
    CALIBRATING = "calibrating"


class CategoryKind(str, enum.Enum):
    """What a category accepts: finished films or scripts (BRD §5.1.2 lists
    screenplays alongside shorts/features/documentaries)."""

    FILM = "film"
    SCREENPLAY = "screenplay"


class Festival(Base):
    __tablename__ = "festivals"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    slug: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    description: Mapped[str] = mapped_column(Text, default="")
    country: Mapped[str] = mapped_column(String(80), default="")
    region: Mapped[str] = mapped_column(String(80), default="")
    calibration_status: Mapped[CalibrationStatus] = mapped_column(
        Enum(CalibrationStatus), default=CalibrationStatus.CALIBRATING
    )
    # Public profile & branding (BRD §5.1.7). Phase 1 stores URLs; uploads
    # move to object storage later.
    logo_url: Mapped[str] = mapped_column(String(512), default="")
    cover_url: Mapped[str] = mapped_column(String(512), default="")
    rules: Mapped[str] = mapped_column(Text, default="")
    awards_and_prizes: Mapped[str] = mapped_column(Text, default="")
    contact_email: Mapped[str] = mapped_column(String(255), default="")
    phone: Mapped[str] = mapped_column(String(40), default="")
    website: Mapped[str] = mapped_column(String(255), default="")
    twitter: Mapped[str] = mapped_column(String(255), default="")
    instagram: Mapped[str] = mapped_column(String(255), default="")
    venue_name: Mapped[str] = mapped_column(String(255), default="")
    venue_address: Mapped[str] = mapped_column(String(512), default="")
    founded_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Tracking sequence for submission reference numbers (e.g. HIL1001).
    tracking_prefix: Mapped[str] = mapped_column(String(10), default="")
    tracking_next: Mapped[int] = mapped_column(Integer, default=1001)
    # How many days after the final deadline deadline-waiver codes still work
    # (0 = no late entries).
    deadline_waiver_days: Mapped[int] = mapped_column(Integer, default=0)
    # Non-public listings are visible only to their own staff — useful while
    # a festival sets up its profile before launch.
    is_public: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    editions: Mapped[list["FestivalEdition"]] = relationship(back_populates="festival")


class FestivalEdition(Base):
    """A yearly cycle of a festival (multi-edition management, BRD §5.1.1)."""

    __tablename__ = "festival_editions"

    id: Mapped[int] = mapped_column(primary_key=True)
    festival_id: Mapped[int] = mapped_column(ForeignKey("festivals.id"), index=True)
    label: Mapped[str] = mapped_column(String(80))  # e.g. "2026"
    opens_on: Mapped[date] = mapped_column(Date)
    closes_on: Mapped[date] = mapped_column(Date)
    notification_on: Mapped[date | None] = mapped_column(Date, nullable=True)

    festival: Mapped[Festival] = relationship(back_populates="editions")
    categories: Mapped[list["Category"]] = relationship(back_populates="edition")
    deadline_tiers: Mapped[list["DeadlineTier"]] = relationship(back_populates="edition")


class Category(Base):
    """Submission category with runtime/format and eligibility rules (BRD §5.1.2)."""

    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(primary_key=True)
    edition_id: Mapped[int] = mapped_column(ForeignKey("festival_editions.id"), index=True)
    name: Mapped[str] = mapped_column(String(120))  # e.g. "Short Documentary"
    kind: Mapped[CategoryKind] = mapped_column(Enum(CategoryKind), default=CategoryKind.FILM)
    # Runtime rules apply to film categories only.
    min_runtime_minutes: Mapped[int] = mapped_column(Integer, default=0)
    max_runtime_minutes: Mapped[int] = mapped_column(Integer, default=600)
    base_fee_cents: Mapped[int] = mapped_column(Integer, default=0)
    requires_premiere: Mapped[bool] = mapped_column(Boolean, default=False)
    min_production_year: Mapped[int | None] = mapped_column(Integer, nullable=True)

    edition: Mapped[FestivalEdition] = relationship(back_populates="categories")


class DeadlineTier(Base):
    """Early bird / regular / late / extended pricing tiers (BRD §5.1.2)."""

    __tablename__ = "deadline_tiers"

    id: Mapped[int] = mapped_column(primary_key=True)
    edition_id: Mapped[int] = mapped_column(ForeignKey("festival_editions.id"), index=True)
    name: Mapped[str] = mapped_column(String(80))
    deadline: Mapped[date] = mapped_column(Date)
    # Fee adjustment applied to the category base fee, in cents (can be negative
    # for early-bird pricing).
    fee_delta_cents: Mapped[int] = mapped_column(Integer, default=0)

    edition: Mapped[FestivalEdition] = relationship(back_populates="deadline_tiers")


class HistoricalSelection(Base):
    """Past selection outcome used to calibrate the fit-scoring engine (BRD §5.1.3)."""

    __tablename__ = "historical_selections"

    id: Mapped[int] = mapped_column(primary_key=True)
    festival_id: Mapped[int] = mapped_column(ForeignKey("festivals.id"), index=True)
    genre: Mapped[str] = mapped_column(String(80))
    runtime_minutes: Mapped[int] = mapped_column(Integer)
    year: Mapped[int] = mapped_column(Integer)
    country: Mapped[str] = mapped_column(String(80), default="")
    selected: Mapped[bool] = mapped_column(Boolean)
