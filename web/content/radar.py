import streamlit as st
import plotly.graph_objects as go
from datetime import datetime
from backend.radar_data import generate_radar_data

def render_radar():
    st.markdown("### 🎯 Weather Radar - Real-time Precipitation")
    lat_grid, lon_grid, rainfall = generate_radar_data()

    fig = go.Figure()
    fig.add_trace(go.Heatmap(
        z=rainfall,
        x=lon_grid[0],
        y=lat_grid[:, 0],
        colorscale=[
            [0, 'rgba(0,0,0,0)'],
            [0.1, '#000080'],
            [0.3, '#0080FF'],
            [0.5, '#00FF00'],
            [0.7, '#FFFF00'],
            [0.8, '#FF8000'],
            [1.0, '#FF0000']
        ],
        hovertemplate='Lat: %{y:.2f}<br>Lon: %{x:.2f}<br>Rainfall: %{z:.1f} mm/hr<extra></extra>',
        name='Rainfall Intensity'
    ))

    fig.add_trace(go.Scatter(
        x=[121.0], y=[14.5],
        mode='markers+text',
        marker=dict(size=20, color='white', symbol='circle', line=dict(color='red', width=3)),
        text=['🌀 NANDO'], textposition="top center",
        textfont=dict(size=14, color='white'),
        name='Typhoon Center'
    ))

    fig.update_layout(
        title=dict(
            text="Doppler Radar - Super Typhoon NANDO<br><sub>Updated: " + datetime.now().strftime("%Y-%m-%d %H:%M UTC") + "</sub>",
            x=0.5, font=dict(color='white', size=16)
        ),
        xaxis=dict(title="Longitude", color='white', gridcolor='gray'),
        yaxis=dict(title="Latitude", color='white', gridcolor='gray'),
        plot_bgcolor='black', paper_bgcolor='black', font=dict(color='white'),
        height=500, showlegend=False
    )

    st.markdown('<div class="radar-container">', unsafe_allow_html=True)
    st.plotly_chart(fig, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)
