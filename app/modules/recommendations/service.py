"""Recommendations: festival ranking and distribution guidance.

Distribution guidance is informational only — Reelfit recommends paths, it
never acts as an aggregator, sales agent, or rights holder (BRD §3.2).
Rankings are computed on demand from stored fit scores rather than
persisted; the Recommendation entity becomes a table if/when we need to
show users a frozen historical snapshot.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class DistributionSuggestion:
    path: str  # "aggregator" | "tvod" | "avod_fast" | "self_distribution"
    title: str
    rationale: str


@dataclass(frozen=True)
class FestivalMatch:
    festival_id: int
    score: int
    reason: str
    tier: str  # "strong" | "solid" | "stretch" | "longshot" | "unavailable"
    closing_soon: bool
    submittable: bool


# Deadline within this many days is flagged "closing soon" on a recommendation.
CLOSING_SOON_DAYS = 14


def rank_festivals(candidates: list[dict]) -> list[FestivalMatch]:
    """Turn a film's raw per-festival fit scores into a ranked, plain-language
    recommendation list — the "where should I spend my submission fee" view
    (BRD §7.4 festival ranking).

    Each candidate dict describes one scored festival:
        festival_id:   int
        score:         int   (0-100 fit score)
        open:          bool  (currently accepting submissions)
        eligible:      bool  (has a category this film can enter)
        days_to_deadline: int | None

    Fit score is the primary signal, but a festival you can't actually submit
    to right now is demoted below every submittable one, no matter how strong
    the match — a great score you can't act on isn't a useful recommendation.
    """
    matches: list[FestivalMatch] = []
    for c in candidates:
        submittable = bool(c["open"]) and bool(c["eligible"])
        days = c.get("days_to_deadline")
        closing_soon = (
            submittable and days is not None and 0 <= days <= CLOSING_SOON_DAYS
        )
        score = c["score"]

        if not submittable:
            if not c["open"]:
                reason = "Not open for submissions right now — check back for the next edition."
            else:
                reason = "No category matches this film at the moment."
            tier = "unavailable"
        elif score >= 75:
            reason = "Strong match — your film looks a lot like what they select."
            tier = "strong"
        elif score >= 55:
            reason = "Solid match — a fee here looks well spent."
            tier = "solid"
        elif score >= 40:
            reason = "A stretch, but within range — worth it if the festival matters to you."
            tier = "stretch"
        else:
            reason = "Long shot — your fee is likely better spent elsewhere."
            tier = "longshot"

        if closing_soon:
            reason += (
                " Deadline is today." if days == 0
                else f" Deadline in {days} day{'s' if days != 1 else ''}."
            )

        matches.append(FestivalMatch(
            festival_id=c["festival_id"], score=score, reason=reason,
            tier=tier, closing_soon=closing_soon, submittable=submittable,
        ))

    # Submittable first; then by fit score; then soonest-closing as a nudge.
    matches.sort(
        key=lambda m: (m.submittable, m.score, m.closing_soon),
        reverse=True,
    )
    return matches


def distribution_guidance(genre: str, runtime_minutes: int, festival_selections: int) -> list[DistributionSuggestion]:
    """Realistic next-step suggestions based on the film's profile.

    Phase 1 uses transparent rules; the point is honest, plain-language
    guidance, not algorithmic mystique.
    """
    genre = genre.strip().lower()
    is_short = runtime_minutes < 40
    suggestions: list[DistributionSuggestion] = []

    if is_short:
        suggestions.append(DistributionSuggestion(
            path="avod_fast",
            title="Free streaming channels (AVOD/FAST)",
            rationale="Short films rarely sell individually; free ad-supported "
                      "channels and curated short-film platforms reach the "
                      "widest audience and build your credit list.",
        ))
        suggestions.append(DistributionSuggestion(
            path="self_distribution",
            title="Self-distribution (YouTube/Vimeo after your festival run)",
            rationale="Once your festival window closes, releasing the short "
                      "yourself keeps full control and costs nothing.",
        ))
    else:
        if festival_selections >= 2:
            suggestions.append(DistributionSuggestion(
                path="aggregator",
                title="Aggregator to major platforms",
                rationale="With multiple festival selections, an aggregator can "
                          "place the film on major rental/subscription platforms. "
                          "Expect an upfront fee — read the terms on revenue share.",
            ))
        suggestions.append(DistributionSuggestion(
            path="tvod",
            title="Rental/purchase platforms (TVOD)",
            rationale="Features with a defined audience can earn direct rental "
                      "revenue; works best with an existing following or a "
                      "festival-run press kit.",
        ))
        if genre in ("documentary", "docs", "doc"):
            suggestions.append(DistributionSuggestion(
                path="avod_fast",
                title="Documentary-focused streaming channels",
                rationale="Documentary catalogs on free streaming channels have "
                          "steady demand; niche topics often out-perform there.",
            ))
        if not suggestions or festival_selections == 0:
            suggestions.append(DistributionSuggestion(
                path="self_distribution",
                title="Self-distribution",
                rationale="Without festival selections yet, building an audience "
                          "directly keeps your options open and costs the least.",
            ))
    return suggestions
