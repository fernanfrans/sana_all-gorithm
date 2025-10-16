from utils_web import get_predicted_data, init_supabase
import numpy as np
import plotly.graph_objects as go

# --- Load data ---
supabase_client, bucket_name_predicted = init_supabase()
predicted_data, _ = get_predicted_data(supabase_client, bucket_name_predicted)

refl_list = [np.array(d["reflectivity"]) for d in predicted_data]
lat = np.array(predicted_data[0]["coordinates"]["lat"])
lon = np.array(predicted_data[0]["coordinates"]["lon"])

# If lat/lon are 1D, meshgrid them
if lat.ndim == 1 and lon.ndim == 1:
    lat, lon = np.meshgrid(lat, lon, indexing='ij')

center_lat = float(np.mean(lat))
center_lon = float(np.mean(lon))

# --- Create frames ---
frames = [
    go.Frame(
        data=[
            go.Densitymapbox(
                lat=lat.flatten(),
                lon=lon.flatten(),
                z=refl_list[i].flatten(),
                zmin=5,
                zmax=75,
                colorscale="Turbo",
                radius=8,
                hovertemplate="Lat: %{lat:.4f}°<br>Lon: %{lon:.4f}°<br>Reflectivity: %{z:.2f} dBZ<extra></extra>"
            )
        ],
        name=str(i)
    )
    for i in range(len(refl_list))
]

# --- Initial figure ---
fig = go.Figure(
    data=frames[0].data,
    frames=frames
)

# --- Layout (with OpenStreetMap overlay, no buttons) ---
fig.update_layout(
    title="Predicted Reflectivity (Map Overlay)",
    mapbox=dict(
        style="open-street-map",  # overlay basemap
        center=dict(lat=center_lat, lon=center_lon),
        zoom=6
    ),
    margin=dict(l=0, r=0, t=40, b=0),
    sliders=[{
        "steps": [
            {
                "args": [[f.name], {"frame": {"duration": 200, "redraw": True}, "mode": "immediate"}],
                "label": str(i),
                "method": "animate"
            }
            for i, f in enumerate(frames)
        ],
        "x": 0.1,
        "y": 0.02
    }]
)

# --- Auto-play animation on load ---
fig.update_layout(
    updatemenus=[],
)

# --- Configure animation ---
fig.update(frames=frames)
fig.layout.sliders[0]['currentvalue'] = {"prefix": "Frame: ", "visible": True}

# Auto-start the animation when opened in browser
fig.show(config={"scrollZoom": True})
