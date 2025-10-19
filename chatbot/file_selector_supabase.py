# chatbot/file_selector_supabase.py
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from chatbot.supabase_ops import list_files


FILENAME_RE = re.compile(r"^(?:(?:weather_data|CHATBOT)_)?(\d{8})_(\d{6})\.json$")
MANILA_TZ = timezone(timedelta(hours=8))

@dataclass(frozen=True)
class ForecastItem:
    name: str
    dt: datetime  # tz-aware

def _parse_dt(date_str: str, time_str: str) -> datetime:
    y = int(date_str[0:4]); m = int(date_str[4:6]); d = int(date_str[6:8])
    hh = int(time_str[0:2]); mm = int(time_str[2:4]); ss = int(time_str[4:6])
    return datetime(y, m, d, hh, mm, ss, tzinfo=MANILA_TZ)

def _snap_down_5min(dt: datetime) -> datetime:
    """08:25:12 -> 08:25:00; 08:25:00 -> 08:25:00"""
    dt = dt.replace(second=0, microsecond=0)
    return dt - timedelta(minutes=(dt.minute % 5))

def _ceil_5min(dt: datetime) -> datetime:
    """08:25:00 -> 08:25:00; 08:25:01 -> 08:30:00"""
    snap = _snap_down_5min(dt)
    return snap if dt == snap else snap + timedelta(minutes=5)

def _list_and_parse(prefix: str = "") -> List[ForecastItem]:
    names = list_files(prefix=prefix) or []
    items: List[ForecastItem] = []
    for name in names:
        m = FILENAME_RE.match(name)
        if not m:
            continue
        items.append(ForecastItem(name=name, dt=_parse_dt(m.group(1), m.group(2))))
    items.sort(key=lambda x: x.dt)
    return items

def _compute_target(now: datetime, offset_minutes: int) -> datetime:
    """
    If offset == 0  -> use current 5-min bucket (snap down).
    If offset  > 0  -> ceil(now + offset) to next 5-min boundary.
    """
    t = now + timedelta(minutes=offset_minutes)
    return _snap_down_5min(t) if offset_minutes <= 0 else _ceil_5min(t)

def select_supabase_file_for_offset(
    offset_minutes: int,
    now: Optional[datetime] = None,
    prefix: str = ""
) -> Optional[ForecastItem]:
    items = _list_and_parse(prefix=prefix)
    if not items:
        return None
    if now is None:
        now = datetime.now(MANILA_TZ)

    target = _compute_target(now, offset_minutes)

    # First file at/after target; if none, fall back to latest available
    for it in items:
        if it.dt >= target:
            return it
    return items[-1]
