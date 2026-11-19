"""Extract images and slide-image mappings from the PPTX."""
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
import os

PPTX = "[Pub] ISRO BAH 2026 _ Idea Submission Template.pptx"
OUT_DIR = Path("_pptx_assets")
OUT_DIR.mkdir(exist_ok=True)

NS_R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
NS_P = "http://schemas.openxmlformats.org/presentationml/2006/main"

with zipfile.ZipFile(PPTX, "r") as z:
    # Extract all media
    for name in z.namelist():
        if "media" in name:
            data = z.read(name)
            out_path = OUT_DIR / Path(name).name
            out_path.write_bytes(data)
            print(f"Extracted: {out_path} ({len(data)/1024:.0f} KB)")
    
    # Map slides to their images via .rels files
    slide_files = sorted([n for n in z.namelist() if n.startswith("ppt/slides/slide") and n.endswith(".xml")])
    
    for sf in slide_files:
        slide_num = sf.split("slide")[-1].replace(".xml", "")
        rels_path = f"ppt/slides/_rels/slide{slide_num}.xml.rels"
        
        print(f"\n--- Slide {slide_num} ---")
        if rels_path in z.namelist():
            rels_data = z.read(rels_path)
            rels_root = ET.fromstring(rels_data)
            for rel in rels_root:
                target = rel.get("Target", "")
                rel_type = rel.get("Type", "").split("/")[-1]
                if "image" in target.lower() or "media" in target.lower():
                    print(f"  Image: {target} (type: {rel_type})")

# Also extract from SHIELD submission
SHIELD_PPTX = "SHIELD_ISRO_Submission.pptx"
SHIELD_OUT = Path("_shield_assets")
SHIELD_OUT.mkdir(exist_ok=True)

with zipfile.ZipFile(SHIELD_PPTX, "r") as z:
    for name in z.namelist():
        if "media" in name:
            data = z.read(name)
            out_path = SHIELD_OUT / Path(name).name
            out_path.write_bytes(data)
            print(f"Extracted: {out_path} ({len(data)/1024:.0f} KB)")
    
    slide_files = sorted([n for n in z.namelist() if n.startswith("ppt/slides/slide") and n.endswith(".xml")])
    for sf in slide_files:
        slide_num = sf.split("slide")[-1].replace(".xml", "")
        rels_path = f"ppt/slides/_rels/slide{slide_num}.xml.rels"
        print(f"\n--- SHIELD Slide {slide_num} ---")
        if rels_path in z.namelist():
            rels_data = z.read(rels_path)
            rels_root = ET.fromstring(rels_data)
            for rel in rels_root:
                target = rel.get("Target", "")
                if "image" in target.lower() or "media" in target.lower():
                    print(f"  Image: {target}")
