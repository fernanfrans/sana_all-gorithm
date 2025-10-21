import re
from difflib import SequenceMatcher
from typing import Any, Dict, List, Optional, Tuple


STOPWORDS = {
    "in",
    "at",
    "for",
    "on",
    "the",
    "weather",
    "forecast",
    "please",
    "tell",
    "me",
    "about",
    "show",
    "what",
    "will",
    "be",
    "is",
}


def normalize_place_name(name: str) -> str:
    """
    Mirror backend slug generation so manifest lookups stay aligned.
    """
    base = (name or "").strip().lower()
    slug = re.sub(r"[^a-z0-9]+", "-", base)
    slug = re.sub(r"-{2,}", "-", slug).strip("-")
    return slug or "unknown"


def _strip_time_phrases(text: str) -> str:
    return re.sub(
        r"in\s+\d+\s*(?:mins?|minutes?|hrs?|hours?)",
        " ",
        text,
        flags=re.IGNORECASE,
    )


def _normalize_text(text: str) -> str:
    lowered = text.lower()
    lowered = re.sub(r"[^a-z0-9\s]", " ", lowered)
    lowered = re.sub(r"\s+", " ", lowered)
    return lowered.strip()


def _tokenize(text: str) -> List[str]:
    return [tok for tok in text.split() if tok]


def _score_match(query_tokens: List[str], query_text: str, loc_text: str) -> float:
    if not loc_text:
        return 0.0
    loc_tokens = set(_tokenize(loc_text))
    overlap = len(loc_tokens & set(query_tokens))
    ratio = SequenceMatcher(None, query_text, loc_text).ratio()
    substring_bonus = 0.5 if any(tok in loc_text for tok in query_tokens) else 0.0
    return overlap * 1.5 + ratio + substring_bonus


def rank_locations(
    query: str,
    locations: List[Dict[str, Any]],
    limit: int = 5,
    min_score: float = 0.65,
) -> List[Tuple[float, Dict[str, Any]]]:
    """
    Rank manifest locations against a free-form query.
    Returns up to `limit` entries sorted by score desc.
    """
    stripped = _strip_time_phrases(query)
    normalized_query = _normalize_text(stripped)
    if not normalized_query:
        return []

    query_tokens = [tok for tok in _tokenize(normalized_query) if tok not in STOPWORDS]
    if not query_tokens:
        query_tokens = _tokenize(normalized_query)

    query_slug = normalize_place_name(normalized_query)

    scored: List[Tuple[float, Dict[str, Any]]] = []
    for loc in locations:
        place_text = _normalize_text(loc.get("place", ""))
        slug_text = _normalize_text(loc.get("normalized_place", "").replace("-", " "))

        # Exact slug match wins immediately
        if loc.get("normalized_place") == query_slug:
            return [(1e6, loc)]

        score_place = _score_match(query_tokens, normalized_query, place_text)
        score_slug = _score_match(query_tokens, normalized_query, slug_text)
        score = max(score_place, score_slug)
        if score >= min_score:
            scored.append((score, loc))

    scored.sort(key=lambda x: (-x[0], x[1].get("place", "")))
    return scored[:limit]


def best_location_match(query: str, locations: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    ranked = rank_locations(query, locations, limit=1)
    return ranked[0][1] if ranked else None

