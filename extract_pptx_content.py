"""Extract text content from PPTX files for analysis."""
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
import sys

def extract_all_text(pptx_path):
    """Extract all text from a PPTX, organized by slide."""
    slides = {}
    with zipfile.ZipFile(pptx_path, "r") as z:
        slide_files = sorted([n for n in z.namelist() 
                            if n.startswith("ppt/slides/slide") and n.endswith(".xml")])
        for sf in slide_files:
            slide_num = sf.split("slide")[-1].replace(".xml", "")
            data = z.read(sf)
            root = ET.fromstring(data)
            ns_a = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
            
            # Get text with shape context
            texts = []
            for sp in root.iter("{http://schemas.openxmlformats.org/presentationml/2006/main}sp"):
                shape_texts = []
                for t in sp.iter(f"{ns_a}t"):
                    if t.text:
                        shape_texts.append(t.text)
                if shape_texts:
                    texts.append(" ".join(shape_texts))
            
            slides[slide_num] = texts
    return slides

def extract_media_info(pptx_path):
    """List media files."""
    with zipfile.ZipFile(pptx_path, "r") as z:
        media = [(n, z.getinfo(n).file_size) for n in z.namelist() if "media" in n]
    return media

for label, path in [
    ("ISRO TEMPLATE", "[Pub] ISRO BAH 2026 _ Idea Submission Template.pptx"),
    ("SHIELD SUBMISSION", "SHIELD_ISRO_Submission.pptx"),
]:
    p = Path(path)
    if not p.exists():
        print(f"File not found: {path}")
        continue
    print(f"\n{'='*70}")
    print(f"  {label}: {path}")
    print(f"  Size: {p.stat().st_size / (1024*1024):.2f} MB")
    print(f"{'='*70}")
    
    slides = extract_all_text(p)
    for num, texts in sorted(slides.items(), key=lambda x: int(x[0])):
        print(f"\n--- Slide {num} ---")
        for t in texts:
            print(f"  {t[:200]}")
    
    media = extract_media_info(p)
    print(f"\n--- Media ({len(media)} files) ---")
    for name, size in media:
        print(f"  {name} ({size/1024:.0f} KB)")
