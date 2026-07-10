import csv
import io
from collections import defaultdict

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy import select

from app.api.deps import DbDep, OrganizerDep
from app.api.routes_festivals import festival_payload
from app.modules.accounts import service as accounts
from app.modules.accounts.models import FestivalMembership, OrgRole
from datetime import date, timedelta

from app.modules.certificates import service as certificates
from app.modules.dashboards import service as dashboards
from app.modules.discounts import service as discounts
from app.modules.discounts.models import CodeType, DiscountKind
from app.modules.festivals import service as festivals
from app.modules.festivals.models import QuestionType
from app.modules.jury import service as jury
from app.modules.jury.models import Recommendation
from app.modules.notifications import service as notifications
from app.modules.notifications.models import NotificationKind
from app.modules.reviews import service as reviews
from app.modules.submissions import service as submissions
from app.modules.submissions.models import (
    SELECTED_STATUSES,
    ExportConfig,
    SubmissionStatus,
)

router = APIRouter(prefix="/api/festival", tags=["festival-admin"])

# Roles allowed to change judging status (viewer is read-only; BRD §5.1.1).
STATUS_ROLES = {OrgRole.OWNER, OrgRole.PROGRAMMER}


class StatusIn(BaseModel):
    status: SubmissionStatus


class ReplyIn(BaseModel):
    reply_text: str


class NoteIn(BaseModel):
    text: str


class StaffIn(BaseModel):
    email: str
    role: OrgRole


class CriterionIn(BaseModel):
    name: str
    weight: float = 1.0


class AssignIn(BaseModel):
    user_id: int


class ScoreItem(BaseModel):
    criterion_id: int
    score: int


class RateIn(BaseModel):
    scores: list[ScoreItem]
    comment: str = ""
    recommendation: Recommendation | None = None


class QuestionIn(BaseModel):
    field_type: QuestionType
    question: str
    options: str = ""
    category_id: int | None = None


class FlagIn(BaseModel):
    name: str
    color: str = "#C0392B"


class SetFlagIn(BaseModel):
    flag_id: int | None = None


class MessageIn(BaseModel):
    audience: str  # "submitters" | "staff"
    subject: str
    body: str = ""


class WebhookIn(BaseModel):
    url: str
    events: list[str]


class ExportConfigIn(BaseModel):
    name: str
    columns: list[str]


# Column keys available for submission exports. Contact stays the masked
# relay — PII never leaves through exports (BRD §7.5).
EXPORT_COLUMNS = [
    "tracking_number", "film_title", "project_type", "genre",
    "runtime_minutes", "year", "country", "language", "category",
    "status", "fee_paid", "discount_code", "source", "submitted_on",
    "rating", "contact",
]


# Roles allowed to score submissions against the rubric.
RATING_ROLES = {OrgRole.OWNER, OrgRole.PROGRAMMER, OrgRole.JURY}


class ProfileIn(BaseModel):
    """Editable public-profile fields (BRD §5.1.7). All optional — only sent
    fields change."""

    description: str | None = None
    country: str | None = None
    region: str | None = None
    logo_url: str | None = None
    cover_url: str | None = None
    rules: str | None = None
    awards_and_prizes: str | None = None
    contact_email: str | None = None
    phone: str | None = None
    tracking_prefix: str | None = None
    website: str | None = None
    twitter: str | None = None
    instagram: str | None = None
    venue_name: str | None = None
    venue_address: str | None = None
    founded_year: int | None = None
    is_public: bool | None = None
    deadline_waiver_days: int | None = None
    reviews_public: bool | None = None


class CodeIn(BaseModel):
    code: str
    code_type: CodeType
    label: str = ""
    kind: DiscountKind = DiscountKind.PERCENT
    amount: int = 0
    category_id: int | None = None
    valid_from: date | None = None
    valid_to: date | None = None
    redemption_limit: int | None = None
    also_deadline_waiver: bool = False
    one_use_per_submitter: bool = False


def _membership(db, user) -> FestivalMembership:
    membership = db.scalar(
        select(FestivalMembership).where(FestivalMembership.user_id == user.id)
    )
    if membership is None:
        raise HTTPException(403, "Your account isn't linked to a festival yet.")
    return membership


@router.get("/dashboard")
def festival_dashboard(db: DbDep, user: OrganizerDep):
    membership = _membership(db, user)
    festival = festivals.get_festival(db, membership.festival_id)
    overview = dashboards.festival_overview(db, festival.id)
    subs = submissions.submissions_for_festival(db, festival.id)
    festival_reviews = reviews.reviews_for_festival(db, festival.id)

    categories = {
        c.id: c.name
        for e in festivals.get_festival(db, membership.festival_id).editions
        for c in festivals.categories_for_edition(db, e.id)
    }
    criteria = jury.criteria_for_festival(db, membership.festival_id)
    flags = {f.id: f for f in festivals.list_flags(db, membership.festival_id)}
    sub_rows = []
    for s in subs:
        film = accounts.get_film(db, s.film_id)
        average, judge_count = jury.rating_summary(db, s.id, criteria)
        flag = flags.get(s.flag_id)
        sub_rows.append({
            "rating": average,
            "rating_judges": judge_count,
            "flag": {"id": flag.id, "name": flag.name, "color": flag.color} if flag else None,
            "id": s.id,
            "tracking_number": s.tracking_number,
            "film_title": film.title,
            "film_kind": film.kind.value,
            "film_genre": film.genre,
            "film_runtime_minutes": film.runtime_minutes,
            "film_country": film.country,
            "category": categories.get(s.category_id, ""),
            # Masked contact: festivals see the relay handle, never an email
            # (BRD §5.2.1), unless the filmmaker revoked access entirely.
            "contact": "access revoked" if s.relay_revoked else s.relay_contact_id,
            "fee_paid_cents": s.fee_paid_cents,
            "status": s.status.value,
            # Status changes always notify the filmmaker automatically.
            "notified": s.status != SubmissionStatus.RECEIVED,
            "created_at": s.created_at.isoformat(),
        })

    return {
        "festival": {
            **festival_payload(festival),
            "rules": festival.rules,
            "deadline_waiver_days": festival.deadline_waiver_days,
            "reviews_public": festival.reviews_public,
        },
        "role": membership.role.value,
        "can_edit_profile": membership.role == OrgRole.OWNER,
        "can_update": membership.role in STATUS_ROLES,
        "overview": {
            "total_submissions": overview.total_submissions,
            "by_status": overview.by_status,
            "gross_revenue_cents": overview.gross_revenue_cents,
            "discounted_count": overview.discounted_count,
        },
        "submissions": sub_rows,
        "flags": [
            {"id": f.id, "name": f.name, "color": f.color} for f in flags.values()
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
        "statuses": [s.value for s in SubmissionStatus],
    }


@router.patch("/profile")
def update_profile(db: DbDep, user: OrganizerDep, body: ProfileIn):
    membership = _membership(db, user)
    if membership.role != OrgRole.OWNER:
        raise HTTPException(403, "Only the festival owner can edit the public profile.")
    festival = festivals.update_profile(
        db, membership.festival_id, body.model_dump(exclude_unset=True)
    )
    return {"festival": {**festival_payload(festival), "rules": festival.rules}}


def _require_owner(membership) -> None:
    if membership.role != OrgRole.OWNER:
        raise HTTPException(403, "Only the festival owner can do that.")


@router.get("/staff")
def list_staff(db: DbDep, user: OrganizerDep):
    membership = _membership(db, user)
    return {
        "staff": [
            {
                "membership_id": m.id,
                "user_id": u.id,
                "display_name": u.display_name,
                "email": u.email,
                "role": m.role.value,
            }
            for m, u in accounts.festival_staff(db, membership.festival_id)
        ]
    }


@router.post("/staff", status_code=201)
def add_staff(db: DbDep, user: OrganizerDep, body: StaffIn):
    membership = _membership(db, user)
    _require_owner(membership)
    if body.role == OrgRole.OWNER:
        raise HTTPException(400, "A festival has one owner.")
    try:
        new_membership = accounts.add_staff(
            db, membership.festival_id, body.email, body.role
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    return {"membership_id": new_membership.id}


@router.delete("/staff/{membership_id}")
def remove_staff(db: DbDep, user: OrganizerDep, membership_id: int):
    membership = _membership(db, user)
    _require_owner(membership)
    try:
        accounts.remove_staff(db, membership_id, membership.festival_id)
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    return {"ok": True}


@router.get("/rubric")
def list_rubric(db: DbDep, user: OrganizerDep):
    membership = _membership(db, user)
    return {
        "criteria": [
            {"id": c.id, "name": c.name, "weight": c.weight}
            for c in jury.criteria_for_festival(db, membership.festival_id)
        ]
    }


@router.post("/rubric", status_code=201)
def add_criterion(db: DbDep, user: OrganizerDep, body: CriterionIn):
    membership = _membership(db, user)
    _require_owner(membership)
    if not body.name.strip():
        raise HTTPException(400, "Criterion needs a name.")
    criterion = jury.add_criterion(db, membership.festival_id, body.name, body.weight)
    return {"id": criterion.id}


@router.delete("/rubric/{criterion_id}")
def delete_criterion(db: DbDep, user: OrganizerDep, criterion_id: int):
    membership = _membership(db, user)
    _require_owner(membership)
    try:
        jury.delete_criterion(db, criterion_id, membership.festival_id)
    except ValueError as exc:
        raise HTTPException(404, str(exc))
    return {"ok": True}


def _festival_categories(db, festival_id: int) -> list:
    festival = festivals.get_festival(db, festival_id)
    return [
        c for e in festival.editions for c in festivals.categories_for_edition(db, e.id)
    ]


@router.get("/questions")
def list_questions(db: DbDep, user: OrganizerDep):
    membership = _membership(db, user)
    return {
        "questions": [
            {
                "id": q.id,
                "field_type": q.field_type.value,
                "question": q.question,
                "options": q.options_list(),
                "category_id": q.category_id,
            }
            for q in festivals.list_questions(db, membership.festival_id)
        ],
        "categories": [
            {"id": c.id, "name": c.name}
            for c in _festival_categories(db, membership.festival_id)
        ],
    }


@router.post("/questions", status_code=201)
def add_question(db: DbDep, user: OrganizerDep, body: QuestionIn):
    membership = _membership(db, user)
    _require_owner(membership)
    try:
        q = festivals.add_question(
            db, membership.festival_id,
            field_type=body.field_type, question=body.question,
            options=body.options, category_id=body.category_id,
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    return {"id": q.id}


@router.delete("/questions/{question_id}")
def delete_question(db: DbDep, user: OrganizerDep, question_id: int):
    membership = _membership(db, user)
    _require_owner(membership)
    try:
        submissions.delete_answers_for_question(db, question_id)
        festivals.delete_question(db, question_id, membership.festival_id)
    except ValueError as exc:
        raise HTTPException(404, str(exc))
    return {"ok": True}


@router.get("/flags")
def list_flags(db: DbDep, user: OrganizerDep):
    membership = _membership(db, user)
    return {
        "flags": [
            {"id": f.id, "name": f.name, "color": f.color}
            for f in festivals.list_flags(db, membership.festival_id)
        ]
    }


@router.post("/flags", status_code=201)
def add_flag(db: DbDep, user: OrganizerDep, body: FlagIn):
    membership = _membership(db, user)
    _require_owner(membership)
    try:
        flag = festivals.add_flag(db, membership.festival_id, body.name, body.color)
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    return {"id": flag.id}


@router.delete("/flags/{flag_id}")
def delete_flag(db: DbDep, user: OrganizerDep, flag_id: int):
    membership = _membership(db, user)
    _require_owner(membership)
    try:
        submissions.clear_flag(db, flag_id)
        festivals.delete_flag(db, flag_id, membership.festival_id)
    except ValueError as exc:
        raise HTTPException(404, str(exc))
    return {"ok": True}


@router.post("/rubric/defaults", status_code=201)
def add_default_rubric(db: DbDep, user: OrganizerDep):
    membership = _membership(db, user)
    _require_owner(membership)
    created = jury.add_default_criteria(db, membership.festival_id)
    return {"created": len(created)}


@router.get("/messages")
def list_messages(db: DbDep, user: OrganizerDep):
    membership = _membership(db, user)
    return {
        "messages": [
            {
                "id": m.id,
                "audience": m.audience,
                "subject": m.subject,
                "recipient_count": m.recipient_count,
                "created_at": m.created_at.isoformat(),
            }
            for m in notifications.bulk_messages(db, membership.festival_id)
        ]
    }


@router.post("/messages", status_code=201)
def send_message(db: DbDep, user: OrganizerDep, body: MessageIn):
    """Bulk message to all submitters or all staff (BRD §5.1.4)."""
    membership = _membership(db, user)
    if membership.role not in STATUS_ROLES:
        raise HTTPException(403, "Your role can't send bulk messages.")
    if body.audience not in ("submitters", "staff"):
        raise HTTPException(400, "Audience is submitters or staff.")
    if not body.subject.strip():
        raise HTTPException(400, "The message needs a subject.")
    festival = festivals.get_festival(db, membership.festival_id)
    if body.audience == "submitters":
        recipient_ids = {
            accounts.get_film(db, s.film_id).filmmaker_id
            for s in submissions.submissions_for_festival(db, festival.id)
        }
    else:
        recipient_ids = {
            u.id for _, u in accounts.festival_staff(db, festival.id) if u.id != user.id
        }
    message = notifications.send_bulk(
        db,
        festival_id=festival.id,
        festival_name=festival.name,
        audience=body.audience,
        subject=body.subject.strip(),
        body=body.body.strip(),
        recipient_user_ids=sorted(recipient_ids),
    )
    return {"id": message.id, "recipient_count": message.recipient_count}


@router.get("/insights")
def judging_insights(db: DbDep, user: OrganizerDep):
    """Per-judge progress: assigned, judged, % judged, runtime assigned."""
    membership = _membership(db, user)
    subs = submissions.submissions_for_festival(db, membership.festival_id)
    films = {s.id: accounts.get_film(db, s.film_id) for s in subs}
    staff_names = {
        u.id: u.display_name
        for _, u in accounts.festival_staff(db, membership.festival_id)
    }

    per_judge: dict[int, dict] = {}
    judged_submissions: set[int] = set()
    for s in subs:
        for a in jury.assignments_for_submission(db, s.id):
            row = per_judge.setdefault(a.juror_user_id, {
                "assigned": 0, "judged": 0, "runtime_minutes": 0,
            })
            row["assigned"] += 1
            row["runtime_minutes"] += films[s.id].runtime_minutes or 0
            if a.status.value == "done":
                row["judged"] += 1
                judged_submissions.add(s.id)

    judges = [
        {
            "user_id": user_id,
            "name": staff_names.get(user_id, "former staff"),
            "assigned": row["assigned"],
            "judged": row["judged"],
            "pct_judged": round(100 * row["judged"] / row["assigned"]) if row["assigned"] else 0,
            "runtime_minutes_assigned": row["runtime_minutes"],
        }
        for user_id, row in sorted(per_judge.items())
    ]
    return {
        "totals": {
            "judges": len(per_judge),
            "submissions": len(subs),
            "judged": len(judged_submissions),
            "not_judged": len(subs) - len(judged_submissions),
            "pct_judged": round(100 * len(judged_submissions) / len(subs)) if subs else 0,
        },
        "judges": judges,
    }


def _export_rows(db, membership) -> list[dict]:
    """One dict per submission with every exportable column."""
    subs = submissions.submissions_for_festival(db, membership.festival_id)
    categories = {
        c.id: c.name for c in _festival_categories(db, membership.festival_id)
    }
    criteria = jury.criteria_for_festival(db, membership.festival_id)
    rows = []
    for s in subs:
        film = accounts.get_film(db, s.film_id)
        average, _ = jury.rating_summary(db, s.id, criteria)
        rows.append({
            "tracking_number": s.tracking_number,
            "film_title": film.title,
            "project_type": film.kind.value,
            "genre": film.genre,
            "runtime_minutes": film.runtime_minutes or "",
            "year": film.year,
            "country": film.country,
            "language": film.language,
            "category": categories.get(s.category_id, ""),
            "status": s.status.value,
            "fee_paid": f"{s.fee_paid_cents / 100:.2f}",
            "discount_code": s.discount_code,
            "source": s.source,
            "submitted_on": s.created_at.date().isoformat(),
            "rating": average if average is not None else "",
            "contact": "access revoked" if s.relay_revoked else s.relay_contact_id,
            "_month": s.created_at.strftime("%B %Y"),
            "_fee_cents": s.fee_paid_cents,
        })
    return rows


def _csv_response(filename: str, header: list[str], rows: list[list]) -> Response:
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(header)
    writer.writerows(rows)
    return Response(
        content=buf.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/marketing")
def marketing_summary(db: DbDep, user: OrganizerDep):
    """Marketing attribution & conversion analytics (BRD §5.1.5 ★): page
    views → submissions → conversion rate, by traffic source."""
    membership = _membership(db, user)
    visits = festivals.visits_by_ref(db, membership.festival_id)
    subs = submissions.submissions_for_festival(db, membership.festival_id)
    sub_counts: dict[str, int] = defaultdict(int)
    revenue: dict[str, int] = defaultdict(int)
    for s in subs:
        sub_counts[s.source] += 1
        revenue[s.source] += s.fee_paid_cents
    sources = sorted(set(visits) | set(sub_counts))
    rows = []
    for source in sources:
        v, c = visits.get(source, 0), sub_counts.get(source, 0)
        rows.append({
            "source": source,
            "views": v,
            "submissions": c,
            "conversion_pct": round(100 * c / v, 1) if v else None,
            "revenue_cents": revenue.get(source, 0),
        })
    rows.sort(key=lambda r: (-r["submissions"], -r["views"]))
    festival = festivals.get_festival(db, membership.festival_id)
    return {
        "rows": rows,
        "totals": {
            "views": sum(visits.values()),
            "submissions": len(subs),
            "revenue_cents": sum(s.fee_paid_cents for s in subs),
        },
        "share_base": f"/festivals/{festival.slug}?ref=",
    }


@router.get("/transactions")
def transactions(db: DbDep, user: OrganizerDep):
    """Monthly ledger of fees collected."""
    membership = _membership(db, user)
    rows = _export_rows(db, membership)
    months: dict[str, dict] = {}
    for r in rows:
        m = months.setdefault(r["_month"], {"total_cents": 0, "items": []})
        m["total_cents"] += r["_fee_cents"]
        m["items"].append({
            "tracking_number": r["tracking_number"],
            "film_title": r["film_title"],
            "amount_cents": r["_fee_cents"],
            "date": r["submitted_on"],
        })
    return {
        "months": [
            {"month": month, **data} for month, data in months.items()
        ]
    }


@router.get("/reports")
def create_report(db: DbDep, user: OrganizerDep, report: str = "sales_by_category"):
    """Aggregate CSV reports (reports builder)."""
    membership = _membership(db, user)
    rows = _export_rows(db, membership)

    def aggregate(key: str):
        agg: dict[str, dict] = defaultdict(lambda: {"count": 0, "cents": 0})
        for r in rows:
            bucket = agg[str(r[key]) or "—"]
            bucket["count"] += 1
            bucket["cents"] += r["_fee_cents"]
        return [
            [name, data["count"], f"{data['cents'] / 100:.2f}"]
            for name, data in sorted(agg.items())
        ]

    reports = {
        "sales_by_category": ("category", "Category"),
        "sales_by_status": ("status", "Judging status"),
        "sales_by_month": ("_month", "Month"),
        "sales_by_source": ("source", "Source"),
    }
    if report not in reports:
        raise HTTPException(400, "Unknown report type.")
    key, label = reports[report]
    return _csv_response(
        f"reelfit-{report}.csv",
        [label, "Submissions", "Fees (USD)"],
        aggregate(key),
    )


@router.get("/export-configs")
def list_export_configs(db: DbDep, user: OrganizerDep):
    membership = _membership(db, user)
    configs = db.scalars(
        select(ExportConfig).where(ExportConfig.festival_id == membership.festival_id)
    )
    return {
        "configs": [
            {"id": c.id, "name": c.name, "columns": c.columns.split(",")}
            for c in configs
        ],
        "available_columns": EXPORT_COLUMNS,
    }


@router.post("/export-configs", status_code=201)
def add_export_config(db: DbDep, user: OrganizerDep, body: ExportConfigIn):
    membership = _membership(db, user)
    _require_owner(membership)
    columns = [c for c in body.columns if c in EXPORT_COLUMNS]
    if not body.name.strip() or not columns:
        raise HTTPException(400, "A configuration needs a name and at least one column.")
    config = ExportConfig(
        festival_id=membership.festival_id,
        name=body.name.strip(),
        columns=",".join(columns),
    )
    db.add(config)
    db.commit()
    return {"id": config.id}


@router.delete("/export-configs/{config_id}")
def delete_export_config(db: DbDep, user: OrganizerDep, config_id: int):
    membership = _membership(db, user)
    _require_owner(membership)
    config = db.get(ExportConfig, config_id)
    if config is None or config.festival_id != membership.festival_id:
        raise HTTPException(404, "Configuration not found.")
    db.delete(config)
    db.commit()
    return {"ok": True}


@router.get("/export")
def export_submissions(db: DbDep, user: OrganizerDep, config_id: int | None = None):
    """Submission spreadsheet export, using a saved configuration's columns
    or every column."""
    membership = _membership(db, user)
    columns = EXPORT_COLUMNS
    if config_id is not None:
        config = db.get(ExportConfig, config_id)
        if config is None or config.festival_id != membership.festival_id:
            raise HTTPException(404, "Configuration not found.")
        columns = config.columns.split(",")
    rows = _export_rows(db, membership)
    return _csv_response(
        "reelfit-submissions.csv",
        columns,
        [[r[c] for c in columns] for r in rows],
    )


@router.get("/webhooks")
def list_webhooks(db: DbDep, user: OrganizerDep):
    membership = _membership(db, user)
    return {
        "webhooks": [
            {
                "id": w.id,
                "url": w.url,
                "events": w.events.split(","),
                "active": w.active,
                "recent": [
                    {
                        "event": d.event,
                        "ok": d.ok,
                        "status_code": d.status_code,
                        "created_at": d.created_at.isoformat(),
                    }
                    for d in notifications.recent_deliveries(db, w.id)
                ],
            }
            for w in notifications.list_webhooks(db, membership.festival_id)
        ],
        "available_events": list(notifications.WEBHOOK_EVENTS),
    }


@router.post("/webhooks", status_code=201)
def add_webhook(db: DbDep, user: OrganizerDep, body: WebhookIn):
    membership = _membership(db, user)
    _require_owner(membership)
    try:
        endpoint = notifications.add_webhook(
            db, membership.festival_id, body.url, body.events
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    return {"id": endpoint.id}


@router.delete("/webhooks/{endpoint_id}")
def delete_webhook(db: DbDep, user: OrganizerDep, endpoint_id: int):
    membership = _membership(db, user)
    _require_owner(membership)
    try:
        notifications.delete_webhook(db, endpoint_id, membership.festival_id)
    except ValueError as exc:
        raise HTTPException(404, str(exc))
    return {"ok": True}


@router.get("/ad.svg")
def ad_creator(
    db: DbDep,
    user: OrganizerDep,
    headline: str = "Submissions open",
    subline: str = "",
    cta: str = "Submit now",
    bg: str = "amber",
    fmt: str = "square",
):
    """Ad creator: social graphics in the festival's Reelfit branding."""
    membership = _membership(db, user)
    festival = festivals.get_festival(db, membership.festival_id)
    svg = certificates.render_ad_svg(
        festival.name, headline, subline=subline, cta=cta,
        background=bg, fmt="square" if fmt == "square" else "wide",
    )
    return Response(content=svg, media_type="image/svg+xml")


@router.get("/codes")
def list_codes(db: DbDep, user: OrganizerDep):
    membership = _membership(db, user)
    festival = festivals.get_festival(db, membership.festival_id)
    edition = festivals.current_edition(db, festival.id)
    categories = festivals.categories_for_edition(db, edition.id) if edition else []
    waiver_through = None
    if festival.deadline_waiver_days > 0:
        base = edition.closes_on if edition else None
        if base is None:
            past = festivals.waiver_window_edition(db, festival.id)
            base = past.closes_on if past else None
        if base:
            waiver_through = (
                base + timedelta(days=festival.deadline_waiver_days)
            ).isoformat()
    return {
        "codes": [
            {
                "id": c.id,
                "code": c.code,
                "code_type": c.code_type.value,
                "label": c.label,
                "kind": c.kind.value,
                "amount": c.amount,
                "category_id": c.category_id,
                "valid_from": c.valid_from.isoformat() if c.valid_from else None,
                "valid_to": c.valid_to.isoformat() if c.valid_to else None,
                "redemption_limit": c.redemption_limit,
                "redemptions": c.redemptions,
                "also_deadline_waiver": c.also_deadline_waiver,
                "one_use_per_submitter": c.one_use_per_submitter,
            }
            for c in discounts.list_codes(db, membership.festival_id)
        ],
        "categories": [{"id": c.id, "name": c.name} for c in categories],
        "deadline_waiver_days": festival.deadline_waiver_days,
        "waiver_accepted_through": waiver_through,
    }


@router.post("/codes", status_code=201)
def create_code(db: DbDep, user: OrganizerDep, body: CodeIn):
    membership = _membership(db, user)
    _require_owner(membership)
    try:
        dc = discounts.create_code(
            db, membership.festival_id,
            code=body.code,
            code_type=body.code_type,
            label=body.label,
            kind=body.kind,
            amount=body.amount,
            category_id=body.category_id,
            valid_from=body.valid_from,
            valid_to=body.valid_to,
            redemption_limit=body.redemption_limit,
            also_deadline_waiver=body.also_deadline_waiver,
            one_use_per_submitter=body.one_use_per_submitter,
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    return {"id": dc.id, "code": dc.code}


@router.delete("/codes/{code_id}")
def delete_code(db: DbDep, user: OrganizerDep, code_id: int):
    membership = _membership(db, user)
    _require_owner(membership)
    try:
        discounts.delete_code(db, code_id, membership.festival_id)
    except ValueError as exc:
        raise HTTPException(404, str(exc))
    return {"ok": True}


@router.get("/queue")
def my_queue(db: DbDep, user: OrganizerDep):
    """The signed-in staff member's review queue (pending assignments)."""
    membership = _membership(db, user)
    rows = []
    for assignment in jury.queue_for_juror(db, user.id):
        sub = submissions.get_submission(db, assignment.submission_id)
        if sub is None or sub.festival_id != membership.festival_id:
            continue
        film = accounts.get_film(db, sub.film_id)
        rows.append({
            "submission_id": sub.id,
            "tracking_number": sub.tracking_number,
            "film_title": film.title,
            "status": assignment.status.value,
        })
    return {"queue": rows}


def _own_submission(db, membership, submission_id: int):
    sub = submissions.get_submission(db, submission_id)
    if sub is None or sub.festival_id != membership.festival_id:
        raise HTTPException(404, "Submission not found")
    return sub


@router.get("/submissions/{submission_id}")
def submission_detail(db: DbDep, user: OrganizerDep, submission_id: int):
    """Everything a programmer needs to judge one entry. The filmmaker's
    public profile is shown; direct contact stays behind the masked relay."""
    membership = _membership(db, user)
    sub = _own_submission(db, membership, submission_id)
    film = accounts.get_film(db, sub.film_id)
    filmmaker = accounts.get_user(db, film.filmmaker_id)
    festival = festivals.get_festival(db, membership.festival_id)
    categories = {
        c.id: c.name
        for e in festival.editions
        for c in festivals.categories_for_edition(db, e.id)
    }

    # Prev/next within this festival's submissions, newest first.
    subs = submissions.submissions_for_festival(db, membership.festival_id)
    ids = [s.id for s in subs]
    idx = ids.index(sub.id)
    prev_id = ids[idx - 1] if idx > 0 else None
    next_id = ids[idx + 1] if idx < len(ids) - 1 else None

    def actor_name(user_id):
        if user_id is None:
            return "system"
        actor = accounts.get_user(db, user_id)
        return actor.display_name if actor else "unknown"

    return {
        "submission": {
            "id": sub.id,
            "tracking_number": sub.tracking_number,
            "status": sub.status.value,
            "notified": sub.status != SubmissionStatus.RECEIVED,
            "category": categories.get(sub.category_id, ""),
            "fee_paid_cents": sub.fee_paid_cents,
            "discount_code": sub.discount_code,
            "cover_letter": sub.cover_letter,
            "contact": "access revoked" if sub.relay_revoked else sub.relay_contact_id,
            "created_at": sub.created_at.isoformat(),
            "flag_id": sub.flag_id,
        },
        "flags": [
            {"id": f.id, "name": f.name, "color": f.color}
            for f in festivals.list_flags(db, membership.festival_id)
        ],
        "custom_answers": _custom_answers(db, membership.festival_id, sub.id),
        "film": {
            "title": film.title,
            "kind": film.kind.value,
            "genre": film.genre,
            "runtime_minutes": film.runtime_minutes,
            "year": film.year,
            "country": film.country,
            "language": film.language,
            "logline": film.logline,
            "synopsis": film.synopsis,
            "credits": film.credits,
            "screener_url": film.screener_url,
            "trailer_url": film.trailer_url,
            "first_time_filmmaker": film.first_time_filmmaker,
            "student_project": film.student_project,
        },
        "filmmaker": {
            "display_name": filmmaker.display_name,
            "bio": filmmaker.bio,
        },
        "status_log": [
            {
                "actor": actor_name(c.actor_user_id),
                "from_status": c.from_status,
                "to_status": c.to_status,
                "created_at": c.created_at.isoformat(),
            }
            for c in submissions.status_log(db, sub.id)
        ],
        "notes": [
            {
                "id": n.id,
                "author": actor_name(n.author_user_id),
                "text": n.text,
                "created_at": n.created_at.isoformat(),
            }
            for n in jury.notes_for_submission(db, sub.id)
        ],
        "statuses": [s.value for s in SubmissionStatus],
        "can_update": membership.role in STATUS_ROLES,
        "can_rate": membership.role in RATING_ROLES,
        "prev_id": prev_id,
        "next_id": next_id,
        **_judging_payload(db, membership, sub, user),
    }


def _custom_answers(db, festival_id: int, submission_id: int) -> list[dict]:
    questions = {q.id: q.question for q in festivals.list_questions(db, festival_id)}
    return [
        {"question": questions.get(a.question_id, "(removed question)"), "answer": a.answer}
        for a in submissions.answers_for_submission(db, submission_id)
    ]


def _judging_payload(db, membership, sub, user) -> dict:
    """Judges, rubric, my scores, and the aggregate rating for one submission."""
    staff = accounts.festival_staff(db, membership.festival_id)
    names = {u.id: u.display_name for _, u in staff}
    assignments = jury.assignments_for_submission(db, sub.id)
    criteria = jury.criteria_for_festival(db, membership.festival_id)
    average, judge_count = jury.rating_summary(db, sub.id, criteria)
    my_assignment = next((a for a in assignments if a.juror_user_id == user.id), None)
    return {
        "judges": [
            {
                "user_id": a.juror_user_id,
                "name": names.get(a.juror_user_id, "former staff"),
                "status": a.status.value,
                "recommendation": a.recommendation.value if a.recommendation else None,
                "comment": a.comment,
            }
            for a in assignments
        ],
        "my_comment": my_assignment.comment if my_assignment else "",
        "my_recommendation": (
            my_assignment.recommendation.value
            if my_assignment and my_assignment.recommendation
            else None
        ),
        "staff": [
            {"user_id": u.id, "display_name": u.display_name, "role": m.role.value}
            for m, u in staff
        ],
        "rubric": [
            {"id": c.id, "name": c.name, "weight": c.weight} for c in criteria
        ],
        "my_scores": (
            jury.scores_for_assignment(db, my_assignment.id) if my_assignment else {}
        ),
        "rating": {"average": average, "judges": judge_count},
    }


@router.post("/submissions/{submission_id}/assign")
def assign_judge(db: DbDep, user: OrganizerDep, submission_id: int, body: AssignIn):
    membership = _membership(db, user)
    if membership.role not in STATUS_ROLES:
        raise HTTPException(403, "Your role can't assign judges.")
    _own_submission(db, membership, submission_id)
    staff_ids = {u.id for _, u in accounts.festival_staff(db, membership.festival_id)}
    if body.user_id not in staff_ids:
        raise HTTPException(400, "That person isn't on this festival's staff.")
    jury.assign(db, submission_id, body.user_id)
    return {"ok": True}


@router.post("/submissions/{submission_id}/unassign")
def unassign_judge(db: DbDep, user: OrganizerDep, submission_id: int, body: AssignIn):
    membership = _membership(db, user)
    if membership.role not in STATUS_ROLES:
        raise HTTPException(403, "Your role can't assign judges.")
    _own_submission(db, membership, submission_id)
    jury.unassign(db, submission_id, body.user_id)
    return {"ok": True}


@router.post("/submissions/{submission_id}/rate")
def rate_submission(db: DbDep, user: OrganizerDep, submission_id: int, body: RateIn):
    membership = _membership(db, user)
    if membership.role not in RATING_ROLES:
        raise HTTPException(403, "Your role can't rate submissions.")
    _own_submission(db, membership, submission_id)
    criteria = {
        c.id for c in jury.criteria_for_festival(db, membership.festival_id)
    }
    scores = {}
    for item in body.scores:
        if item.criterion_id not in criteria:
            raise HTTPException(400, "Unknown rubric criterion.")
        if not 1 <= item.score <= 10:
            raise HTTPException(400, "Scores are 1–10.")
        scores[item.criterion_id] = item.score
    if not scores:
        raise HTTPException(400, "No scores given.")
    # Rating implies an assignment; create one if the rater wasn't assigned.
    assignment = jury.assign(db, submission_id, user.id)
    jury.record_scores(
        db, assignment.id, scores,
        comment=body.comment, recommendation=body.recommendation,
    )
    return {"ok": True}


@router.post("/submissions/{submission_id}/flag")
def set_flag(db: DbDep, user: OrganizerDep, submission_id: int, body: SetFlagIn):
    membership = _membership(db, user)
    if membership.role not in STATUS_ROLES:
        raise HTTPException(403, "Your role can't set flags.")
    _own_submission(db, membership, submission_id)
    if body.flag_id is not None:
        flags = {f.id for f in festivals.list_flags(db, membership.festival_id)}
        if body.flag_id not in flags:
            raise HTTPException(400, "That flag doesn't exist.")
    submissions.set_flag(db, submission_id, body.flag_id)
    return {"ok": True}


@router.post("/submissions/{submission_id}/notes", status_code=201)
def add_note(db: DbDep, user: OrganizerDep, submission_id: int, body: NoteIn):
    """Internal jury note — never visible to the filmmaker (BRD §5.1.3)."""
    membership = _membership(db, user)
    _own_submission(db, membership, submission_id)
    if not body.text.strip():
        raise HTTPException(400, "Note can't be empty.")
    note = jury.add_internal_note(db, submission_id, user.id, body.text.strip())
    return {"note": {"id": note.id}}


@router.post("/submissions/{submission_id}/status")
def update_status(db: DbDep, user: OrganizerDep, submission_id: int, body: StatusIn):
    membership = _membership(db, user)
    if membership.role not in STATUS_ROLES:
        raise HTTPException(403, "Your role can't change judging status.")
    sub = _own_submission(db, membership, submission_id)
    submissions.update_status(db, submission_id, body.status, actor_user_id=user.id)

    film = accounts.get_film(db, sub.film_id)
    festival = festivals.get_festival(db, membership.festival_id)
    friendly = {
        SubmissionStatus.IN_REVIEW: "is now in review",
        SubmissionStatus.SHORTLISTED: "has been shortlisted",
        SubmissionStatus.FINALIST: "is a FINALIST",
        SubmissionStatus.SELECTED: "has been SELECTED 🎉",
        SubmissionStatus.AWARD_WINNER: "is an AWARD WINNER 🏆",
        SubmissionStatus.HONORABLE_MENTION: "received an honorable mention",
        SubmissionStatus.REJECTED: "was not selected this time",
        SubmissionStatus.RECEIVED: "was received",
    }[body.status]
    notifications.notify(
        db,
        user_id=film.filmmaker_id,
        kind=NotificationKind.STATUS_CHANGE,
        subject=f"“{film.title}” {friendly} at {festival.name}",
    )
    if body.status in SELECTED_STATUSES:
        certificates.issue_certificate(db, sub.id)
    db.commit()
    notifications.fire_event(
        db, membership.festival_id, "submission.status_changed",
        {
            "tracking_number": sub.tracking_number,
            "film_title": film.title,
            "status": body.status.value,
        },
    )
    return {"ok": True}


@router.post("/reviews/{review_id}/reply")
def reply_to_review(db: DbDep, user: OrganizerDep, review_id: int, body: ReplyIn):
    membership = _membership(db, user)
    review = next(
        (r for r in reviews.reviews_for_festival(db, membership.festival_id)
         if r.id == review_id),
        None,
    )
    if review is None:
        raise HTTPException(404, "Review not found")
    reviews.reply(db, review_id, body.reply_text)
    return {"ok": True}
