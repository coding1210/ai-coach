"""Exercise bank — concrete graded tasks per competency (behavioral assessment).

Each exercise carries a prompt, a grading rubric for the code-judge, and a set of
objective `checks` (regexes over the submission) that give a deterministic,
keyless signal of whether the code actually exhibits the target properties.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel


class Check(BaseModel):
    id: str
    description: str
    kind: str  # "present" (regex must match) | "absent" (regex must not match)
    pattern: str
    weight: int = 1


class Exercise(BaseModel):
    competency_id: str
    title: str
    language: str
    prompt: str
    rubric: str
    checks: list[Check]
    # Optional hidden test harness (Python). Appended after the submission and
    # run in the sandbox; must print SANDBOX_PASS on success. Withheld from the
    # client (ExerciseOut) so it can't be gamed.
    tests: str | None = None


class ExerciseBank(BaseModel):
    description: str
    exercises: list[Exercise]

    def by_competency(self, competency_id: str) -> Exercise | None:
        return next((e for e in self.exercises if e.competency_id == competency_id), None)

    @property
    def competency_ids(self) -> list[str]:
        return [e.competency_id for e in self.exercises]


def load_exercise_bank(path: Path | None = None) -> ExerciseBank:
    p = path or (Path(__file__).resolve().parents[2] / "exercises" / "exercises.json")
    data = json.loads(Path(p).read_text(encoding="utf-8"))
    return ExerciseBank.model_validate(data)


@lru_cache
def get_exercise_bank() -> ExerciseBank:
    return load_exercise_bank()
