import streamlit as st

def inject_styles():
    st.markdown("""
    <style>
        .main > div { padding-top: 1rem; }
        .stApp > header { background-color: transparent; }
        .header-container {
            background: linear-gradient(90deg, #1e3a8a 0%, #3b82f6 100%);
            padding: 0.5rem 1rem;
            margin: -1rem -1rem 1rem -1rem;
            border-bottom: 3px solid #fbbf24;
        }
        .header-title { color: white !important; font-size: 1.5rem; font-weight: bold; margin: 0; }
        .header-subtitle { color: #e5e7eb; font-size: 0.9rem; margin: 0; }
        .warning-card { background: linear-gradient(90deg, #dc2626 0%, #ef4444 100%); color: white; padding: 0.75rem; border-radius: 0.5rem; margin: 0.5rem 0; border-left: 4px solid #fbbf24; }
        .advisory-card { background: linear-gradient(90deg, #0891b2 0%, #06b6d4 100%); color: white; padding: 0.75rem; border-radius: 0.5rem; margin: 0.5rem 0; border-left: 4px solid #fbbf24; }
        .info-card { background: linear-gradient(90deg, #059669 0%, #10b981 100%); color: white; padding: 0.75rem; border-radius: 0.5rem; margin: 0.5rem 0; border-left: 4px solid #fbbf24; }
        .weather-current { background: rgba(30, 58, 138, 0.1); border-radius: 0.5rem; padding: 1rem; border: 1px solid #3b82f6; }
        .chatbot-container { background: #f8fafc; border-radius: 0.5rem; padding: 1rem; border: 2px solid #e2e8f0; margin-top: 1rem; }
        .chat-message { background: white; border-radius: 0.5rem; padding: 0.75rem; margin: 0.5rem 0; border-left: 4px solid #3b82f6; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
        .radar-container { border: 2px solid #1e3a8a; border-radius: 0.5rem; padding: 0.5rem; background: #000; }
        .metric-card { background: white; border-radius: 0.5rem; padding: 1rem; box-shadow: 0 2px 4px rgba(0,0,0,0.1); border-left: 4px solid #3b82f6; }
        .banner {text-align: right; color: #9ca3af; font-size: 0.8rem;line-height: 1;margin-bottom: 1.5rem;}
    </style>
    """, unsafe_allow_html=True)
