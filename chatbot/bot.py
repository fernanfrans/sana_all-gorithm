# chatbot/bot.py
import math
import streamlit as st
from datetime import datetime, timedelta, timezone

from chatbot.session import get_chat_session, clear_chat_session
from chatbot.query_time import extract_offset_minutes
from chatbot.file_selector_supabase import MANILA_TZ, nearest_lead_minutes
from chatbot.supabase_ops import (
    latest_complete_run_dir,
    load_manifest,
    fetch_record_json,
    resolve_offset_for_location,
)
from chatbot.location_lookup import rank_locations

st.set_page_config(page_title="RainLoop AI Assistant", page_icon="🌧️", layout="wide")


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


def _valid_datetime(base_time_utc: datetime, lead_minutes: int) -> datetime:
    return base_time_utc + timedelta(minutes=int(lead_minutes))


def _display_run_freshness(base_time_utc: datetime):
    run_age = datetime.now(timezone.utc) - base_time_utc
    if run_age > timedelta(minutes=10):
        minutes_old = run_age.total_seconds() / 60
        st.warning(
            f"Latest run is {minutes_old:.1f} minutes old. A new update should arrive soon."
        )


# ---------------- Main app ----------------

def run_chatbot():
    _ensure_session_state()
    chat = st.session_state.get("chat_session") or get_chat_session()

    # Header & controls
    st.markdown("---")
    col1, col2, col3 = st.columns([13, 1, 1], gap="small")
    with col1:
        st.markdown("### 🦾🌧️ RainLoop AI Assistant - Ask me...💬")
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

    # Render chat history
    for msg in st.session_state["messages"]:
        with st.chat_message(msg["role"], avatar=msg["avatar"]):
            st.markdown(msg["content"])

    query = st.chat_input("Ask: 'How will the weather in Wyoming in 2 hours?' or 'in 30 mins'")
    if not query:
        return

    timestamp = datetime.now(MANILA_TZ).strftime("%I:%M %p")
    user_msg = f"**[{timestamp}]** {query}"
    _append_message("user", "🧑‍💻", user_msg)
    with st.chat_message("user", avatar="🧑‍💻"):
        st.markdown(user_msg)

    spinner_anchor = st.empty()
    spinner_ctx = None
    container_ctx = None

    def _spinner_replace(text: str):
        nonlocal spinner_ctx, container_ctx
        if container_ctx is None:
            container_ctx = spinner_anchor.container()
            container_ctx.__enter__()
        if spinner_ctx is not None:
            spinner_ctx.__exit__(None, None, None)
        spinner_ctx = st.spinner(text)
        spinner_ctx.__enter__()

    def _spinner_finish():
        nonlocal spinner_ctx, container_ctx
        if spinner_ctx is not None:
            spinner_ctx.__exit__(None, None, None)
            spinner_ctx = None
        if container_ctx is not None:
            container_ctx.__exit__(None, None, None)
            container_ctx = None
        spinner_anchor.empty()

    _spinner_replace("⏳ Fetching nowcast data…")

    offset_minutes = extract_offset_minutes(query) or 0

    try:
        run_id = latest_complete_run_dir()
        if not run_id:
            raise RuntimeError("No completed forecast run available yet.")
        manifest = load_manifest(run_id)
    except Exception as exc:
        _spinner_finish()
        err = f"⚠️ Unable to load forecast run: {exc}"
        st.warning(err)
        _append_message("assistant", "🌧️", err)
        return

    try:
        base_time_iso = manifest["base_time"]
        base_time_utc = datetime.fromisoformat(base_time_iso)
        if base_time_utc.tzinfo is None:
            base_time_utc = base_time_utc.replace(tzinfo=timezone.utc)
        else:
            base_time_utc = base_time_utc.astimezone(timezone.utc)
    except Exception as exc:
        _spinner_finish()
        err = f"⚠️ Manifest is missing base_time: {exc}"
        st.warning(err)
        _append_message("assistant", "🌧️", err)
        return

    lead_bins = manifest.get("lead_bins") or []
    if not lead_bins:
        _spinner_finish()
        err = "⚠️ Manifest has no lead_bins."
        st.warning(err)
        _append_message("assistant", "🌧️", err)
        return

    if offset_minutes >= 0:
        target_dt_utc = base_time_utc + timedelta(minutes=offset_minutes)
    else:
        target_dt_utc = datetime.now(timezone.utc) + timedelta(minutes=offset_minutes)
    lead_minutes = nearest_lead_minutes(lead_bins, base_time_utc, target_dt_utc)
    lead_filename = f"lead_{int(lead_minutes):03d}.jsonl"

    files = manifest.get("files", {})
    file_entry = files.get(lead_filename)
    if not file_entry:
        _spinner_finish()
        err = f"⚠️ Lead file `{lead_filename}` is missing from manifest."
        st.warning(err)
        _append_message("assistant", "🌧️", err)
        return

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
        _spinner_finish()
        err = "⚠️ I couldn't find that place in the latest forecast data."
        st.warning(err)
        _append_message("assistant", "🌧️", err)
        return
    normalized_place = location_entry.get("normalized_place")
    if not normalized_place:
        _spinner_finish()
        err = "⚠️ Selected location is missing a normalized key."
        st.warning(err)
        _append_message("assistant", "🌧️", err)
        return

    try:
        offset, length = resolve_offset_for_location(
            run_id=run_id,
            filename=lead_filename,
            file_entry=file_entry,
            location_index=int(location_entry.get("location_index", -1)),
        )
    except Exception as exc:
        _spinner_finish()
        err = f"⚠️ No record found for `{normalized_place}` in {lead_filename} ({exc})."
        st.warning(err)
        _append_message("assistant", "🌧️", err)
        return

    try:
        record = fetch_record_json(run_id, lead_filename, offset, length)
    except Exception as exc:
        _spinner_finish()
        err = f"⚠️ Unable to download forecast record: {exc}"
        st.warning(err)
        _append_message("assistant", "🌧️", err)
        return

    valid_dt_utc = _valid_datetime(base_time_utc, lead_minutes)
    valid_when_local = _format_local(valid_dt_utc)

    _display_run_freshness(base_time_utc)

    # Sidebar diagnostics
    try:
        with st.sidebar:
            st.markdown("### Forecast Debug")
            st.write(f"**Run ID:** `{run_id}`")
            st.write(f"**Base (UTC):** {base_time_utc.isoformat()}")
            st.write(f"**Lead minutes:** {lead_minutes}")
            st.write(f"**Valid (Manila):** {valid_when_local}")
            st.write(f"**Lead file:** `{lead_filename}`")
            st.write(f"**Byte range:** {offset} – {offset + length - 1}")
            st.write(f"**Location:** {location_entry.get('place')}")
            if used_cached_location or (isinstance(best_score, float) and math.isnan(best_score)):
                score_display = "previous query"
            else:
                score_display = f"{best_score:.2f}"
            st.write(f"**Match score/source:** {score_display}")

            if len(matches) > 1:
                st.markdown("### Other matches")
                for score, loc in matches[1:4]:
                    st.write(f"{score:.2f} — {loc.get('place')}")
    except Exception:
        pass  # sidebar should not break main flow

    reflectivity = record.get("reflectivity")
    rain_category = record.get("rain_category")
    latitude = record.get("latitude")
    longitude = record.get("longitude")
    place_name = record.get("place")

    context = (
        f"Run ID: {run_id}\n"
        f"Base time (UTC): {base_time_utc.isoformat()}\n"
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

    _spinner_replace("🌧️ RainLoop AI Assistant generating answer...")

    try:
        response = chat.send_message(prompt)
        answer = response.text if hasattr(response, "text") else "⚠️ No response generated."
    except Exception as exc:
        answer = f"⚠️ Error generating response: {exc}"
    finally:
        _spinner_finish()

    _append_message("assistant", "🌧️", answer)
    with st.chat_message("assistant", avatar="🌧️"):
        st.markdown(answer)


if __name__ == "__main__":
    run_chatbot()
