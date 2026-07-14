"""Judge calibration harness (Design.md §6).

Scores a small human-labeled sample with the live LLM-as-judge and measures
agreement with the human labels: exact accuracy, within-one, MAE, Cohen's κ, and
quadratic-weighted κ, plus a confusion matrix and per-item breakdown.

    uv run python scripts/calibrate_judge.py

Runs against whatever provider is active (add OPENAI_API_KEY to .env for a real
judge; on the FakeProvider every prediction is L3, which the metrics correctly
report as chance-level — a sanity check that the harness detects a bad judge).
Writes calibration/results.json and calibration/report.md. Tune the judge prompt
in app/llm/judge.py and re-run until κ is acceptable (target: substantial, ≥0.6).
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.competency.loader import get_competency_map  # noqa: E402
from app.eval.metrics import (  # noqa: E402
    accuracy,
    cohen_kappa,
    confusion_matrix,
    interpret_kappa,
    mae,
    quadratic_weighted_kappa,
    within_one,
)
from app.eval.metrics import LEVELS  # noqa: E402
from app.llm.judge import score_answer  # noqa: E402
from app.llm.router import get_router  # noqa: E402

_DATA = Path(__file__).resolve().parents[1] / "calibration" / "labeled_sample.json"
_OUT = Path(__file__).resolve().parents[1] / "calibration"
_CONCURRENCY = 5


async def _score(sem, cmap, sample):
    async with sem:
        comp = cmap.competency(sample["competency_id"])
        r = await score_answer(comp, comp.sample_question, sample["answer"])
        return {
            "competency_id": sample["competency_id"],
            "competency_name": comp.name,
            "label": int(sample["label"]),
            "pred": int(r["level"]),
            "confidence": r["confidence"],
            "evidence": r["evidence"],
        }


def _matrix_str(labels, preds) -> str:
    m = confusion_matrix(labels, preds, LEVELS)
    head = "        " + "  ".join(f"p{lv}" for lv in LEVELS)
    rows = [head]
    for i, lvl in enumerate(LEVELS):
        rows.append(f"  true{lvl}  " + "  ".join(f"{m[i][j]:2d}" for j in range(len(LEVELS))))
    return "\n".join(rows)


async def main() -> int:
    cmap = get_competency_map()
    data = json.loads(_DATA.read_text(encoding="utf-8"))
    samples = data["samples"]
    provider = get_router().for_task("score").name

    print(f"Calibrating judge · provider={provider} · n={len(samples)}\n")
    if provider == "fake":
        print("  ! FakeProvider active — predictions will be constant (L3). Add\n"
              "    OPENAI_API_KEY to .env for a real calibration.\n")

    sem = asyncio.Semaphore(_CONCURRENCY)
    rows = await asyncio.gather(*(_score(sem, cmap, s) for s in samples))

    labels = [r["label"] for r in rows]
    preds = [r["pred"] for r in rows]

    metrics = {
        "n": len(rows),
        "provider": provider,
        "accuracy": round(accuracy(labels, preds), 3),
        "within_one": round(within_one(labels, preds), 3),
        "mae": round(mae(labels, preds), 3),
        "cohen_kappa": round(cohen_kappa(labels, preds), 3),
        "quadratic_weighted_kappa": round(quadratic_weighted_kappa(labels, preds), 3),
    }

    print(f"  exact accuracy      {metrics['accuracy']:.3f}")
    print(f"  within one level    {metrics['within_one']:.3f}")
    print(f"  mean abs error      {metrics['mae']:.3f}")
    print(f"  Cohen's kappa       {metrics['cohen_kappa']:.3f}  ({interpret_kappa(metrics['cohen_kappa'])})")
    print(f"  weighted kappa      {metrics['quadratic_weighted_kappa']:.3f}  ({interpret_kappa(metrics['quadratic_weighted_kappa'])})")
    print("\nConfusion (rows = human label, cols = judge):")
    print(_matrix_str(labels, preds))

    print("\nDisagreements (|Δ| ≥ 1):")
    for r in sorted(rows, key=lambda x: -abs(x["label"] - x["pred"])):
        d = abs(r["label"] - r["pred"])
        if d == 0:
            continue
        print(f"  L{r['label']}→L{r['pred']} (Δ{d}) {r['competency_id']}: {r['evidence'][:90]}")

    # Artifacts
    _OUT.mkdir(exist_ok=True)
    (_OUT / "results.json").write_text(
        json.dumps({"metrics": metrics, "items": rows}, indent=2), encoding="utf-8"
    )
    _write_report_md(metrics, rows, labels, preds)
    print(f"\nWrote {(_OUT / 'results.json').relative_to(_OUT.parents[1])} and calibration/report.md")

    k = metrics["cohen_kappa"]
    return 0 if provider == "fake" or k >= 0.4 else 1


def _write_report_md(metrics, rows, labels, preds):
    lines = [
        "# Judge calibration report",
        "",
        f"- Provider: **{metrics['provider']}** · sample size: **{metrics['n']}**",
        f"- Exact accuracy: **{metrics['accuracy']}**",
        f"- Within one level: **{metrics['within_one']}**",
        f"- Mean absolute error: **{metrics['mae']}**",
        f"- Cohen's κ: **{metrics['cohen_kappa']}** ({interpret_kappa(metrics['cohen_kappa'])})",
        f"- Quadratic-weighted κ: **{metrics['quadratic_weighted_kappa']}** "
        f"({interpret_kappa(metrics['quadratic_weighted_kappa'])})",
        "",
        "## Confusion matrix (rows = human, cols = judge)",
        "",
        "```",
        _matrix_str(labels, preds),
        "```",
        "",
        "## Per-item",
        "",
        "| competency | human | judge | Δ |",
        "| --- | --- | --- | --- |",
    ]
    for r in rows:
        d = abs(r["label"] - r["pred"])
        mark = "" if d == 0 else f" ⚠️{d}"
        lines.append(f"| {r['competency_id']} | L{r['label']} | L{r['pred']} |{mark or ' 0'} |")
    (_OUT / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
