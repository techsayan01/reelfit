"""Dashboards service: aggregates for festival- and filmmaker-side views.

Reads only through other modules' service layers / model rows returned by
them — no cross-module SQL joins, keeping the monolith decomposable.
"""

from collections import Counter
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.modules.submissions import service as submissions
from app.modules.submissions.models import SubmissionStatus


@dataclass(frozen=True)
class FestivalOverview:
    total_submissions: int
    by_status: dict[str, int]
    gross_revenue_cents: int
    discounted_count: int


def festival_overview(db: Session, festival_id: int) -> FestivalOverview:
    subs = submissions.submissions_for_festival(db, festival_id)
    by_status = Counter(s.status.value for s in subs)
    return FestivalOverview(
        total_submissions=len(subs),
        by_status=dict(by_status),
        gross_revenue_cents=sum(s.fee_paid_cents for s in subs),
        discounted_count=sum(1 for s in subs if s.discount_code),
    )


@dataclass(frozen=True)
class FilmmakerOverview:
    total_submissions: int
    by_status: dict[str, int]
    total_fees_cents: int


def filmmaker_overview(db: Session, film_ids: list[int]) -> FilmmakerOverview:
    subs = submissions.submissions_for_films(db, film_ids)
    by_status = Counter(s.status.value for s in subs)
    return FilmmakerOverview(
        total_submissions=len(subs),
        by_status=dict(by_status),
        total_fees_cents=sum(s.fee_paid_cents for s in subs),
    )


SELECTED = SubmissionStatus.SELECTED
