from fastapi import APIRouter, HTTPException

from app.api.deps import DbDep
from app.modules.festivals import service as festivals
from app.modules.reviews import service as reviews

router = APIRouter(prefix="/api/festivals", tags=["festivals"])


def festival_payload(f) -> dict:
    return {
        "id": f.id,
        "name": f.name,
        "slug": f.slug,
        "description": f.description,
        "country": f.country,
        "region": f.region,
        "calibration_status": f.calibration_status.value,
    }


def edition_payload(e) -> dict | None:
    if e is None:
        return None
    return {
        "id": e.id,
        "label": e.label,
        "opens_on": e.opens_on.isoformat(),
        "closes_on": e.closes_on.isoformat(),
        "notification_on": e.notification_on.isoformat() if e.notification_on else None,
    }


def tier_payload(t) -> dict | None:
    if t is None:
        return None
    return {"id": t.id, "name": t.name, "deadline": t.deadline.isoformat()}


@router.get("")
def list_festivals(db: DbDep, q: str = "", region: str = ""):
    items = festivals.list_festivals(db, region=region or None, query=q or None)
    out = []
    for f in items:
        edition = festivals.current_edition(db, f.id)
        tier = festivals.active_deadline_tier(db, edition.id) if edition else None
        out.append({
            "festival": festival_payload(f),
            "edition": edition_payload(edition),
            "tier": tier_payload(tier),
        })
    return {"festivals": out}


@router.get("/{slug}")
def festival_detail(db: DbDep, slug: str):
    festival = festivals.get_festival_by_slug(db, slug)
    if festival is None:
        raise HTTPException(404, "Festival not found")
    edition = festivals.current_edition(db, festival.id)
    categories = festivals.categories_for_edition(db, edition.id) if edition else []
    tier = festivals.active_deadline_tier(db, edition.id) if edition else None
    festival_reviews = reviews.reviews_for_festival(db, festival.id)
    return {
        "festival": festival_payload(festival),
        "edition": edition_payload(edition),
        "tier": tier_payload(tier),
        "categories": [
            {
                "id": c.id,
                "name": c.name,
                "min_runtime_minutes": c.min_runtime_minutes,
                "max_runtime_minutes": c.max_runtime_minutes,
                "fee_cents": festivals.category_fee_cents(c, tier),
            }
            for c in categories
        ],
        "reviews": [
            {
                "id": r.id,
                "rating": r.rating,
                "text": r.text,
                "festival_reply": r.festival_reply,
                "created_at": r.created_at.isoformat(),
            }
            for r in festival_reviews
        ],
    }
