import streamlit as st

def render_banner():
    st.markdown("""
    <style>
        /* Full-width banner */
        .banner {
            width: 100%;
            background: linear-gradient(90deg, #1e3a8a 0%, #3b82f6 100%);
            color: white;
            text-align: center;
            font-size: 1.15rem; /* Increased for readability */
            font-weight: 600;
            padding: 1.4rem 1rem; /* Slightly taller for balance */
            border-radius: 0.75rem;
            margin-top: 2rem;
            margin-bottom: 3.5rem;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            letter-spacing: 0.5px;
            animation: fadeIn 0.8s ease-in-out;
        }

        .banner .accent {
            color: #fde047; /* bright yellow accent */
            font-weight: 700;
        }

        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(8px); }
            to { opacity: 1; transform: translateY(0); }
        }

        /* Smooth scroll and top behavior */
        html, body, .stApp {
            scroll-behavior: smooth;
        }

        /* Responsive text scaling for small screens */
        @media (max-width: 600px) {
            .banner {
                font-size: 1rem;
                padding: 1rem 0.8rem;
            }
        }
    </style>

    <div class="banner">
        🌦️ <span class="accent">RAINLOOP</span> nowcasting data updates every 
        <span class="accent">5 minutes</span> | Radar data updates every 
        <span class="accent">6 minutes</span>
    </div>

    <script>
        // Always scroll to top on load or rerun
        window.addEventListener('load', () => window.scrollTo(0, 0));
        document.addEventListener('DOMContentLoaded', () => window.scrollTo(0, 0));
    </script>
    """, unsafe_allow_html=True)
