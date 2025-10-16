import streamlit as st
import numpy as np
import pandas as pd
from utils_web import get_predicted_data, init_supabase
import plotly.express as px
import plotly.graph_objects as go
from streamlit_plotly_events import plotly_events

st.set_page_config(layout="wide")
st.title("🌦 Predicted Reflectivity Animation with Clickable Moving Pin")

# --- Load data ---
supabase_client, bucket_name_predicted = init_supabase()
predicted_data, _ = get_predicted_data(supabase_client, bucket_name_predicted)

# --- Prepare reflectivity and coordinates ---
refl_list = []
for data in predicted_data:
    refl = np.array(data["reflectivity"])
    refl_masked = np.ma.masked_where(refl < 5, refl)
    refl_list.append(refl_masked.filled(np.nan))

lat = np.array(predicted_data[0]["coordinates"]["lat"])
lon = np.array(predicted_data[0]["coordinates"]["lon"])

# Flatten arrays for DataFrame
flat_lat = lat.flatten()
flat_lon = lon.flatten()

# --- Create DataFrame for all frames ---
df_list = []
for t, refl in enumerate(refl_list):
    df_list.append(pd.DataFrame({
        "lat": flat_lat,
        "lon": flat_lon,
        "reflectivity": refl.flatten(),
        "time": t
    }))
df_all = pd.concat(df_list, ignore_index=True)

# --- Ask user to click ---
st.markdown("### Click on the map to place a pin:")
fig = px.density_mapbox(
    df_all,
    lat="lat",
    lon="lon",
    z="reflectivity",
    animation_frame="time",
    radius=10,
    range_color=[5, 75],
    color_continuous_scale="Turbo",
    mapbox_style="open-street-map",
    center={"lat": lat.mean(), "lon": lon.mean()},
    zoom=6,
    height=700
)

fig.update_layout(
    coloraxis_colorbar=dict(title="Reflectivity (dBZ)"),
    margin=dict(l=0, r=0, t=0, b=0)
)

clicked_points = plotly_events(fig, click_event=True, hover_event=False)

if clicked_points:
    click = clicked_points[0]
    lat_click = click["lat"]
    lon_click = click["lon"]

    # --- Find nearest grid index ---
    dist = (lat - lat_click)**2 + (lon - lon_click)**2
    i, j = np.unravel_index(dist.argmin(), lat.shape)

    val_init = refl_list[0][i, j]
    val_last = refl_list[-1][i, j]
    diff = val_last - val_init

    st.success(f"🟡 Clicked → Lat: {lat_click:.4f}, Lon: {lon_click:.4f}")
    st.write(f"Reflectivity → Initial: {val_init:.2f} dBZ, Latest: {val_last:.2f} dBZ, Difference: {diff:.2f} dBZ")

    # --- Add moving pin trace ---
    pin_frames = []
    for t in range(len(refl_list)):
        pin_frames.append(go.Frame(
            data=[go.Scattermapbox(
                lat=[lat[i, j]],
                lon=[lon[i, j]],
                mode="markers",
                marker=dict(size=12, color="red"),
                showlegend=False
            )],
            name=str(t)
        ))

    fig.add_trace(go.Scattermapbox(
        lat=[lat[i, j]],
        lon=[lon[i, j]],
        mode="markers",
        marker=dict(size=12, color="red"),
        name="Pin"
    ))

    fig.frames += pin_frames

    # --- Add animation buttons ---
    fig.update_layout(
        updatemenus=[dict(
            type="buttons",
            showactive=False,
            buttons=[
                dict(label="Play", method="animate",
                     args=[None, {"frame": {"duration": 500, "redraw": True},
                                  "fromcurrent": True}]),
                dict(label="Pause", method="animate",
                     args=[[None], {"frame": {"duration": 0, "redraw": False},
                                    "mode": "immediate"}])
            ])]
    )

st.plotly_chart(fig, use_container_width=True)
