"""Scoring service: the public interface other modules use for fit scores.

One flat fee per film evaluated, not per festival compared (BRD §5.2.2):
score_film_everywhere charges a single credit and scores against every
listed festival.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.festivals.models import Festival, HistoricalSelection
from app.modules.scoring.engine import FilmProfile, FitResult, compute_fit
from app.modules.scoring.models import FitScore


def _history(db: Session, festival_id: int) -> list[HistoricalSelection]:
    return list(
        db.scalars(
            select(HistoricalSelection).where(HistoricalSelection.festival_id == festival_id)
        )
    )


def score_film_against_festival(
    db: Session, film_id: int, festival_id: int, profile: FilmProfile
) -> tuple[FitScore, FitResult]:
    result = compute_fit(profile, _history(db, festival_id))
    record = FitScore(
        film_id=film_id,
        festival_id=festival_id,
        score=result.score,
        confidence=result.confidence,
        calibration_status=result.calibration_status.value,
    )
    db.add(record)
    db.commit()
    return record, result


def score_film_everywhere(
    db: Session, film_id: int, profile: FilmProfile
) -> list[tuple[Festival, FitScore, FitResult]]:
    """Score one film against all publicly listed festivals. Caller is
    responsible for charging exactly one scoring credit for the whole run."""
    festivals = list(db.scalars(select(Festival).where(Festival.is_public.is_(True))))
    out = []
    for festival in festivals:
        record, result = score_film_against_festival(db, film_id, festival.id, profile)
        out.append((festival, record, result))
    out.sort(key=lambda item: item[1].score, reverse=True)
    return out


def latest_scores_for_film(db: Session, film_id: int) -> list[FitScore]:
    """Most recent score per festival for a film."""
    rows = db.scalars(
        select(FitScore).where(FitScore.film_id == film_id).order_by(FitScore.created_at.desc())
    )
    seen: set[int] = set()
    latest = []
    for row in rows:
        if row.festival_id not in seen:
            seen.add(row.festival_id)
            latest.append(row)
    latest.sort(key=lambda s: s.score, reverse=True)
    return latest


def outcome_tracking(db: Session, film_ids: list[int]) -> list[FitScore]:
    """All scores for a filmmaker's films — used for score-vs-outcome history
    (BRD §5.2.3)."""
    if not film_ids:
        return []
    return list(
        db.scalars(
            select(FitScore)
            .where(FitScore.film_id.in_(film_ids))
            .order_by(FitScore.created_at.desc())
        )
    )
