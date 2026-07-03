"""Festivals service: listing, search/filter, editions and fee schedules."""

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.festivals.models import (
    Category,
    DeadlineTier,
    Festival,
    FestivalEdition,
    HistoricalSelection,
)


def list_festivals(
    db: Session, *, region: str | None = None, query: str | None = None
) -> list[Festival]:
    stmt = select(Festival).order_by(Festival.name)
    if region:
        stmt = stmt.where(Festival.region == region)
    if query:
        stmt = stmt.where(Festival.name.ilike(f"%{query}%"))
    return list(db.scalars(stmt))


def get_festival(db: Session, festival_id: int) -> Festival | None:
    return db.get(Festival, festival_id)


def get_festival_by_slug(db: Session, slug: str) -> Festival | None:
    return db.scalar(select(Festival).where(Festival.slug == slug))


def current_edition(db: Session, festival_id: int) -> FestivalEdition | None:
    """The edition currently open for submissions, or the next upcoming one."""
    today = date.today()
    return db.scalar(
        select(FestivalEdition)
        .where(FestivalEdition.festival_id == festival_id, FestivalEdition.closes_on >= today)
        .order_by(FestivalEdition.opens_on)
    )


def categories_for_edition(db: Session, edition_id: int) -> list[Category]:
    return list(db.scalars(select(Category).where(Category.edition_id == edition_id)))


def active_deadline_tier(db: Session, edition_id: int) -> DeadlineTier | None:
    """Cheapest tier whose deadline has not passed."""
    today = date.today()
    return db.scalar(
        select(DeadlineTier)
        .where(DeadlineTier.edition_id == edition_id, DeadlineTier.deadline >= today)
        .order_by(DeadlineTier.deadline)
    )


def category_fee_cents(category: Category, tier: DeadlineTier | None) -> int:
    return max(0, category.base_fee_cents + (tier.fee_delta_cents if tier else 0))


def eligible_category(
    category: Category, runtime_minutes: int, year: int
) -> bool:
    if not (category.min_runtime_minutes <= runtime_minutes <= category.max_runtime_minutes):
        return False
    if category.min_production_year and year < category.min_production_year:
        return False
    return True


def ingest_historical_selection(
    db: Session,
    festival_id: int,
    *,
    genre: str,
    runtime_minutes: int,
    year: int,
    selected: bool,
    country: str = "",
) -> HistoricalSelection:
    """Structured intake of past selection outcomes (BRD §5.1.3)."""
    row = HistoricalSelection(
        festival_id=festival_id,
        genre=genre.strip().lower(),
        runtime_minutes=runtime_minutes,
        year=year,
        selected=selected,
        country=country,
    )
    db.add(row)
    db.commit()
    return row
