import streamlit as st
from chatbot.chunking import load_weather_json, chunk_weather_data
from chatbot.embedding import embed_chunks, embed_query
from chatbot.retrieval import build_faiss_index, retrieve
from config.settings import gen_ai, CHAT_MODEL

def run_chatbot():
    # Load and process data
    json_data = load_weather_json()
    chunks = chunk_weather_data(json_data)
    embeddings = embed_chunks(chunks)
    index = build_faiss_index(embeddings)

    # Gemini chat model (generation only)
    model = gen_ai.GenerativeModel(model_name=CHAT_MODEL)

    # Streamlit UI
    st.title("🦾🌧️ Weather RAG Assistant")

    query = st.text_input("Ask about weather conditions (e.g., 'What's the rain status in Cebu')")

    if query:
        # Embed query locally
        query_emb = embed_query(query)

        # Retrieve with FAISS
        results = retrieve(query, index, embeddings, query_emb)

        if not results:
            st.warning("⚠️ No relevant weather data found for your query. Try another location or keyword.")
        else:
            context = "\n".join([r["text"] for r in results])
            prompt = f"Using the following weather data:\n{context}\nAnswer this question: {query}"

            try:
                response = model.generate_content(prompt)
                answer = response.text if hasattr(response, "text") else "⚠️ No response generated."
            except Exception as e:
                answer = f"⚠️ Error generating response: {e}"

            st.markdown("### 💬 Gemini's Answer")
            st.write(answer)
