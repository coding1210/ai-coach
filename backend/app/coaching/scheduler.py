"""Spaced re-assessment — turn a one-shot diagnosis into an ongoing program.

After a session we schedule the next review of each competency using a simple
spaced-repetition curve: the shakier something is (bigger gap to target), the
sooner it resurfaces; the more solid, the longer it rests. `due_items` then
reports what's ready for a quick re-check and how long it's been.

Pure functions — `now` is always passed in, so this is deterministic to test.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

# Base rest interval (days) by current level — mastery earns a longer gap.
_BASE_INTERVAL = {1: 1, 2: 2, 3: 4, 4: 9, 5: 21}


def interval_days(current_level: int, target_level: int) -> int:
    """Days until the next review. A still-open gap pulls it sooner."""
    base = _BASE_INTERVAL.get(max(1, min(5, current_level)), 4)
    gap = max(0, target_level - current_level)
    if gap >= 2:
        return max(1, base // 2)  # weak → resurface fast
    if gap == 1:
        return base
    return base * 2  # at/above target → let it rest longer


def _parse(dt) -> datetime | None:
    if dt is None:
        return None
    if isinstance(dt, datetime):
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    try:
        return datetime.fromisoformat(str(dt).replace("Z", "+00:00"))
    except ValueError:
        return None


def schedule_after_session(entries: list, now: datetime) -> dict[str, str]:
    """Return {competency_id: next_review_iso} for every scored competency."""
    out: dict[str, str] = {}
    for e in entries:
        cur = e.current_level or 1
        tgt = e.target_level or cur
        out[e.competency_id] = (now + timedelta(days=interval_days(cur, tgt))).isoformat()
    return out


def due_items(
    entries: list,
    next_reviews: dict[str, str],
    now: datetime,
    cmap=None,
) -> list[dict]:
    """Competencies whose next review is at or before `now`, most-overdue first."""
    due: list[dict] = []
    for e in entries:
        cur = e.current_level or 1
        tgt = e.target_level or cur
        scheduled = _parse(next_reviews.get(e.competency_id))
        if scheduled is None:
            base = _parse(e.updated_at) or now
            scheduled = base + timedelta(days=interval_days(cur, tgt))
        if scheduled > now:
            continue
        days_over = (now - scheduled).days
        name = e.competency_id
        if cmap is not None:
            try:
                name = cmap.competency(e.competency_id).name
            except KeyError:
                pass
        due.append(
            {
                "competency_id": e.competency_id,
                "competency_name": name,
                "current_level": cur,
                "target_level": tgt,
                "days_overdue": max(0, days_over),
                "still_weak": cur < tgt,
            }
        )
    due.sort(key=lambda d: (d["still_weak"], d["days_overdue"]), reverse=True)
    return due
