"""Assemble and compile the leveled coaching state graph.

    onboard → (ask → await_answer → score)×3 per level → level_review
            → [weak spots? coach_offer → consent_await → coach_light]
            → mastery gate → next_level (loop) or report → persist

`await_answer` and `consent_await` pause via interrupt() to collect user input,
so the compiled graph REQUIRES a checkpointer (supplied by the caller).
"""

from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from app.graph import nodes
from app.graph.edges import (
    route_after_coach_light,
    route_after_consent,
    route_after_onboard,
    route_after_review,
    route_after_score,
)
from app.graph.state import CoachState


def build_graph(checkpointer):
    g = StateGraph(CoachState)

    g.add_node("onboard", nodes.onboard)
    g.add_node("ask", nodes.ask)
    g.add_node("await_answer", nodes.await_answer)
    g.add_node("score", nodes.score)
    g.add_node("level_review", nodes.level_review)
    g.add_node("coach_offer", nodes.coach_offer)
    g.add_node("consent_await", nodes.consent_await)
    g.add_node("coach_light", nodes.coach_light)
    g.add_node("next_level", nodes.next_level)
    g.add_node("report", nodes.report)
    g.add_node("persist", nodes.persist)

    g.add_edge(START, "onboard")
    g.add_conditional_edges("onboard", route_after_onboard, {"ask": "ask", "report": "report"})
    g.add_edge("ask", "await_answer")
    g.add_edge("await_answer", "score")
    g.add_conditional_edges("score", route_after_score, {"ask": "ask", "review": "level_review", "report": "report"})
    g.add_conditional_edges(
        "level_review",
        route_after_review,
        {"offer": "coach_offer", "next_level": "next_level", "report": "report"},
    )
    g.add_edge("coach_offer", "consent_await")
    g.add_conditional_edges(
        "consent_await",
        route_after_consent,
        {"coach_light": "coach_light", "next_level": "next_level", "report": "report"},
    )
    g.add_conditional_edges(
        "coach_light", route_after_coach_light, {"next_level": "next_level", "report": "report"}
    )
    g.add_edge("next_level", "ask")
    g.add_edge("report", "persist")
    g.add_edge("persist", END)

    return g.compile(checkpointer=checkpointer)
