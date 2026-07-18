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


def next_competency(
    cmap: CompetencyMap, asked: list[str], scores: dict | None = None
) -> Competency | None:
    """Next competency to probe, None when everything is covered.

    Breadth-first across domains (pick the least-probed domain, weight as
    tie-break) so the first few questions span domains and the radar fills fast.
    Once answers come in it becomes confidence-driven: a domain that scored below
    target or with low confidence gets a "dig" bonus, so the coach revisits weak
    or uncertain areas sooner instead of marching on — closing the loop.
    """
    asked_set = set(asked)
    scores = scores or {}

    def dig_bonus(domain) -> int:
        target = target_level_for(domain.weight)
        for c in domain.competencies:
            s = scores.get(c.id)
            if s and (s["level"] < target or s.get("confidence", 1.0) < 0.6):
                return 1  # weak/uncertain here — worth going deeper
        return 0

    best: tuple[int, int, int] | None = None
    choice: Competency | None = None
    for order, domain in enumerate(cmap.domains):
        unasked = [c for c in domain.competencies if c.id not in asked_set]
        if not unasked:
            continue
        probed = len(domain.competencies) - len(unasked)
        # least "effective probed" first (dig bonus pulls weak domains up),
        # then higher weight, then map order.
        key = (probed - dig_bonus(domain), -cmap.weight_scale[domain.weight], order)
        if best is None or key < best:
            best = key
            choice = unasked[0]
    return choice


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


def target_for(cmap: CompetencyMap, competency_id: str, jd_targets: dict | None = None) -> int:
    """Target level for a competency: from the job description if provided (per its
    domain), otherwise the generic weight-derived target."""
    domain = cmap.domain_of(competency_id)
    if jd_targets:
        lvl = jd_targets.get(domain.id)
        if lvl:  # 0/None = not emphasized by the role → fall back
            return max(1, min(5, int(lvl)))
    return target_level_for(domain.weight)


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
