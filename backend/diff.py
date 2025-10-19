import json
import numpy as np
import matplotlib.pyplot as plt
import contextily as ctx
from pyproj import Transformer
from matplotlib.colors import LogNorm
import matplotlib.ticker as mticker
import matplotlib.animation as animation

# --- Two JSON files ---
initial_json_path = r"C:\Users\Administrator\DATA SCIENTIST\sana_all-gorithm\sana_all-gorithm\backend\tryprediction_+5min.json"
last_json_path    = r"C:\Users\Administrator\DATA SCIENTIST\sana_all-gorithm\sana_all-gorithm\backend\tryprediction_+100min.json"
json_paths = [initial_json_path, last_json_path]

# --- Load reflectivity arrays ---
refl_list = []
lead_times = []

for path in json_paths:
    with open(path, "r") as f:
        data = json.load(f)
    refl = np.array(data["reflectivity"])
    refl_masked = np.ma.masked_where(refl < 5, refl)
    refl_list.append(refl_masked)
    lead_times.append(data["metadata"]["lead_time"])

# Coordinates from first file
lat = np.array(data["coordinates"]["lat"])
lon = np.array(data["coordinates"]["lon"])

# Convert to Web Mercator
transformer = Transformer.from_crs("epsg:4326", "epsg:3857", always_xy=True)
x, y = transformer.transform(lon, lat)
extent = [x.min(), x.max(), y.min(), y.max()]

# --- Setup figure ---
fig, ax = plt.subplots(figsize=(12, 10))
im = ax.imshow(
    refl_list[0],
    extent=extent,
    origin="lower",
    cmap="turbo",
    norm=LogNorm(vmin=5, vmax=75),
    alpha=0.7,
    interpolation='bilinear'
)

# Add basemap
try:
    ctx.add_basemap(ax, source=ctx.providers.OpenStreetMap.Mapnik, zoom=9)
except Exception as e:
    print(f"Basemap error: {e}")

ax.set_xlim(extent[0], extent[1])
ax.set_ylim(extent[2], extent[3])

# --- Convert ticks to lat/lon ---
inv_transformer = Transformer.from_crs("epsg:3857", "epsg:4326", always_xy=True)
def x_to_lon(xval): return inv_transformer.transform(xval, y.min())[0]
def y_to_lat(yval): return inv_transformer.transform(x.min(), yval)[1]

ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda xval, _: f"{x_to_lon(xval):.2f}°"))
ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda yval, _: f"{y_to_lat(yval):.2f}°"))

# Colorbar
cbar = plt.colorbar(im, ax=ax, label="Reflectivity (dBZ)", shrink=0.7, pad=0.02)
ax.set_aspect('equal', adjustable='box')
ax.grid(True, alpha=0.3, linestyle='--')

# --- Find nearest index ---
def find_nearest_index(lat_array, lon_array, lat_point, lon_point):
    dist = (lat_array - lat_point)**2 + (lon_array - lon_point)**2
    return np.unravel_index(dist.argmin(), lat_array.shape)

# --- Keep pin info ---
pin_coords = None  # Stores last clicked location (xdata, ydata)
pin_marker = None  # Matplotlib marker object

# --- Click event ---
def onclick(event):
    global pin_coords
    if event.inaxes != ax:
        return
    
    # Store clicked coordinates
    pin_coords = (event.xdata, event.ydata)
    
    # Convert to lat/lon
    lon_click, lat_click = inv_transformer.transform(event.xdata, event.ydata)
    i, j = find_nearest_index(lat, lon, lat_click, lon_click)
    
    val_init = refl_list[0][i, j]
    val_last = refl_list[1][i, j]
    
    # Handle masked values
    val_init_str = f"{val_init:.2f}" if not np.ma.is_masked(val_init) else "--"
    val_last_str = f"{val_last:.2f}" if not np.ma.is_masked(val_last) else "--"
    diff_str = f"{(val_last - val_init):.2f}" if (not np.ma.is_masked(val_init) and not np.ma.is_masked(val_last)) else "--"
    
    print(f"🟡 Clicked → Lat: {lat_click:.4f}, Lon: {lon_click:.4f}")
    print(f"Reflectivity → initial: {val_init_str} dBZ, later: {val_last_str} dBZ")
    print(f"Difference: {diff_str} dBZ")
    
    fig.canvas.draw()

fig.canvas.mpl_connect('button_press_event', onclick)

# --- Animation update function ---
def update(frame):
    global pin_marker
    im.set_data(refl_list[frame])
    ax.set_title(f"Predicted Reflectivity — {lead_times[frame]}", fontsize=14, fontweight='bold')
    
    # Draw or update pin if clicked
    if pin_coords is not None:
        if pin_marker is None:
            pin_marker, = ax.plot([pin_coords[0]], [pin_coords[1]], marker='o', color='red', markersize=12, zorder=10)
        else:
            pin_marker.set_data([pin_coords[0]], [pin_coords[1]])
    
    return [im] + ([pin_marker] if pin_marker else [])

# --- Create GIF ---
ani = animation.FuncAnimation(fig, update, frames=2, blit=True)
ani.save(r"C:\Users\Administrator\DATA SCIENTIST\sana_all-gorithm\sana_all-gorithm\backend\reflectivity_twoframes_with_pin.gif",
         writer="pillow", fps=1)

plt.show()
