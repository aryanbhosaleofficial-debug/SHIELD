"""
Compress SHIELD_ISRO_Submission.pptx to ≤ 5 MB.

Strategy:
1. PPTX is a ZIP archive — extract it.
2. Find all embedded images (PNG, JPEG, TIFF, BMP).
3. Compress/resize images to reduce total size.
4. Re-pack the ZIP as a valid PPTX.
"""

import os
import sys
import shutil
import zipfile
from pathlib import Path
from io import BytesIO

try:
    from PIL import Image
except ImportError:
    print("Installing Pillow...")
    os.system(f"{sys.executable} -m pip install Pillow")
    from PIL import Image

# --- Configuration ---
INPUT_PPTX = Path("SHIELD_ISRO_Submission.pptx")
OUTPUT_PPTX = Path("SHIELD_ISRO_Submission_compressed.pptx")
TARGET_SIZE_MB = 5.0
TEMP_DIR = Path("_pptx_temp")

# Image compression settings — we'll try progressively aggressive settings
COMPRESSION_PROFILES = [
    {"max_dim": 1920, "jpeg_quality": 80, "label": "Light"},
    {"max_dim": 1600, "jpeg_quality": 65, "label": "Medium"},
    {"max_dim": 1280, "jpeg_quality": 50, "label": "Aggressive"},
    {"max_dim": 1024, "jpeg_quality": 40, "label": "Heavy"},
    {"max_dim": 800,  "jpeg_quality": 30, "label": "Maximum"},
]

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".tiff", ".tif", ".bmp"}


def extract_pptx(pptx_path: Path, dest: Path):
    """Extract PPTX (ZIP) to a temp directory."""
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)
    with zipfile.ZipFile(pptx_path, "r") as z:
        z.extractall(dest)


def compress_image(img_path: Path, max_dim: int, jpeg_quality: int) -> bytes:
    """Compress a single image and return bytes."""
    img = Image.open(img_path)

    # Convert RGBA/palette to RGB for JPEG
    if img.mode in ("RGBA", "P", "LA"):
        # Keep PNGs with transparency as PNG but optimized
        if img.mode == "RGBA":
            # Check if there's actual transparency
            alpha = img.getchannel("A")
            if alpha.getextrema()[0] < 255:
                # Has real transparency — keep as optimized PNG
                img.thumbnail((max_dim, max_dim), Image.LANCZOS)
                buf = BytesIO()
                img.save(buf, format="PNG", optimize=True)
                return buf.getvalue(), ".png"

        img = img.convert("RGB")
    elif img.mode != "RGB":
        img = img.convert("RGB")

    # Resize if larger than max_dim
    img.thumbnail((max_dim, max_dim), Image.LANCZOS)

    # Save as JPEG
    buf = BytesIO()
    img.save(buf, format="JPEG", quality=jpeg_quality, optimize=True)
    return buf.getvalue(), ".jpg"


def repack_pptx(source_dir: Path, output_path: Path):
    """Re-pack the extracted directory into a valid PPTX (ZIP)."""
    if output_path.exists():
        output_path.unlink()

    with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as z:
        for root, dirs, files in os.walk(source_dir):
            for f in files:
                file_path = Path(root) / f
                arcname = file_path.relative_to(source_dir)
                z.write(file_path, arcname)


def get_size_mb(path: Path) -> float:
    return path.stat().st_size / (1024 * 1024)


def try_compress(profile: dict) -> float:
    """Apply a compression profile and return resulting size in MB."""
    max_dim = profile["max_dim"]
    quality = profile["jpeg_quality"]
    label = profile["label"]

    print(f"\n--- Trying '{label}' profile: max_dim={max_dim}, quality={quality} ---")

    # Fresh extraction each attempt
    extract_pptx(INPUT_PPTX, TEMP_DIR)

    media_dir = TEMP_DIR / "ppt" / "media"
    if not media_dir.exists():
        print("  No ppt/media directory found!")
        return get_size_mb(INPUT_PPTX)

    images = [f for f in media_dir.iterdir() if f.suffix.lower() in IMAGE_EXTENSIONS]
    print(f"  Found {len(images)} images in ppt/media/")

    total_saved = 0
    for img_path in images:
        original_size = img_path.stat().st_size
        try:
            compressed_data, new_ext = compress_image(img_path, max_dim, quality)
            new_size = len(compressed_data)

            if new_size < original_size:
                # If format changed (e.g., PNG → JPEG), we need to update references
                if new_ext != img_path.suffix.lower():
                    # Write with new extension
                    new_path = img_path.with_suffix(new_ext)
                    new_path.write_bytes(compressed_data)

                    # Update all XML references from old filename to new filename
                    old_name = img_path.name
                    new_name = new_path.name
                    update_references(TEMP_DIR, old_name, new_name)

                    # Remove old file
                    img_path.unlink()
                else:
                    img_path.write_bytes(compressed_data)

                saved = original_size - new_size
                total_saved += saved
        except Exception as e:
            print(f"  Warning: Could not compress {img_path.name}: {e}")

    print(f"  Saved {total_saved / 1024:.0f} KB from image compression")

    # Repack
    repack_pptx(TEMP_DIR, OUTPUT_PPTX)
    result_mb = get_size_mb(OUTPUT_PPTX)
    print(f"  Result: {result_mb:.2f} MB")

    return result_mb


def update_references(temp_dir: Path, old_name: str, new_name: str):
    """Update XML/rels files that reference the old image name."""
    xml_extensions = {".xml", ".rels"}
    for root, dirs, files in os.walk(temp_dir):
        for f in files:
            fp = Path(root) / f
            if fp.suffix.lower() in xml_extensions:
                try:
                    content = fp.read_text(encoding="utf-8")
                    if old_name in content:
                        content = content.replace(old_name, new_name)
                        fp.write_text(content, encoding="utf-8")
                except Exception:
                    pass


def main():
    if not INPUT_PPTX.exists():
        print(f"Error: {INPUT_PPTX} not found!")
        sys.exit(1)

    original_mb = get_size_mb(INPUT_PPTX)
    print(f"Original size: {original_mb:.2f} MB")
    print(f"Target size:   {TARGET_SIZE_MB:.2f} MB")

    for profile in COMPRESSION_PROFILES:
        result_mb = try_compress(profile)
        if result_mb <= TARGET_SIZE_MB:
            print(f"\n[OK] Success! '{profile['label']}' profile achieved {result_mb:.2f} MB")
            print(f"   Output: {OUTPUT_PPTX}")
            break
    else:
        print(f"\n[WARN] Best result: {result_mb:.2f} MB (target was {TARGET_SIZE_MB:.2f} MB)")
        print(f"   Output saved as: {OUTPUT_PPTX}")

    # Cleanup
    if TEMP_DIR.exists():
        shutil.rmtree(TEMP_DIR)

    print("\nDone!")


if __name__ == "__main__":
    main()
