import numpy as np
import xarray as xr
import matplotlib.pyplot as plt
import contextily as ctx
import geopandas as gpd
from shapely.geometry import box

# === 1. Load radar file ===
file_path = r"C:\Users\Administrator\DATA SCIENTIST\sana_all-gorithm\sana_all-gorithm\backend\KCYS_20251013_063105_V06.nc"  # change this path if needed
ds = xr.open_dataset(file_path)

print("Variables:", list(ds.data_vars))
print("Coordinates:", list(ds.coords))

# === 2. Extract reflectivity and select 2D slice ===
reflectivity = ds["reflectivity"].values

print("Reflectivity shape:", reflectivity.shape)

# If it's 4D (time, z, y, x) → take first frame
if reflectivity.ndim == 4:
    reflectivity = reflectivity[0, 0, :, :]
elif reflectivity.ndim == 3:
    reflectivity = reflectivity[0, :, :]

print("New reflectivity shape:", reflectivity.shape)

# === 3. Get coordinate info ===
x = ds["x"].values
y = ds["y"].values

# Radar origin
origin_lat = ds["origin_latitude"].values.item()
origin_lon = ds["origin_longitude"].values.item()
print(f"Radar origin: ({origin_lat}, {origin_lon})")

# === 4. Convert x/y meters to lat/lon (approximation) ===
deg_per_meter_lat = 1 / 111000
deg_per_meter_lon = 1 / (111000 * np.cos(np.radians(origin_lat)))

lons = origin_lon + x * deg_per_meter_lon
lats = origin_lat + y * deg_per_meter_lat

# === 5. Prepare reflectivity grid ===
reflectivity = np.clip(reflectivity, 0, 60)
reflectivity = np.nan_to_num(reflectivity, nan=0)

# === 6. Convert to Web Mercator ===
bbox = box(lons.min(), lats.min(), lons.max(), lats.max())
gdf = gpd.GeoDataFrame({"geometry": [bbox]}, crs="EPSG:4326")
gdf_web_mercator = gdf.to_crs(epsg=3857)

x_web = np.linspace(gdf_web_mercator.bounds.minx[0], gdf_web_mercator.bounds.maxx[0], reflectivity.shape[1])
y_web = np.linspace(gdf_web_mercator.bounds.miny[0], gdf_web_mercator.bounds.maxy[0], reflectivity.shape[0])
X, Y = np.meshgrid(x_web, y_web)

# === 7. Plot ===
fig, ax = plt.subplots(figsize=(10, 8))
im = ax.pcolormesh(X, Y, reflectivity, cmap="turbo", shading="auto")

ctx.add_basemap(ax, source=ctx.providers.OpenStreetMap.Mapnik)

plt.colorbar(im, ax=ax, label="Reflectivity (dBZ)")
ax.set_title("Radar Reflectivity (dBZ)", fontsize=14)
plt.tight_layout()
plt.show()
