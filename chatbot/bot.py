# chatbot/bot.py
import math
from pathlib import Path
import streamlit as st
from datetime import datetime, timedelta, timezone

from chatbot.session import get_chat_session, clear_chat_session
from chatbot.query_time import extract_offset_minutes
from chatbot.file_selector_supabase import MANILA_TZ
from chatbot.supabase_ops import (
    latest_complete_run_dir,
    load_manifest,
    fetch_record_json,
    resolve_offset_for_location,
)
from chatbot.location_lookup import rank_locations

# Absolute path to assistant avatar image (define before set_page_config)
ASSISTANT_AVATAR = str((Path(__file__).resolve().parent.parent / "assets" / "finalicon.png"))

st.set_page_config(page_title="RainLoop AI Assistant", page_icon=ASSISTANT_AVATAR, layout="wide")


# ---------------- Session helpers ----------------

def _ensure_session_state():
    """Initialize all session_state keys used by the app."""
    if "messages" not in st.session_state:
        st.session_state["messages"] = []
    if "chat_session" not in st.session_state:
        try:
            st.session_state["chat_session"] = get_chat_session()
        except Exception:
            st.session_state["chat_session"] = None


def _append_message(role: str, avatar: str, content: str):
    st.session_state.setdefault("messages", [])
    st.session_state["messages"].append({"role": role, "avatar": avatar, "content": content})


# ---------------- Utility functions ----------------

def _format_local(dt: datetime) -> str:
    return dt.astimezone(MANILA_TZ).strftime("%Y-%m-%d %I:%M %p %Z")


def _parse_iso_to_utc(value: str) -> datetime:
    cleaned = (value or "").strip()
    if not cleaned:
        raise ValueError("Datetime string is empty")
    if cleaned.endswith("Z"):
        cleaned = cleaned[:-1] + "+00:00"
    dt = datetime.fromisoformat(cleaned)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _select_best_slot(slots, target_dt: datetime):
    if not slots:
        raise ValueError("No forecast slots are available.")
    target_dt = target_dt.astimezone(timezone.utc)
    best = None
    best_key = (float("inf"), True)
    for slot in slots:
        valid_dt = slot["valid_dt_utc"].astimezone(timezone.utc)
        diff_seconds = (valid_dt - target_dt).total_seconds()
        key = (abs(diff_seconds), diff_seconds < 0)
        if key < best_key:
            best_key = key
            best = slot
    return best


def _display_run_freshness(base_time_utc: datetime):
    """Compute staleness and age in minutes.

    Returns (is_stale: bool, minutes_old: float).
    """
    run_age = datetime.now(timezone.utc) - base_time_utc
    minutes_old = run_age.total_seconds() / 60
    if run_age > timedelta(minutes=10):
        return True, minutes_old
    return False, minutes_old


# ---------------- Main app ----------------

def run_chatbot():
    _ensure_session_state()
    chat = st.session_state.get("chat_session") or get_chat_session()

    # Header & controls
    st.markdown("---")
    col1, col2, col3 = st.columns([13, 1, 1], gap="small")
    with col1:
        st.markdown("### RainLoop AI Assistant - Ask me...")
        st.caption("Nowcast update every 5-minute steps. Examples: `in 5 mins`, `in 10 mins`.")
    with col2:
        if st.button("↻ Restart"):
            st.session_state["messages"] = []
            clear_chat_session()
            st.success("Reset!")
    with col3:
        if st.button("🧹 Clear"):
            st.session_state["messages"] = []
            st.success("Clear!")

    summary_placeholder = st.empty()
    history_placeholder = st.empty()
    alert_placeholder = st.empty()
    status_placeholder = st.empty()

    def _render_history():
        history_placeholder.empty()
        with history_placeholder.container():
            for msg in st.session_state.get("messages", []):
                with st.chat_message(msg["role"], avatar=msg["avatar"]):
                    st.markdown(msg["content"])
        _render_summary()

    def _render_summary():
        summary_placeholder.empty()
        summary = st.session_state.get("forecast_summary")
        if not summary:
            return
        freshness_icon = "✅" if not summary.get("stale") else "⚠️"
        age_text = summary.get("age_text") or ""
        if not summary.get("stale"):
            lines = [
                summary.get("requested_local", "?"),
                f"Base: {summary.get('base_time_local','?')}",
                f"Place: {summary.get('place','?')}",
                f"Reflectivity: {summary.get('reflectivity','?')} dBZ",
                f"Rain: {summary.get('rain_category','?')}",
                f"Match Score: {summary.get('match_score','?')}",
            ]
        else:
            if age_text:
                lines = [f"Age: {age_text}"]
        message = f"**{freshness_icon} Nowcast Snapshot**\n" + "\n".join(f"- {line}" for line in lines if line)
        if summary.get("stale"):
            summary_placeholder.warning(message)
        else:
            summary_placeholder.success(message)

    def _status_replace(text: str):
        status_placeholder.info(text)

    def _status_finish():
        status_placeholder.empty()

    def _alert_warning(text: str):
        alert_placeholder.warning(text)

    def _alert_clear():
        alert_placeholder.empty()

    def _clear_summary():
        st.session_state.pop("forecast_summary", None)
        summary_placeholder.empty()

    _render_history()
    _alert_clear()

    query = st.chat_input("Ask: 'How will the weather in Wyoming in 2 hours?' or 'in 30 mins'")

    if not query:
        _clear_summary()
        _render_history()
        return

    timestamp = datetime.now(MANILA_TZ).strftime("%I:%M %p")
    user_msg = f"**[{timestamp}]** {query}"
    _append_message("user", "🧑‍💻", user_msg)
    _render_history()

    _status_replace("⏳ Fetching nowcast data…")

    offset_minutes = extract_offset_minutes(query) or 0

    try:
        run_id = latest_complete_run_dir()
        if not run_id:
            raise RuntimeError("No completed forecast run available yet.")
        manifest = load_manifest(run_id)
    except Exception as exc:
        _status_finish()
        err = f"⚠️ Unable to load forecast run: {exc}"
        _alert_warning(err)
        _append_message("assistant", ASSISTANT_AVATAR, err)
        _clear_summary()
        _render_history()
        return

    try:
        base_time_iso = manifest.get("base_time_utc") or manifest["base_time"]
        base_time_utc = datetime.fromisoformat(base_time_iso)
        if base_time_utc.tzinfo is None:
            base_time_utc = base_time_utc.replace(tzinfo=timezone.utc)
        else:
            base_time_utc = base_time_utc.astimezone(timezone.utc)
        base_time_local = base_time_utc.astimezone(MANILA_TZ)
    except Exception as exc:
        _status_finish()
        err = f"⚠️ Manifest is missing base_time: {exc}"
        _alert_warning(err)
        _append_message("assistant", ASSISTANT_AVATAR, err)
        _clear_summary()
        _render_history()
        return

    lead_bins = manifest.get("lead_bins") or []
    files = manifest.get("files") or {}
    available_slots = []

    for filename, entry in files.items():
        if not isinstance(filename, str) or not filename.endswith(".jsonl"):
            continue
        lead_value = entry.get("lead_minutes")
        valid_iso = entry.get("valid_time_utc") or entry.get("valid_time")
        valid_dt_utc = None

        if isinstance(valid_iso, str):
            try:
                valid_dt_utc = _parse_iso_to_utc(valid_iso)
            except Exception:
                valid_dt_utc = None

        if valid_dt_utc is None and lead_value is not None:
            try:
                valid_dt_utc = base_time_utc + timedelta(minutes=int(lead_value))
            except Exception:
                valid_dt_utc = None

        if valid_dt_utc is None:
            continue

        try:
            lead_int = int(lead_value)
        except Exception:
            diff_minutes = (valid_dt_utc - base_time_utc).total_seconds() / 60.0
            lead_int = int(round(diff_minutes))

        available_slots.append(
            {
                "filename": filename,
                "entry": entry,
                "lead_minutes": lead_int,
                "valid_dt_utc": valid_dt_utc,
                "valid_time_label": entry.get("valid_time_label"),
            }
        )

    if not available_slots and lead_bins:
        for minutes in lead_bins:
            try:
                minutes_int = int(minutes)
            except Exception:
                continue
            legacy_name = f"lead_{minutes_int:03d}.jsonl"
            entry = files.get(legacy_name)
            if not entry:
                continue
            valid_dt_utc = base_time_utc + timedelta(minutes=minutes_int)
            available_slots.append(
                {
                    "filename": legacy_name,
                    "entry": entry,
                    "lead_minutes": minutes_int,
                    "valid_dt_utc": valid_dt_utc,
                    "valid_time_label": entry.get("valid_time_label")
                    or valid_dt_utc.astimezone(MANILA_TZ).strftime("%Y%m%dT%H%MPHT"),
                }
            )

    if not available_slots:
        _status_finish()
        err = "⚠️ Manifest has no forecast time slots."
        _alert_warning(err)
        _append_message("assistant", ASSISTANT_AVATAR, err)
        _clear_summary()
        _render_history()
        return

    available_slots.sort(key=lambda slot: slot["valid_dt_utc"])
    target_dt_utc = datetime.now(timezone.utc) + timedelta(minutes=offset_minutes)
    try:
        selected_slot = _select_best_slot(available_slots, target_dt_utc)
    except Exception as exc:
        _status_finish()
        err = f"⚠️ Unable to pick forecast slot: {exc}"
        _alert_warning(err)
        _append_message("assistant", ASSISTANT_AVATAR, err)
        _clear_summary()
        _render_history()
        return

    lead_minutes = selected_slot["lead_minutes"]
    lead_filename = selected_slot["filename"]
    file_entry = selected_slot["entry"]
    valid_dt_utc = selected_slot["valid_dt_utc"]
    valid_label = selected_slot.get("valid_time_label")

    locations = manifest.get("locations") or []
    matches = rank_locations(query, locations)
    cached_location = st.session_state.get("latest_location")
    used_cached_location = False

    if matches:
        best_score, location_entry = matches[0]
        st.session_state["latest_location"] = location_entry
    elif cached_location:
        location_entry = cached_location
        best_score = float("nan")
        used_cached_location = True
    else:
        _status_finish()
        err = "⚠️ I couldn't find that place in the latest forecast data."
        _alert_warning(err)
        _append_message("assistant", ASSISTANT_AVATAR, err)
        _clear_summary()
        _render_history()
        return
    if used_cached_location or (isinstance(best_score, float) and math.isnan(best_score)):
        score_display = "previous query"
    else:
        score_display = f"{best_score:.2f}"
    normalized_place = location_entry.get("normalized_place")
    if not normalized_place:
        _status_finish()
        err = "⚠️ Selected location is missing a normalized key."
        _alert_warning(err)
        _append_message("assistant", ASSISTANT_AVATAR, err)
        _clear_summary()
        _render_history()
        return

    try:
        offset, length = resolve_offset_for_location(
            run_id=run_id,
            filename=lead_filename,
            file_entry=file_entry,
            location_index=int(location_entry.get("location_index", -1)),
        )
    except Exception as exc:
        _status_finish()
        err = f"⚠️ No record found for `{normalized_place}` in {lead_filename} ({exc})."
        _alert_warning(err)
        _append_message("assistant", ASSISTANT_AVATAR, err)
        _clear_summary()
        _render_history()
        return

    try:
        record = fetch_record_json(run_id, lead_filename, offset, length)
    except Exception as exc:
        _status_finish()
        err = f"⚠️ Unable to download forecast record: {exc}"
        _alert_warning(err)
        _append_message("assistant", ASSISTANT_AVATAR, err)
        _render_history()
        _clear_summary()
        return

    valid_when_local = _format_local(valid_dt_utc)
    target_when_local = _format_local(target_dt_utc)

    is_stale, minutes_old = _display_run_freshness(base_time_utc)

    reflectivity = record.get("reflectivity")
    rain_category = record.get("rain_category") or "Unknown"
    latitude = record.get("latitude")
    longitude = record.get("longitude")
    place_name = record.get("place") or location_entry.get("place")
    try:
        reflectivity_display = f"{float(reflectivity):.1f}"
    except (TypeError, ValueError):
        reflectivity_display = "?"
        if isinstance(reflectivity, str) and reflectivity.strip():
            reflectivity_display = reflectivity

    base_time_local_str = base_time_local.strftime("%Y-%m-%d %I:%M %p %Z")
    lead_display = f"+{int(lead_minutes)} min"
    summary_data = {
        "run_id": run_id,
        "lead_minutes": lead_minutes,
        "lead_display": lead_display,
        "base_time_local": base_time_local_str,
        "valid_local": valid_when_local,
        "lead_filename": lead_filename,
        "valid_label": valid_label,
        "place": place_name or "Unknown location",
        "reflectivity": reflectivity_display,
        "rain_category": rain_category,
        "match_score": score_display,
        "stale": is_stale,
        "age_text": f"{minutes_old:.1f} min old",
        "requested_local": target_when_local,
    }
    st.session_state["forecast_summary"] = summary_data
    _render_history()
    
    # If the latest run is stale, finish spinner, show warning, and respond.
    if is_stale:
        _status_finish()
        _alert_warning(
            f"Latest run is {minutes_old:.1f} minutes old. A new update should arrive soon."
        )
        answer = "No new information available."
        _append_message("assistant", ASSISTANT_AVATAR, answer)
        _render_history()
        return

    # Sidebar diagnostics
    try:
        with st.sidebar:
            st.markdown("### Forecast Debug")
            st.write(f"**Run ID:** `{run_id}`")
            st.write(f"**Base (UTC):** {base_time_utc.isoformat()}")
            st.write(f"**Lead minutes:** {lead_minutes}")
            st.write(f"**Valid (UTC):** {valid_dt_utc.isoformat()}")
            st.write(f"**Valid (Manila):** {valid_when_local}")
            if valid_label:
                st.write(f"**Valid label:** {valid_label}")
            st.write(f"**Requested (Manila):** {target_when_local}")
            st.write(f"**Forecast file:** `{lead_filename}`")
            st.write(f"**Byte range:** {offset} – {offset + length - 1}")
            st.write(f"**Location:** {location_entry.get('place')}")
            st.write(f"**Match score/source:** {score_display}")

            if len(matches) > 1:
                st.markdown("### Other matches")
                for score, loc in matches[1:4]:
                    st.write(f"{score:.2f} — {loc.get('place')}")
    except Exception:
        pass  # sidebar should not break main flow

    context = (
        f"Run ID: {run_id}\n"
        f"Base time (UTC): {base_time_utc.isoformat()}\n"
        f"Requested time (UTC): {target_dt_utc.isoformat()}\n"
        f"Valid time (UTC): {valid_dt_utc.isoformat()}\n"
        f"Location: {place_name}\n"
        f"Latitude: {latitude}, Longitude: {longitude}\n"
        f"Lead minutes: {lead_minutes}\n"
        f"Reflectivity (dBZ): {reflectivity}\n"
        f"Rain category: {rain_category}\n"
    )

    prompt = (
        "You are the RadarLoop Weather Assistant. Use the forecast record below to answer "
        "the user's weather question concisely, include rain intensity, and provide exactly three safety tips "
        "as a bulleted list (one sentence each). "
        "If the location does not exist in the record, reply that no information is available.\n\n"
        f"Forecast record:\n{context}\n"
        f"User question: {query}"
    )

    _status_replace("🌧️ RainLoop AI Assistant generating answer...")

    try:
        response = chat.send_message(prompt)
        answer = response.text if hasattr(response, "text") else "⚠️ No response generated."
    except Exception as exc:
        answer = f"⚠️ Error generating response: {exc}"
    finally:
        _status_finish()

    _append_message("assistant", ASSISTANT_AVATAR, answer)
    _render_history()


if __name__ == "__main__":
    run_chatbot()
