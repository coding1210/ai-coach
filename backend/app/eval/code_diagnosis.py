"""Diagnose a Gen AI engineer from their REAL code, not a self-report.

Point the behavioral grader at an actual project — pasted files or a public
GitHub repo — and, for every competency that has an exercise, ask: does this
codebase actually exhibit the target properties (async, retries, structured
output, retrieval eval, injection defense…)? Each competency is graded against
its rubric with the real code as the submission, so evidence cites what the
code does. The result is the same report + roadmap the conversational path
produces — but grounded in artifacts. This is the honest answer to "why not
just use ChatGPT".
"""

from __future__ import annotations

import asyncio
import logging

import httpx

from app.coaching.benchmark import benchmark_report
from app.coaching.roadmap import build_roadmap, enrich_roadmap
from app.competency.loader import get_competency_map
from app.eval.exercises import get_exercise_bank
from app.graph.nodes.report import build_report
from app.llm.grader import grade_submission

log = logging.getLogger(__name__)

_MAX_FILES = 40
_MAX_TOTAL = 120_000  # chars of code fed to the judges


def _clip(code: str) -> str:
    return code[:_MAX_TOTAL]


async def fetch_github(url: str) -> str:
    """Best-effort fetch of a public GitHub repo's Python files, concatenated.
    Raises ValueError on anything unusable."""
    parts = url.rstrip("/").replace("https://github.com/", "").split("/")
    if len(parts) < 2:
        raise ValueError("Not a GitHub repo URL.")
    owner, repo = parts[0], parts[1]
    async with httpx.AsyncClient(timeout=20, headers={"Accept": "application/vnd.github+json"}) as c:
        info = await c.get(f"https://api.github.com/repos/{owner}/{repo}")
        if info.status_code != 200:
            raise ValueError("Repo not found or not public.")
        branch = info.json().get("default_branch", "main")
        tree = await c.get(
            f"https://api.github.com/repos/{owner}/{repo}/git/trees/{branch}?recursive=1"
        )
        if tree.status_code != 200:
            raise ValueError("Could not read the repo tree.")
        files = [
            n["path"]
            for n in tree.json().get("tree", [])
            if n.get("type") == "blob" and n["path"].endswith(".py")
        ][:_MAX_FILES]
        if not files:
            raise ValueError("No Python files found in that repo.")

        blobs: list[str] = []
        total = 0
        for path in files:
            raw = await c.get(
                f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{path}"
            )
            if raw.status_code != 200:
                continue
            text = raw.text
            blobs.append(f"# ===== {path} =====\n{text}")
            total += len(text)
            if total >= _MAX_TOTAL:
                break
        if not blobs:
            raise ValueError("Could not fetch any file contents.")
    return _clip("\n\n".join(blobs))


async def diagnose_code(
    code: str, profile: dict | None = None, jd_targets: dict | None = None, role_title: str = ""
) -> dict:
    """Grade real code against every competency with an exercise, then build the
    same evaluation report + coaching roadmap."""
    code = _clip(code or "")
    cmap = get_competency_map()
    bank = get_exercise_bank()

    async def _grade(ex):
        try:
            r = await grade_submission(ex, code)
            return ex.competency_id, r
        except Exception as e:  # noqa: BLE001 — one bad grade shouldn't sink the diagnosis
            log.warning("code diagnosis: grading %s failed: %s", ex.competency_id, e)
            return ex.competency_id, None

    graded = await asyncio.gather(*[_grade(ex) for ex in bank.exercises])
    scores = {
        cid: {
            "competency_id": cid,
            "level": r["level"],
            "evidence": r["evidence"],
            "confidence": r["confidence"],
        }
        for cid, r in graded
        if r is not None
    }

    built = build_report(scores, cmap, jd_targets=jd_targets or {})
    built["role_title"] = role_title
    built["source"] = "code"
    built["benchmark"] = benchmark_report(built["radar"])
    early = bool(built.get("early_stage"))
    built["roadmap"] = build_roadmap(built, cmap, beginner=early)
    await enrich_roadmap(built["roadmap"], profile or {}, role_title, beginner=early)
    return built
