"""Role presets — a community-editable-style map of what different Gen AI roles
demand, expressed as per-domain target levels.

These override the generic domain weights so "current vs target" is measured
against the bar for the role the user is actually aiming at, without needing a
pasted JD. The competency map itself (competency_map.json) is the editable
source of truth for the competencies; this is the role → target overlay.
Targets are keyed by domain_id (same shape as JD-derived `jd_targets`).
"""

from __future__ import annotations

ROLE_PRESETS: dict[str, dict] = {
    "rag_engineer": {
        "label": "RAG Engineer",
        "description": "Builds retrieval-augmented systems: retrieval quality, eval, and serving.",
        "targets": {"rag": 5, "evaluation": 4, "llm_fundamentals": 4, "production": 4, "context_prompt": 4},
    },
    "agent_engineer": {
        "label": "Agent Engineer",
        "description": "Builds tool-using agents: orchestration, reliability, and evaluation.",
        "targets": {"agents": 5, "evaluation": 4, "production": 4, "llm_fundamentals": 4, "safety": 4},
    },
    "llmops_engineer": {
        "label": "LLMOps Engineer",
        "description": "Ships and operates LLM systems: serving, observability, cost, and CI/CD.",
        "targets": {"production": 5, "observability": 5, "evaluation": 4, "python": 4, "safety": 4},
    },
    "generalist": {
        "label": "Gen AI Generalist",
        "description": "Broad senior competence across the whole Gen AI stack.",
        "targets": {"rag": 4, "agents": 4, "evaluation": 4, "llm_fundamentals": 4, "production": 4},
    },
}


def targets_for_role(role_key: str | None) -> dict[str, int]:
    """Per-domain target overrides for a role preset, or {} if unknown/None."""
    preset = ROLE_PRESETS.get(role_key or "")
    return dict(preset["targets"]) if preset else {}


def role_label(role_key: str | None) -> str:
    preset = ROLE_PRESETS.get(role_key or "")
    return preset["label"] if preset else ""


def list_roles() -> list[dict]:
    return [
        {"key": k, "label": v["label"], "description": v["description"]}
        for k, v in ROLE_PRESETS.items()
    ]
