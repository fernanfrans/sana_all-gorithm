import streamlit as st
from chatbot.session import get_chat_session
from chatbot.utils import translate_role

def run_chatbot():
    st.markdown("---")
    # Chatbot title
    st.markdown("### 🦾🌧️ RAINLOOP Assistant - Ask Me.. 💬")

    # Initialize chat session
    chat_session = get_chat_session()

    # Display chat history
    for msg in chat_session.history:
        with st.chat_message(translate_role(msg.role)):
            st.markdown(msg.parts[0].text)

    # Chat input
    user_input = st.chat_input("Ask RAINLOOP Chatbot...")
    if user_input:
        st.chat_message("user", avatar="🧑‍💻").markdown(user_input)
        response = chat_session.send_message(user_input)
        with st.chat_message("assistant", avatar="🦾🌧️"):
            st.markdown(response.text)

    
