"""Assemble and compile the coaching state graph (Design.md §2).

    onboard → assess_ask → assess_await → score → report
            → plan_focus → coach → coach_await → persist

`assess_await` and `coach_await` pause the graph via interrupt() to collect input,
so the compiled graph REQUIRES a checkpointer. The caller supplies one
(AsyncPostgresSaver in the app, InMemorySaver in tests) to keep this module free
of I/O concerns.
"""

from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from app.graph import nodes
from app.graph.edges import (
    route_after_coach,
    route_after_coach_await,
    route_after_onboard,
    route_after_score,
)
from app.graph.state import CoachState


def build_graph(checkpointer):
    g = StateGraph(CoachState)

    g.add_node("onboard", nodes.onboard)
    g.add_node("assess_ask", nodes.assess_ask)
    g.add_node("assess_await", nodes.assess_await)
    g.add_node("score", nodes.score)
    g.add_node("report", nodes.report)
    g.add_node("plan_focus", nodes.plan_focus)
    g.add_node("coach", nodes.coach)
    g.add_node("coach_await", nodes.coach_await)
    g.add_node("challenge", nodes.challenge)
    g.add_node("challenge_await", nodes.challenge_await)
    g.add_node("persist", nodes.persist)

    g.add_edge(START, "onboard")
    g.add_conditional_edges(
        "onboard", route_after_onboard, {"assess": "assess_ask", "report": "report"}
    )
    g.add_edge("assess_ask", "assess_await")
    g.add_edge("assess_await", "score")
    g.add_conditional_edges(
        "score", route_after_score, {"assess": "assess_ask", "report": "report"}
    )
    g.add_edge("report", "plan_focus")
    g.add_edge("plan_focus", "coach")
    g.add_conditional_edges(
        "coach", route_after_coach, {"challenge": "challenge", "reply": "coach_await"}
    )
    g.add_edge("challenge", "challenge_await")
    g.add_conditional_edges(
        "challenge_await", route_after_coach_await, {"coach": "coach", "persist": "persist"}
    )
    g.add_conditional_edges(
        "coach_await", route_after_coach_await, {"coach": "coach", "persist": "persist"}
    )
    g.add_edge("persist", END)

    return g.compile(checkpointer=checkpointer)
