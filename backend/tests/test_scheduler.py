"""Spaced re-assessment scheduler — intervals, scheduling, and due detection."""

from datetime import datetime, timedelta, timezone

from app.coaching.scheduler import due_items, interval_days, schedule_after_session
from app.models import LedgerEntry

NOW = datetime(2026, 7, 19, tzinfo=timezone.utc)


def test_interval_shorter_for_bigger_gaps():
    # A wide gap resurfaces sooner than an at-target competency.
    weak = interval_days(current_level=1, target_level=4)
    solid = interval_days(current_level=4, target_level=4)
    assert weak < solid


def _entry(cid, cur, tgt, updated):
    return LedgerEntry(
        competency_id=cid, baseline_level=cur, current_level=cur, target_level=tgt, updated_at=updated
    )


def test_schedule_after_session_covers_all_entries():
    entries = [_entry("rag.chunking", 2, 4, NOW), _entry("py.async", 4, 4, NOW)]
    sched = schedule_after_session(entries, NOW)
    assert set(sched) == {"rag.chunking", "py.async"}
    # weak spot is scheduled sooner than the solid one
    assert sched["rag.chunking"] < sched["py.async"]


def test_due_items_flags_overdue_weak_first():
    old = NOW - timedelta(days=30)
    entries = [
        _entry("rag.chunking", 2, 4, old),  # weak + long overdue
        _entry("py.async", 4, 4, NOW),       # solid, just done → not due
    ]
    due = due_items(entries, {}, NOW)
    ids = [d["competency_id"] for d in due]
    assert "rag.chunking" in ids
    assert "py.async" not in ids
    assert due[0]["still_weak"] is True


def test_explicit_schedule_overrides_computed():
    entries = [_entry("rag.chunking", 2, 4, NOW)]
    future = (NOW + timedelta(days=10)).isoformat()
    assert due_items(entries, {"rag.chunking": future}, NOW) == []
