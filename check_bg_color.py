from PIL import Image
from pathlib import Path
import numpy as np

img = Image.open(Path("_optimized_assets/template_bg.jpg"))
img_np = np.array(img)
avg_color = img_np.mean(axis=(0, 1))
print(f"Average color of template background (RGB): {avg_color}")
