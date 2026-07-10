from datetime import date

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from app.api.deps import DbDep
from app.modules.dashboards import service as dashboards
from app.modules.festivals import service as festivals
from app.modules.reviews import service as reviews
from app.modules.submissions.models import SELECTED_STATUSES

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
        "logo_url": f.logo_url,
        "cover_url": f.cover_url,
        "contact_email": f.contact_email,
        "phone": f.phone,
        "website": f.website,
        "twitter": f.twitter,
        "instagram": f.instagram,
        "venue_name": f.venue_name,
        "venue_address": f.venue_address,
        "founded_year": f.founded_year,
        "is_public": f.is_public,
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


def public_stats(db, festival) -> dict:
    """Honest, platform-verified stats — computed from real submission and
    review records, never self-reported (the transparency angle vs. incumbents)."""
    overview = dashboards.festival_overview(db, festival.id)
    festival_reviews = reviews.reviews_for_festival(db, festival.id)
    avg_rating = (
        round(sum(r.rating for r in festival_reviews) / len(festival_reviews), 1)
        if festival_reviews
        else None
    )
    years_running = (
        date.today().year - festival.founded_year + 1 if festival.founded_year else None
    )
    selected = sum(
        overview.by_status.get(s.value, 0) for s in SELECTED_STATUSES
    )
    return {
        "total_submissions": overview.total_submissions,
        "selected": selected,
        "review_count": len(festival_reviews),
        "avg_rating": avg_rating,
        "years_running": years_running,
    }


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


@router.get("/{slug}/laurel.svg")
def public_laurel(db: DbDep, slug: str, text: str = "OFFICIAL SELECTION", variant: str = "black"):
    """Public laurel download (laurel center) — festivals share this link
    with their laurel recipients."""
    from app.modules.certificates import service as certificates

    festival = festivals.get_festival_by_slug(db, slug)
    if festival is None:
        raise HTTPException(404, "Festival not found")
    edition = festivals.current_edition(db, festival.id)
    label = edition.label if edition else ""
    svg = certificates.render_laurel_svg(
        festival.name, label, headline=text,
        variant="white" if variant == "white" else "black",
    )
    return Response(content=svg, media_type="image/svg+xml")


@router.get("/{slug}")
def festival_detail(db: DbDep, slug: str, ref: str = ""):
    festival = festivals.get_festival_by_slug(db, slug)
    if festival is None or not festival.is_public:
        raise HTTPException(404, "Festival not found")
    # Marketing attribution: every public view is logged with its source.
    festivals.record_visit(db, festival.id, ref)
    edition = festivals.current_edition(db, festival.id)
    categories = festivals.categories_for_edition(db, edition.id) if edition else []
    tier = festivals.active_deadline_tier(db, edition.id) if edition else None
    all_tiers = festivals.all_deadline_tiers(db, edition.id) if edition else []
    festival_reviews = reviews.reviews_for_festival(db, festival.id)

    # Deadline timeline: opening date, each fee tier, notification, event dates.
    timeline = []
    if edition:
        timeline.append({
            "label": "Opening date", "date": edition.opens_on.isoformat(),
            "is_current": False,
        })
        for t in all_tiers:
            timeline.append({
                "label": t.name,
                "date": t.deadline.isoformat(),
                "is_current": tier is not None and t.id == tier.id,
            })
        if edition.notification_on:
            timeline.append({
                "label": "Notification date",
                "date": edition.notification_on.isoformat(),
                "is_current": False,
            })

    return {
        "festival": {
            **festival_payload(festival),
            "rules": festival.rules,
            "awards_and_prizes": festival.awards_and_prizes,
        },
        "edition": edition_payload(edition),
        "tier": tier_payload(tier),
        "timeline": timeline,
        "stats": public_stats(db, festival),
        "categories": [
            {
                "id": c.id,
                "name": c.name,
                "kind": c.kind.value,
                "min_runtime_minutes": c.min_runtime_minutes,
                "max_runtime_minutes": c.max_runtime_minutes,
                "fee_cents": festivals.category_fee_cents(c, tier),
            }
            for c in categories
        ],
        "reviews_public": festival.reviews_public,
        "reviews": [
            {
                "id": r.id,
                "rating": r.rating,
                "text": r.text,
                "festival_reply": r.festival_reply,
                "created_at": r.created_at.isoformat(),
            }
            for r in festival_reviews
        ] if festival.reviews_public else [],
    }
