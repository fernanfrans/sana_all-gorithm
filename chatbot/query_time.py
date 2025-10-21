# chatbot/query_time.py
import re
from typing import Optional

RE_MIN = re.compile(
    r"\bin\s*(?:the\s+)?(?:next\s+)?(\d+)\s*(?:min|mins|minute|minutes)\b",
    re.I,
)
RE_HR = re.compile(
    r"\bin\s*(?:the\s+)?(?:next\s+)?(\d+)\s*(?:hr|hrs|hour|hours)\b",
    re.I,
)

def extract_offset_minutes(text: str) -> Optional[int]:
    """
    Parse phrases like:
      - 'in 5 min/mins/minutes'
      - 'in 2 hr/hrs/hour/hours'
    Returns offset in minutes, or None if not found.
    Prefers hours if both appear.
    """
    m_hr = RE_HR.search(text)
    if m_hr:
        return int(m_hr.group(1)) * 60
    m_min = RE_MIN.search(text)
    if m_min:
        return int(m_min.group(1))
    return None
