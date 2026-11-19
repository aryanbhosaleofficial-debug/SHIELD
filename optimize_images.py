"""Optimize images for PDF to bring total under 5MB."""
from PIL import Image
from pathlib import Path

BRAIN_DIR = Path(r"C:\Users\lalit\.gemini\antigravity-ide\brain\207d36b0-5af4-4cd4-b75d-0d283e1aff40")
OPT_DIR = Path("_optimized_assets")
OPT_DIR.mkdir(exist_ok=True)

# Optimize AI-generated images (these are the biggest)
ai_images = list(BRAIN_DIR.glob("solar_flare_hero_*.png")) + \
            list(BRAIN_DIR.glob("architecture_diagram_*.png")) + \
            list(BRAIN_DIR.glob("neupert_effect_*.png")) + \
            list(BRAIN_DIR.glob("pipeline_flow_*.png")) + \
            list(BRAIN_DIR.glob("tech_stack_visual_*.png"))

for img_path in ai_images:
    img = Image.open(img_path)
    print(f"Original: {img_path.name} - {img.size} - {img_path.stat().st_size/1024:.0f}KB")
    
    # Resize to max 1600px wide, convert to JPEG
    img.thumbnail((1600, 1600), Image.LANCZOS)
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")
    
    out_name = img_path.stem.rsplit("_", 1)[0] + ".jpg"
    out_path = OPT_DIR / out_name
    img.save(out_path, "JPEG", quality=70, optimize=True)
    print(f"  -> {out_name} - {img.size} - {out_path.stat().st_size/1024:.0f}KB")

# Also optimize the large template backgrounds
for name, path in [
    ("template_bg.jpg", Path("_pptx_assets/image2.png")),
    ("title_bg.jpg", Path("_shield_assets/image1.png")),
    ("dashboard.jpg", Path("_shield_assets/image3.jpg")),
    ("suit.jpg", Path("dashboard/public/suit_may2024.png")),
]:
    if path.exists():
        img = Image.open(path)
        print(f"Original: {path.name} - {img.size} - {path.stat().st_size/1024:.0f}KB")
        img.thumbnail((1600, 1600), Image.LANCZOS)
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
        out_path = OPT_DIR / name
        img.save(out_path, "JPEG", quality=75, optimize=True)
        print(f"  -> {name} - {img.size} - {out_path.stat().st_size/1024:.0f}KB")

print("\nDone optimizing!")
