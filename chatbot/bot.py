import streamlit as st
from chatbot.chunking import load_weather_json, chunk_weather_data
from chatbot.embedding import embed_chunks, embed_query
from chatbot.retrieval import build_faiss_index, retrieve
from datetime import datetime
from chatbot.logger import log_chat  
from chatbot.session import get_chat_session, clear_chat_session

def run_chatbot():
    # Load and process data once
    json_data = load_weather_json()
    chunks = chunk_weather_data(json_data)
    embeddings = embed_chunks(chunks)
    index = build_faiss_index(embeddings)

    # Gemini Chat Session 
    chat = get_chat_session()

    # Initialize message history
    if "messages" not in st.session_state:
        st.session_state["messages"] = []

    # Streamlit UI header
    st.markdown("---")
    col1, col2, col3 = st.columns([13, 1, 1], gap="small")  
    with col1:
        st.markdown("### 🦾🌧️ RainLoop AI Assistant - Ask me...💬")
    with col2:
        if st.button("↻ Restart"):
            st.session_state["messages"] = []
            clear_chat_session()
            st.success("Reset!")
    with col3:
        if st.button("🧹 Clear"):
            st.session_state["messages"] = []
            st.success("Clear!")

    # Display previous messages
    for msg in st.session_state["messages"]:
        with st.chat_message(msg["role"], avatar=msg["avatar"]):
            st.markdown(msg["content"])

    # Input box
    query = st.chat_input("Ask RainLoop AI Assistant about weather conditions, forecasts, or warnings in your area!")

    error_message = "⚠️ No relevant weather data found for your query. Try another location or keyword."

    if query:
        timestamp = datetime.now().strftime("%I:%M %p")
        
        # Store and display user message
        user_msg = f"**[{timestamp}]** {query}"
        st.session_state["messages"].append({
            "role": "user",
            "avatar": "🧑‍💻",
            "content": user_msg
        })
        with st.chat_message("user", avatar="🧑‍💻"):
            st.markdown(user_msg)

        # Embed query and retrieve results
        query_emb = embed_query(query)
        results = retrieve(query, index, embeddings, query_emb)

        if not results:
            # No results found
            st.warning(error_message)
            st.session_state["messages"].append({
                "role": "assistant",
                "avatar": "🌧️",
                "content": error_message
            })
            log_chat(user_input=query, response=error_message, mode="rag")
        else:
            context = "\n".join([r["text"] for r in results])
            # Gemini Prompt
            prompt = (
                f"Act as the RadarLoop Weather Assistant that provides nowcasted information. "
                f"Using the following predicted weather information:\n{context}\n"
                f"Answer this question: {query} and provide short safety tips. "
                f"If place is not found, strictly state no information is available and enter other places, "
                f"do not summarize other info and do not give tips."
            )

            # Generate Gemini response
            with st.spinner("🌧️ RainLoop AI Assistant generating answer..."):
                try:
                    response = chat.send_message(prompt)
                    answer = response.text if hasattr(response, "text") else "⚠️ No response generated."
                except Exception as e:
                    answer = f"⚠️ Error generating response: {e}"

            # Store and display assistant message
            st.session_state["messages"].append({
                "role": "assistant",
                "avatar": "🌧️",
                "content": answer
            })
            with st.chat_message("assistant", avatar="🌧️"):
                st.markdown(answer)

            log_chat(user_input=query, response=answer, mode="rag")
