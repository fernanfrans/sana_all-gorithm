import json
import numpy as np
import matplotlib.pyplot as plt
import contextily as ctx
from pyproj import Transformer
from matplotlib.colors import LogNorm
import matplotlib.ticker as mticker

# --- Load reflectivity JSON ---
last_json_path = r"C:\Users\Administrator\DATA SCIENTIST\sana_all-gorithm\sana_all-gorithm\backend\tryprediction_+100min.json"
initial_json_path = r"C:\Users\Administrator\DATA SCIENTIST\sana_all-gorithm\sana_all-gorithm\backend\tryprediction_+0min.json"
with open(last_json_path, "r") as f:
    data = json.load(f)

refl = np.array(data["reflectivity"])
lat = np.array(data["coordinates"]["lat"])
lon = np.array(data["coordinates"]["lon"])

print(f"Reflectivity shape: {refl.shape}")
print(f"Lat range: {lat.min():.4f} to {lat.max():.4f}")
print(f"Lon range: {lon.min():.4f} to {lon.max():.4f}")

# --- Convert all grid points to Web Mercator (EPSG:3857) ---
transformer = Transformer.from_crs("epsg:4326", "epsg:3857", always_xy=True)
x, y = transformer.transform(lon, lat)

# Compute extents for imshow
extent = [x.min(), x.max(), y.min(), y.max()]

# --- Mask reflectivity values below threshold ---
refl_masked = np.ma.masked_where(refl < 5, refl)

# --- Plot setup ---
fig, ax = plt.subplots(figsize=(12, 10))

# Plot reflectivity (with LogNorm for better contrast)
im = ax.imshow(
    refl_masked,
    extent=extent,
    origin="lower",
    cmap="turbo",
    norm=LogNorm(vmin=5, vmax=75),
    alpha=0.7,
    interpolation='bilinear',
    zorder=2
)

# Add basemap
try:
    ctx.add_basemap(
        ax,
        source=ctx.providers.OpenStreetMap.Mapnik,
        zoom=9,
        zorder=1
    )
except Exception as e:
    print(f"Basemap error: {e}")
    ax.set_xlim(extent[0], extent[1])
    ax.set_ylim(extent[2], extent[3])

# --- Convert ticks to lat/lon ---
inv_transformer = Transformer.from_crs("epsg:3857", "epsg:4326", always_xy=True)
def x_to_lon(x): return inv_transformer.transform(x, y.min())[0]
def y_to_lat(yval): return inv_transformer.transform(x.min(), yval)[1]

ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda xval, _: f"{x_to_lon(xval):.2f}°"))
ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda yval, _: f"{y_to_lat(yval):.2f}°"))

# --- Add click event to print coordinates ---
def onclick(event):
    if event.inaxes != ax:
        return
    lon_click, lat_click = inv_transformer.transform(event.xdata, event.ydata)
    print(f"🟡 Clicked → Lat: {lat_click:.4f}, Lon: {lon_click:.4f}")

fig.canvas.mpl_connect('button_press_event', onclick)

# --- Final touches ---
cbar = plt.colorbar(im, ax=ax, label="Reflectivity (dBZ)", shrink=0.7, pad=0.02)
ax.set_title(f"Predicted Reflectivity with Map Overlay — {data['metadata']['lead_time']}",
             fontsize=14, fontweight='bold')
ax.grid(True, alpha=0.3, linestyle='--', zorder=3)
ax.set_aspect('equal', adjustable='box')

plt.tight_layout()
plt.show()
