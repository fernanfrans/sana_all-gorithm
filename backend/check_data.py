import json
import numpy as np
import matplotlib.pyplot as plt
from PIL import Image

# List your JSON files in order of prediction (e.g., +5min, +10min, ..., +120min)
json_files = [
    r"prediction_+5min.json",
    r"prediction_+10min.json",
    r"prediction_+15min.json",
    r"prediction_+20min.json",
    r"prediction_+25min.json",
    r"prediction_+30min.json",
    r"prediction_+35min.json",
    r"prediction_+40min.json",
    r"prediction_+45min.json",
    r"prediction_+50min.json",
    r"prediction_+55min.json",
    r"prediction_+60min.json",
    r"prediction_+65min.json",
    r"prediction_+70min.json",
    r"prediction_+75min.json",
    r"prediction_+80min.json",
    r"prediction_+85min.json",
    r"prediction_+90min.json",
    r"prediction_+95min.json",
    r"prediction_+100min.json",
    r"prediction_+105min.json",
    r"prediction_+110min.json",
    r"prediction_+115min.json",
    r"prediction_+120min.json"
    # add up to +120min
]

frames = []

for jf in json_files:
    with open(jf, "r") as f:
        data = json.load(f)
    refl = np.array(data["reflectivity"])
    
    # Optional: exaggerate differences for visualization
    refl_scaled = np.clip(refl, 0, 75)
    
    # Create figure
    fig, ax = plt.subplots(figsize=(6,6))
    im = ax.imshow(refl_scaled, cmap="turbo", origin="lower", vmin=0, vmax=75)
    ax.set_title(f"Predicted Reflectivity — {data['metadata']['lead_time']}")
    ax.axis('off')
    
    # Save frame to image in memory
    fig.canvas.draw()
    image = np.frombuffer(fig.canvas.tostring_rgb(), dtype='uint8')
    image = image.reshape(fig.canvas.get_width_height()[::-1] + (3,))
    frames.append(Image.fromarray(image))
    plt.close(fig)

# Save as GIF
frames[0].save(
    "predicted_reflectivity.gif",
    format="GIF",
    append_images=frames[1:],
    save_all=True,
    duration=500,  # milliseconds per frame
    loop=0
)

print("GIF created successfully!")
