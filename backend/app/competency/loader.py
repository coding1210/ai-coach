"""Load and validate competency_map.json into typed models.

The map is the coach's internal *diagnostic rubric* (COACHING, not teaching):
the assess/score nodes read it to pick questions and ground the LLM-judge. It is
never delivered to the user as a curriculum.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel

from app.config import get_settings


class ProficiencyLevel(BaseModel):
    level: int
    name: str
    meaning: str


class Competency(BaseModel):
    id: str
    name: str
    sample_question: str
    level_anchors: dict[str, str]  # e.g. {"2": "...", "4": "..."}


class Domain(BaseModel):
    id: str
    name: str
    weight: str  # critical | high | medium-high | medium | low-medium
    competencies: list[Competency]


class ScoringConfig(BaseModel):
    method: str
    output_schema: dict[str, str]
    bias_controls: list[str]
    calibration: str


class AssessmentConfig(BaseModel):
    order: list[str]
    coverage_threshold: float
    notes: str


class CompetencyMap(BaseModel):
    version: str
    updated: str
    purpose: str
    proficiency_levels: list[ProficiencyLevel]
    weight_scale: dict[str, int]
    assessment: AssessmentConfig
    scoring: ScoringConfig
    domains: list[Domain]

    # ── convenience accessors ────────────────────────────────────
    def all_competencies(self) -> list[Competency]:
        return [c for d in self.domains for c in d.competencies]

    def domain_of(self, competency_id: str) -> Domain:
        for d in self.domains:
            if any(c.id == competency_id for c in d.competencies):
                return d
        raise KeyError(f"Unknown competency_id: {competency_id}")

    def competency(self, competency_id: str) -> Competency:
        for c in self.all_competencies():
            if c.id == competency_id:
                return c
        raise KeyError(f"Unknown competency_id: {competency_id}")

    def weight_of(self, competency_id: str) -> int:
        return self.weight_scale[self.domain_of(competency_id).weight]


def load_competency_map(path: Path | None = None) -> CompetencyMap:
    settings = get_settings()
    p = Path(path or settings.competency_map_path)
    if not p.is_absolute():
        # Resolve relative to the backend/ package root, not the CWD.
        p = (Path(__file__).resolve().parents[2] / p).resolve()
    data = json.loads(p.read_text(encoding="utf-8"))
    return CompetencyMap.model_validate(data)


@lru_cache
def get_competency_map() -> CompetencyMap:
    return load_competency_map()
