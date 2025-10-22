from datetime import datetime, timedelta, timezone
from typing import Iterable

MANILA_TZ = timezone(timedelta(hours=8))


def to_manila(dt: datetime) -> datetime:
    return dt.astimezone(MANILA_TZ)


def nearest_lead_minutes(lead_bins: Iterable[int], base_time: datetime, target_dt: datetime) -> int:
    """
    Shared helper for picking the closest lead to a desired timestamp.
    Prefers future (or exact) leads in the event of ties.
    """
    base_time = base_time.astimezone(timezone.utc)
    target_dt = target_dt.astimezone(timezone.utc)
    candidates = sorted({int(m) for m in lead_bins})
    if not candidates:
        raise ValueError("lead_bins is empty")

    best = candidates[0]
    best_key = (float("inf"), True)
    for minutes in candidates:
        valid_dt = base_time + timedelta(minutes=minutes)
        diff_seconds = (valid_dt - target_dt).total_seconds()
        key = (abs(diff_seconds), diff_seconds < 0)
        if key < best_key:
            best_key = key
            best = minutes
    return best
