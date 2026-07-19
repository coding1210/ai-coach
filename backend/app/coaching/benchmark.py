"""Anonymized benchmarking — where the user stands vs a typical Gen AI engineer.

We compare each domain's current level against a reference distribution (a prior
for what practising Gen AI engineers typically reach, by domain weight). It's a
seeded prior, not a live cohort — honest for a prototype and refined as real
population data accrues (see `refine_with_population`). No personal data leaves.
"""

from __future__ import annotations

import math

# Reference mean level by domain weight — heavier domains are where the field
# concentrates skill, so the typical bar sits a little higher.
_REF_BY_WEIGHT = {
    "critical": 3.2,
    "high": 3.0,
    "medium-high": 2.8,
    "medium": 2.7,
    "low-medium": 2.3,
}
_REF_SD = 0.9  # spread of the reference population


def _percentile(value: float, mean: float, sd: float) -> int:
    """Normal-CDF percentile of `value` in N(mean, sd), as an int 0–100."""
    if sd <= 0:
        return 50
    z = (value - mean) / sd
    cdf = 0.5 * (1 + math.erf(z / math.sqrt(2)))
    return int(round(max(0.0, min(1.0, cdf)) * 100))


def _standing(pct: int) -> str:
    if pct >= 66:
        return "ahead of most"
    if pct >= 40:
        return "about typical"
    return "behind most"


def benchmark_report(radar: list[dict], population: dict[str, dict] | None = None) -> list[dict]:
    """Given the report's per-domain radar, return a per-domain benchmark.

    `population` (optional) overrides the prior with real aggregates:
    {domain_id: {"mean": float, "sd": float}}.
    """
    out: list[dict] = []
    for d in radar:
        weight = d.get("weight", "medium")
        ref = (population or {}).get(d["domain_id"])
        mean = ref["mean"] if ref else _REF_BY_WEIGHT.get(weight, 2.7)
        sd = ref["sd"] if ref else _REF_SD
        pct = _percentile(d["current"], mean, sd)
        out.append(
            {
                "domain_id": d["domain_id"],
                "domain_name": d["domain_name"],
                "you": d["current"],
                "typical": round(mean, 1),
                "percentile": pct,
                "standing": _standing(pct),
            }
        )
    out.sort(key=lambda x: x["percentile"], reverse=True)
    return out


def refine_with_population(levels_by_domain: dict[str, list[float]]) -> dict[str, dict]:
    """Build a {domain_id: {mean, sd}} override from real aggregated levels.

    Hook for when there's enough anonymized data to beat the seeded prior.
    """
    stats: dict[str, dict] = {}
    for did, levels in levels_by_domain.items():
        if not levels:
            continue
        mean = sum(levels) / len(levels)
        var = sum((x - mean) ** 2 for x in levels) / len(levels)
        stats[did] = {"mean": mean, "sd": max(0.4, math.sqrt(var))}
    return stats
