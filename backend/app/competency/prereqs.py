"""Prerequisite edges between competencies (see prereqs.json)."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

_PREREQ_LEVEL = 2  # a prereq counts as met once demonstrated at ≥ this level


@lru_cache
def _prereqs() -> dict[str, list[str]]:
    p = Path(__file__).resolve().parent / "prereqs.json"
    try:
        return json.loads(p.read_text(encoding="utf-8")).get("prereqs", {})
    except Exception:  # noqa: BLE001
        return {}


def prereqs_for(competency_id: str) -> list[str]:
    return list(_prereqs().get(competency_id, []))


def prereqs_met(competency_id: str, mastery_levels: dict[str, int]) -> bool:
    """True if every prerequisite is demonstrated at ≥ the prereq level (or none)."""
    return all(
        mastery_levels.get(pid, 0) >= _PREREQ_LEVEL for pid in prereqs_for(competency_id)
    )
