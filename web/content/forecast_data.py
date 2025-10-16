from utils_web import get_predicted_data, init_supabase
import numpy as np
from pyproj import Transformer
import matplotlib.pyplot as plt
import contextily as ctx
from matplotlib.colors import LogNorm
import matplotlib.ticker as mticker
import matplotlib.animation as animation




supabase_client, bucket_name_predicted = init_supabase()
predicted_data, sorted_files = get_predicted_data(supabase_client, bucket_name_predicted)


refl_list = []
for data in predicted_data:
    refl = np.array(data["reflectivity"])
    refl_masked = np.ma.masked_where(refl < 5, refl)
    refl_list.append(refl_masked)

# Coordinates from first file
lat = np.array(predicted_data[0]["coordinates"]["lat"])
lon = np.array(predicted_data[0]["coordinates"]["lon"])

# Convert to Web Mercator
transformer = Transformer.from_crs("epsg:4326", "epsg:3857", always_xy=True)
x, y = transformer.transform(lon, lat)
extent = [x.min(), x.max(), y.min(), y.max()]

# Setup figure
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
    val_last = refl_list[-1][i, j]
    
    # Handle masked values
    val_init_str = f"{val_init:.2f}"
    val_last_str = f"{val_last:.2f}" 
    diff_str = f"{(val_last - val_init):.2f}" 
    
    print(f"🟡 Clicked → Lat: {lat_click:.4f}, Lon: {lon_click:.4f}")
    print(f"Reflectivity → initial: {val_init_str} dBZ, later: {val_last_str} dBZ")
    print(f"Difference: {diff_str} dBZ")
    
    fig.canvas.draw()

fig.canvas.mpl_connect('button_press_event', onclick)

# --- Animation update function ---
def update(frame):
    global pin_marker
    im.set_data(refl_list[frame])
    ax.set_title("Predicted Reflectivity", fontsize=14, fontweight='bold')
    
    # Draw or update pin if clicked
    if pin_coords is not None:
        if pin_marker is None:
            pin_marker, = ax.plot([pin_coords[0]], [pin_coords[1]], marker='o', color='red', markersize=12, zorder=10)
        else:
            pin_marker.set_data([pin_coords[0]], [pin_coords[1]])
    
    return [im] + ([pin_marker] if pin_marker else [])

# --- Create GIF ---
ani = animation.FuncAnimation(fig, update, frames=24, blit=True)
plt.show()

