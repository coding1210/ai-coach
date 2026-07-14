"""Adaptive assessment logic: which competency to probe next, and how much of
the important surface we've covered (Design.md §5).

Principle: rank by domain weight (Critical first), skip what's already scored,
prefer high-weight / low-coverage. Coverage is measured over Critical + High
competencies so short sessions still cover what matters most.
"""

from __future__ import annotations

from app.competency.loader import CompetencyMap, Competency

# Domains that count toward the stop-condition coverage metric.
_COVERAGE_WEIGHTS = {"critical", "high"}


def next_competency(cmap: CompetencyMap, asked: list[str]) -> Competency | None:
    """Highest-weight competency not yet asked. None when everything is covered."""
    asked_set = set(asked)
    candidates = [
        c for c in cmap.all_competencies() if c.id not in asked_set
    ]
    if not candidates:
        return None
    # Sort by descending domain weight; ties keep map order (already Critical-first).
    candidates.sort(key=lambda c: cmap.weight_of(c.id), reverse=True)
    return candidates[0]


def weighted_coverage(cmap: CompetencyMap, asked: list[str]) -> float:
    """Fraction of Critical+High competency weight that has been probed (0..1)."""
    asked_set = set(asked)
    total = 0.0
    covered = 0.0
    for d in cmap.domains:
        if d.weight not in _COVERAGE_WEIGHTS:
            continue
        w = cmap.weight_scale[d.weight]
        for c in d.competencies:
            total += w
            if c.id in asked_set:
                covered += w
    return covered / total if total else 0.0


def reassess_targets(cmap: CompetencyMap, prior_levels: dict[str, int]) -> list[str]:
    """Competencies a returning user was previously below target on, ordered by
    gap × weight (highest leverage first). This is the re-assessment worklist:
    re-probe exactly the areas worth checking for growth, not the whole map."""
    scored: list[tuple[str, int]] = []
    for cid, level in prior_levels.items():
        try:
            weight = cmap.domain_of(cid).weight
        except KeyError:
            continue
        gap = target_level_for(weight) - level
        if gap > 0:
            scored.append((cid, gap * cmap.weight_scale[weight]))
    scored.sort(key=lambda x: x[1], reverse=True)
    return [cid for cid, _ in scored]


def target_level_for(weight: str) -> int:
    """Derive a target proficiency from domain weight (Syllabus.md §1).

    A "senior Gen AI role" implies mostly L4 on what matters, less on the fringe.
    Kept simple and weight-driven for v1; can later be personalized from the goal.
    """
    return {
        "critical": 4,
        "high": 4,
        "medium-high": 3,
        "medium": 3,
        "low-medium": 2,
    }.get(weight, 3)
