"""Integrity checks for the exercise bank — guards future expansions.

These are static (no LLM/network): every exercise must map to a real
competency, every check regex must compile, and the shapes must be sane.
"""

import re

from app.competency.loader import get_competency_map
from app.eval.exercises import get_exercise_bank


def test_every_exercise_maps_to_a_real_competency():
    valid = {c.id for c in get_competency_map().all_competencies()}
    orphans = [e.competency_id for e in get_exercise_bank().exercises if e.competency_id not in valid]
    assert not orphans, f"exercises reference unknown competencies: {orphans}"


def test_no_duplicate_competencies_in_bank():
    ids = get_exercise_bank().competency_ids
    assert len(ids) == len(set(ids)), "duplicate competency in the exercise bank"


def test_every_check_regex_compiles():
    bad = []
    for e in get_exercise_bank().exercises:
        for c in e.checks:
            try:
                re.compile(c.pattern)
            except re.error as err:
                bad.append((e.competency_id, c.id, str(err)))
    assert not bad, f"non-compiling check patterns: {bad}"


def test_exercises_are_well_formed():
    for e in get_exercise_bank().exercises:
        assert e.title and e.prompt and e.rubric, f"{e.competency_id} missing text"
        assert e.checks, f"{e.competency_id} has no checks"
        for c in e.checks:
            assert c.kind in ("present", "absent"), f"{e.competency_id}/{c.id} bad kind {c.kind!r}"
            assert c.weight >= 1
