import streamlit as st

def inject_styles():
    st.markdown("""
    <style>
        /* General App Layout */
        .main > div {
            padding-top: 1rem;
            background-color: #ffffff;
            color: #1e3a8a;
        }
        .stApp > header {
            background-color: transparent;
        }

        /* Header Section */
        .header-container {
            background: white;
            padding: 1rem;
            margin: -2rem -1rem 1.5rem -1rem;
            border-bottom: 3px solid #3b82f6;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }
        .header-title {
            color: #1e3a8a !important;
            font-size: 2rem;
            font-weight: 800;
            margin: 0;
        }
        .header-subtitle {
            color: #2563eb;
            font-size: 1rem;
            font-weight: 500;
            margin: 0;
        }

        /* Cards */
        .metric-card, .weather-current, .chat-message {
            background: white;
            border-radius: 1rem;
            padding: 1.25rem;
            border: 1px solid #e2e8f0;
            box-shadow: 0 3px 6px rgba(0,0,0,0.06);
            margin-bottom: 1rem;
            transition: transform 0.2s ease, box-shadow 0.2s ease;
        }
        .metric-card:hover, .weather-current:hover, .chat-message:hover {
            transform: translateY(-3px);
            box-shadow: 0 5px 10px rgba(0,0,0,0.1);
        }

        /* Weather Card Specific */
        .weather-current {
            border-left: 5px solid #3b82f6;
        }
        .weather-current h3 {
            color: #1e3a8a;
            font-weight: 700;
        }
        .weather-current p {
            margin: 0.2rem 0;
            color: #1e40af;
        }

        /* Notification Cards */
        .warning-card {
            background: linear-gradient(90deg, #b91c1c 0%, #dc2626 100%);
            color: white;
            padding: 0.75rem;
            border-radius: 0.5rem;
            margin: 0.5rem 0;
            border-left: 4px solid #fbbf24;
        }
        .advisory-card {
            background: linear-gradient(90deg, #1e3a8a 0%, #3b82f6 100%);
            color: white;
            padding: 0.75rem;
            border-radius: 0.5rem;
            margin: 0.5rem 0;
            border-left: 4px solid #fbbf24;
        }
        .info-card {
            background: linear-gradient(90deg, #0284c7 0%, #06b6d4 100%);
            color: white;
            padding: 0.75rem;
            border-radius: 0.5rem;
            margin: 0.5rem 0;
            border-left: 4px solid #fbbf24;
        }

        /* Chatbot */
        .chatbot-container {
            background: #f8fafc;
            border-radius: 0.5rem;
            padding: 1rem;
            border: 1px solid #e5e7eb;
        }
        .chat-message {
            border-left: 4px solid #3b82f6;
        }

        /* Radar Container */
        .radar-container {
            border: 2px solid #1e3a8a;
            border-radius: 0.5rem;
            padding: 0.5rem;
            background: #000;
        }

        /* Footer or Tagline */
        .banner {
            text-align: center;
            color: #6b7280;
            font-size: 0.85rem;
            margin-top: 2rem;
        }
        .banner span {
            color: #2563eb;
            font-weight: 600;
        }
    </style>
    """, unsafe_allow_html=True)
