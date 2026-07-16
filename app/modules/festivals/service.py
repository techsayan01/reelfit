"""Festivals service: listing, search/filter, editions and fee schedules."""

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.festivals.models import (
    Category,
    CategoryKind,
    CustomQuestion,
    DeadlineTier,
    Festival,
    FestivalEdition,
    FlagDef,
    HistoricalSelection,
    QuestionType,
    TrackingVisit,
)

# Festival profile fields organizers may edit through update_profile.
PROFILE_FIELDS = (
    "description", "country", "region", "logo_url", "cover_url", "rules",
    "awards_and_prizes", "contact_email", "phone", "website", "twitter",
    "instagram", "venue_name", "venue_address", "founded_year", "is_public",
    "tracking_prefix", "deadline_waiver_days", "reviews_public",
)


def default_tracking_prefix(name: str) -> str:
    letters = [c for c in name.upper() if c.isalpha()]
    return "".join(letters[:3]) or "SUB"


def assign_tracking_number(db: Session, festival_id: int) -> str:
    """Hand out the next submission reference number (e.g. HIL1001)."""
    festival = db.get(Festival, festival_id)
    prefix = festival.tracking_prefix or default_tracking_prefix(festival.name)
    number = f"{prefix}{festival.tracking_next}"
    festival.tracking_next += 1
    return number


def list_festivals(
    db: Session,
    *,
    region: str | None = None,
    query: str | None = None,
    public_only: bool = True,
) -> list[Festival]:
    stmt = select(Festival).order_by(Festival.name)
    if public_only:
        stmt = stmt.where(Festival.is_public.is_(True))
    if region:
        stmt = stmt.where(Festival.region == region)
    if query:
        stmt = stmt.where(Festival.name.ilike(f"%{query}%"))
    return list(db.scalars(stmt))


def update_profile(db: Session, festival_id: int, changes: dict) -> Festival:
    festival = db.get(Festival, festival_id)
    if festival is None:
        raise ValueError("Festival not found")
    for field, value in changes.items():
        if field in PROFILE_FIELDS and value is not None:
            setattr(festival, field, value)
    db.commit()
    return festival


def get_festival(db: Session, festival_id: int) -> Festival | None:
    return db.get(Festival, festival_id)


def get_festival_by_slug(db: Session, slug: str) -> Festival | None:
    return db.scalar(select(Festival).where(Festival.slug == slug))


def get_edition(db: Session, edition_id: int) -> FestivalEdition | None:
    return db.get(FestivalEdition, edition_id)


def current_edition(db: Session, festival_id: int) -> FestivalEdition | None:
    """The edition currently open for submissions, or the next upcoming one."""
    today = date.today()
    return db.scalar(
        select(FestivalEdition)
        .where(FestivalEdition.festival_id == festival_id, FestivalEdition.closes_on >= today)
        .order_by(FestivalEdition.opens_on)
    )


def waiver_window_edition(db: Session, festival_id: int) -> FestivalEdition | None:
    """The most recently closed edition still inside the festival's deadline
    waiver window, or None. Late entries into it need a deadline-waiver code."""
    festival = db.get(Festival, festival_id)
    if festival is None or festival.deadline_waiver_days <= 0:
        return None
    today = date.today()
    edition = db.scalar(
        select(FestivalEdition)
        .where(FestivalEdition.festival_id == festival_id, FestivalEdition.closes_on < today)
        .order_by(FestivalEdition.closes_on.desc())
    )
    if edition is None:
        return None
    days_late = (today - edition.closes_on).days
    return edition if days_late <= festival.deadline_waiver_days else None


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


def all_deadline_tiers(db: Session, edition_id: int) -> list[DeadlineTier]:
    """Every tier of an edition, ordered — powers the public deadline timeline."""
    return list(
        db.scalars(
            select(DeadlineTier)
            .where(DeadlineTier.edition_id == edition_id)
            .order_by(DeadlineTier.deadline)
        )
    )


def category_fee_cents(category: Category, tier: DeadlineTier | None) -> int:
    return max(0, category.base_fee_cents + (tier.fee_delta_cents if tier else 0))


def eligible_category(
    category: Category, project_kind: str, runtime_minutes: int | None, year: int
) -> bool:
    if category.kind.value != project_kind:
        return False
    if category.kind == CategoryKind.FILM:
        if runtime_minutes is None:
            return False
        if not (
            category.min_runtime_minutes <= runtime_minutes <= category.max_runtime_minutes
        ):
            return False
    if category.min_production_year and year < category.min_production_year:
        return False
    return True


def list_questions(db: Session, festival_id: int) -> list[CustomQuestion]:
    return list(
        db.scalars(
            select(CustomQuestion)
            .where(CustomQuestion.festival_id == festival_id)
            .order_by(CustomQuestion.position, CustomQuestion.id)
        )
    )


def questions_for_category(
    db: Session, festival_id: int, category_id: int
) -> list[CustomQuestion]:
    """Questions a submitter must answer for this category (all-category
    questions plus category-specific ones)."""
    return [
        q for q in list_questions(db, festival_id)
        if q.category_id is None or q.category_id == category_id
    ]


def add_question(
    db: Session,
    festival_id: int,
    *,
    field_type: QuestionType,
    question: str,
    options: str = "",
    category_id: int | None = None,
) -> CustomQuestion:
    question = question.strip()
    if not question:
        raise ValueError("The question needs a title.")
    if field_type == QuestionType.DROPDOWN:
        cleaned = [o.strip() for o in options.split("\n") if o.strip()]
        if len(cleaned) < 2:
            raise ValueError("Dropdown questions need at least two options.")
        options = "\n".join(cleaned)
    else:
        options = ""
    row = CustomQuestion(
        festival_id=festival_id,
        field_type=field_type,
        question=question,
        options=options,
        category_id=category_id,
        position=len(list_questions(db, festival_id)),
    )
    db.add(row)
    db.commit()
    return row


def delete_question(db: Session, question_id: int, festival_id: int) -> None:
    q = db.get(CustomQuestion, question_id)
    if q is None or q.festival_id != festival_id:
        raise ValueError("Question not found.")
    db.delete(q)
    db.commit()


def list_flags(db: Session, festival_id: int) -> list[FlagDef]:
    return list(
        db.scalars(
            select(FlagDef)
            .where(FlagDef.festival_id == festival_id)
            .order_by(FlagDef.position, FlagDef.id)
        )
    )


def add_flag(db: Session, festival_id: int, name: str, color: str) -> FlagDef:
    name = name.strip()
    if not name:
        raise ValueError("The flag needs a name.")
    flag = FlagDef(
        festival_id=festival_id, name=name, color=color,
        position=len(list_flags(db, festival_id)),
    )
    db.add(flag)
    db.commit()
    return flag


def delete_flag(db: Session, flag_id: int, festival_id: int) -> None:
    flag = db.get(FlagDef, flag_id)
    if flag is None or flag.festival_id != festival_id:
        raise ValueError("Flag not found.")
    db.delete(flag)
    db.commit()


def record_visit(db: Session, festival_id: int, ref: str) -> None:
    """Log a public listing view with its traffic source."""
    ref = "".join(c for c in ref.strip().lower() if c.isalnum() or c in "-_")[:60] or "direct"
    db.add(TrackingVisit(festival_id=festival_id, ref=ref))
    db.commit()


def visits_by_ref(db: Session, festival_id: int) -> dict[str, int]:
    counts: dict[str, int] = {}
    for v in db.scalars(
        select(TrackingVisit).where(TrackingVisit.festival_id == festival_id)
    ):
        counts[v.ref] = counts.get(v.ref, 0) + 1
    return counts


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
