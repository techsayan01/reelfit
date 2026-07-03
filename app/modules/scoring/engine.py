"""Fit-scoring engine (Phase 1 heuristic baseline).

Scores a film against a festival's historical selection pattern. This is the
statistical baseline the ML model (scikit-learn/PyTorch) will replace once
partner-festival data volume justifies it; the public interface — score,
confidence, calibration status — stays identical (BRD §7.2).

The score reads as neutral information, never pass/fail: it estimates how
closely the film matches what this festival has actually selected before.
"""

from dataclasses import dataclass

from app.modules.festivals.models import CalibrationStatus, HistoricalSelection

# Below this many historical records a festival stays "calibrating" and
# confidence is capped accordingly (BRD §5.1.3 calibration transparency).
MIN_RECORDS_FOR_VALIDATION = 30


@dataclass(frozen=True)
class FilmProfile:
    genre: str
    runtime_minutes: int
    year: int
    country: str = ""


@dataclass(frozen=True)
class FitResult:
    score: int  # 0-100
    confidence: float  # 0.0-1.0
    calibration_status: CalibrationStatus
    explanation: list[str]


def compute_fit(film: FilmProfile, history: list[HistoricalSelection]) -> FitResult:
    if not history:
        return FitResult(
            score=50,
            confidence=0.1,
            calibration_status=CalibrationStatus.CALIBRATING,
            explanation=[
                "This festival has no confirmed selection history on Reelfit yet, "
                "so this score is an early-access estimate only."
            ],
        )

    selected = [h for h in history if h.selected]
    explanation: list[str] = []

    # Genre affinity: share of selected films in this genre vs. its share of
    # all submissions — measures whether the festival favors this genre.
    genre = film.genre.strip().lower()
    genre_selected = sum(1 for h in selected if h.genre.lower() == genre)
    genre_total = sum(1 for h in history if h.genre.lower() == genre)
    if genre_total == 0:
        genre_component = 0.35  # unseen genre: mild uncertainty, not a penalty
        explanation.append(
            f"This festival hasn't received {film.genre} films before — "
            "genre fit is uncertain."
        )
    else:
        genre_rate = genre_selected / genre_total
        overall_rate = len(selected) / len(history)
        # Normalize against the festival's own base acceptance rate.
        ratio = genre_rate / overall_rate if overall_rate > 0 else 0.0
        genre_component = max(0.0, min(1.0, 0.5 * ratio))
        if ratio >= 1.2:
            explanation.append(
                f"{film.genre.title()} films are selected here more often than average."
            )
        elif ratio <= 0.6:
            explanation.append(
                f"{film.genre.title()} films are selected here less often than average."
            )

    # Runtime fit: distance from the median runtime of selected films.
    if selected:
        runtimes = sorted(h.runtime_minutes for h in selected)
        median_rt = runtimes[len(runtimes) // 2]
        distance = abs(film.runtime_minutes - median_rt)
        runtime_component = max(0.0, 1.0 - distance / max(median_rt, 30))
        if runtime_component >= 0.8:
            explanation.append(
                f"Your runtime ({film.runtime_minutes} min) is close to what "
                f"this festival typically selects (~{median_rt} min)."
            )
        elif runtime_component <= 0.4:
            explanation.append(
                f"Your runtime ({film.runtime_minutes} min) is far from this "
                f"festival's typical selection (~{median_rt} min)."
            )
    else:
        runtime_component = 0.5

    # Recency: festivals drift in taste; recent selections in this genre count more.
    recent_years = {h.year for h in selected if h.genre.lower() == genre}
    recency_component = 1.0 if recent_years and max(recent_years) >= film.year - 3 else 0.5

    raw = 0.55 * genre_component + 0.30 * runtime_component + 0.15 * recency_component
    score = round(raw * 100)

    n = len(history)
    confidence = min(0.95, n / (MIN_RECORDS_FOR_VALIDATION * 2))
    status = (
        CalibrationStatus.VALIDATED
        if n >= MIN_RECORDS_FOR_VALIDATION
        else CalibrationStatus.CALIBRATING
    )
    if status == CalibrationStatus.CALIBRATING:
        explanation.append(
            "This festival's scoring is still calibrating — treat the number "
            "as a directional guide, not a verdict."
        )

    return FitResult(
        score=score, confidence=round(confidence, 2), calibration_status=status,
        explanation=explanation,
    )
