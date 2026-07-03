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
