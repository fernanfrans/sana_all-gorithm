# chatbot/bot.py
import os
import streamlit as st
from datetime import datetime

from chatbot.chunking import chunk_iter_from_file
from chatbot.embedding import embed_query, build_faiss_index_from_chunks
from chatbot.retrieval import retrieve
from chatbot.logger import log_chat
from chatbot.session import get_chat_session, clear_chat_session

from chatbot.query_time import extract_offset_minutes
from chatbot.file_selector_supabase import (
    select_supabase_file_for_offset,
    MANILA_TZ,
    _compute_target,  # <-- for Selection Debug
)
from chatbot.remote_cache import ensure_local_from_supabase

st.set_page_config(page_title="RainLoop AI Assistant", page_icon="🌧️", layout="wide")


# ---------------- Utils ----------------

def _human_bytes(n: int) -> str:
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} PB"


# ---------------- Session-state helpers ----------------

def _ensure_session_state():
    """Initialize all session_state keys used by the app."""
    if "messages" not in st.session_state:
        st.session_state["messages"] = []  # list[{"role","avatar","content"}]
    if "chat_session" not in st.session_state:
        # lazily create a Gemini chat session; if it fails, keep None (we handle later)
        try:
            st.session_state["chat_session"] = get_chat_session()
        except Exception:
            st.session_state["chat_session"] = None

def _append_message(role: str, avatar: str, content: str):
    """Safe append (avoids KeyError across reruns)."""
    st.session_state.setdefault("messages", [])
    st.session_state["messages"].append({"role": role, "avatar": avatar, "content": content})


# ---------------- Cached index builder ----------------

@st.cache_resource(show_spinner=False)
def _build_index_for_file_cached(local_path: str, batch_size: int = 512):
    """
    Build a FAISS index + records from one local JSON file.
    Cache key includes file mtime, so updates invalidate cache automatically.
    """
    if not os.path.exists(local_path):
        raise FileNotFoundError(f"Data file not found: {local_path}")
    mtime = os.path.getmtime(local_path)  # cache key part

    # Stream chunks from the file and embed in batches
    chunks_iter = chunk_iter_from_file(local_path)
    index, records, dim = build_faiss_index_from_chunks(chunks_iter, batch_size=batch_size)

    return {
        "index": index,
        "records": records,
        "dim": dim,
        "mtime": mtime,
        "path": local_path,
    }


# ---------------- Main app ----------------

def run_chatbot():
    _ensure_session_state()  # <<< IMPORTANT: initialize before any session_state use

    BATCH_SIZE = int(os.getenv("RAINLOOP_EMBED_BATCH", "512"))
    chat = st.session_state.get("chat_session") or get_chat_session()

    # Header & controls
    st.markdown("---")
    col1, col2, col3 = st.columns([13, 1, 1], gap="small")
    with col1:
        st.markdown("### 🦾🌧️ RainLoop AI Assistant - Ask me...💬")
        st.caption("Snapshots are on a 5-minute cadence. Example: `in 30 mins`, `in 2 hours`.")
    with col2:
        if st.button("↻ Restart"):
            st.session_state["messages"] = []
            clear_chat_session()
            st.success("Reset!")
    with col3:
        if st.button("🧹 Clear"):
            st.session_state["messages"] = []
            st.success("Clear!")

    # Render history
    for msg in st.session_state["messages"]:
        with st.chat_message(msg["role"], avatar=msg["avatar"]):
            st.markdown(msg["content"])

    # Input
    query = st.chat_input("Ask: 'How will the weather in Wyoming in 2 hours?' or 'in 30 mins'")
    if not query:
        return

    # Add user message safely
    timestamp = datetime.now(MANILA_TZ).strftime("%I:%M %p")
    user_msg = f"**[{timestamp}]** {query}"
    _append_message("user", "🧑‍💻", user_msg)
    with st.chat_message("user", avatar="🧑‍💻"):
        st.markdown(user_msg)

    error_message = "⚠️ No relevant weather data found. Try another location or lead time."

    # 1) Parse lead time → minutes (supports 'in X minutes' or 'in X hours')
    offset_minutes = extract_offset_minutes(query) or 0

    # 2) Choose Supabase file at/after target time (Asia/Manila, with snap-down for now / ceil for future)
    try:
        selected = select_supabase_file_for_offset(offset_minutes=offset_minutes, prefix="")  # set a folder prefix if needed
    except Exception as e:
        err = f"⚠️ Failed to list/select forecast files: {e}"
        st.warning(err)
        _append_message("assistant", "🌧️", err)
        log_chat(user_input=query, response=err, mode="rag")
        return

    if not selected:
        st.warning(error_message)
        _append_message("assistant", "🌧️", error_message)
        log_chat(user_input=query, response=error_message, mode="rag")
        return

    when_str = selected.dt.strftime("%Y-%m-%d %H:%M:%S %Z")

    # 3) Download selected Supabase file into local cache (once), then build/load index (cached)
    try:
        with st.spinner(f"Fetching forecast {selected.name} (valid at {when_str})…"):
            local_path = ensure_local_from_supabase(selected.name)

        with st.spinner("Indexing (first run per file)…"):
            built = _build_index_for_file_cached(local_path, batch_size=BATCH_SIZE)

    except Exception as e:
        err = f"⚠️ Error preparing index: {e}"
        st.warning(err)
        _append_message("assistant", "🌧️", err)
        log_chat(user_input=query, response=err, mode="rag")
        return

    # ---------------- Sidebar debug: Selection + Snapshot ----------------
    try:
        _now = datetime.now(MANILA_TZ)
        _target = _compute_target(_now, offset_minutes)  # same rounding logic as selector

        with st.sidebar:
            st.markdown("### Selection Debug")
            st.write(f"**Now (Manila):** {_now.strftime('%Y-%m-%d %H:%M:%S %Z')}")
            st.write(f"**Offset (min):** {offset_minutes}")
            st.write(f"**Target (rounded):** {_target.strftime('%Y-%m-%d %H:%M:%S %Z')}")
            st.write(f"**Chosen time:** {selected.dt.strftime('%Y-%m-%d %H:%M:%S %Z')}")
            st.write(f"**Chosen file:** `{selected.name}`")

            st.markdown("### Snapshot Debug")
            st.write(f"**Local file:** `{os.path.basename(built['path'])}`")
            st.write(f"**Valid at:** {when_str}")
            st.write(f"**Entries (chunks):** {len(built['records'])}")
            st.write(f"**Vectors in index:** {built['index'].ntotal}")
            st.write(f"**Local mtime:** {datetime.fromtimestamp(built['mtime']).isoformat()}")
            try:
                size = os.path.getsize(built["path"])
                st.write(f"**File size:** {_human_bytes(size)}")
            except Exception:
                pass
    except Exception:
        # Sidebar should never break the main flow
        pass

    # 4) Retrieve top-k chunks for the query
    try:
        query_emb = embed_query(query)
        results = retrieve(index=built["index"], records=built["records"], query_embedding=query_emb, top_k=5)
    except Exception as e:
        err = f"{error_message}\n\nDetails: {e}"
        st.warning(err)
        _append_message("assistant", "🌧️", err)
        log_chat(user_input=query, response=err, mode="rag")
        return

    if not results:
        st.warning(error_message)
        _append_message("assistant", "🌧️", error_message)
        log_chat(user_input=query, response=error_message, mode="rag")
        return

    # 5) Compose prompt and ask Gemini
    context = "\n".join([r["text"] for r in results])
    prompt = (
        "Act as the RadarLoop Weather Assistant that provides nowcasted information. "
        f"Using the following predicted weather information (valid at {when_str}):\n{context}\n"
        f"Answer this question: {query} and provide short safety tips. "
        "If place is not found, strictly state no information is available and enter other places, "
        "do not summarize other info and do not give tips."
    )

    with st.spinner("🌧️ RainLoop AI Assistant generating answer..."):
        try:
            response = chat.send_message(prompt)
            answer = response.text if hasattr(response, "text") else "⚠️ No response generated."
        except Exception as e:
            answer = f"⚠️ Error generating response: {e}"

    _append_message("assistant", "🌧️", answer)
    with st.chat_message("assistant", avatar="🌧️"):
        st.markdown(answer)

    log_chat(user_input=query, response=answer, mode="rag")


if __name__ == "__main__":
    run_chatbot()
