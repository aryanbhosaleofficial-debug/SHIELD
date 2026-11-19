"""
Cross-check the repaired compressed PPTX against the original.
Compares: file size, slide count, slide layouts, text content, image count, and XML integrity.
"""

import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

ORIGINAL = Path("SHIELD_ISRO_Submission.pptx")
REPAIRED = Path("SHIELD_ISRO_Submission_compressed  -  Repaired.pptx")

NS = {
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
}


def get_size_mb(path):
    return path.stat().st_size / (1024 * 1024)


def list_zip_contents(pptx_path):
    with zipfile.ZipFile(pptx_path, "r") as z:
        return {info.filename: info.file_size for info in z.infolist()}


def get_slides(pptx_path):
    """Return list of slide XML filenames."""
    with zipfile.ZipFile(pptx_path, "r") as z:
        return sorted([n for n in z.namelist() if n.startswith("ppt/slides/slide") and n.endswith(".xml")])


def get_slide_text(pptx_path, slide_name):
    """Extract all text from a slide."""
    with zipfile.ZipFile(pptx_path, "r") as z:
        try:
            data = z.read(slide_name)
            root = ET.fromstring(data)
            texts = []
            for t in root.iter("{http://schemas.openxmlformats.org/drawingml/2006/main}t"):
                if t.text:
                    texts.append(t.text)
            return " ".join(texts)
        except Exception as e:
            return f"[ERROR: {e}]"


def get_media_files(pptx_path):
    """List all media files in ppt/media/."""
    with zipfile.ZipFile(pptx_path, "r") as z:
        return sorted([n for n in z.namelist() if n.startswith("ppt/media/")])


def check_xml_validity(pptx_path):
    """Check all XML files parse correctly."""
    errors = []
    with zipfile.ZipFile(pptx_path, "r") as z:
        for name in z.namelist():
            if name.endswith(".xml") or name.endswith(".rels"):
                try:
                    data = z.read(name)
                    ET.fromstring(data)
                except ET.ParseError as e:
                    errors.append((name, str(e)))
    return errors


def main():
    print("=" * 65)
    print("CROSS-CHECK: Original vs Repaired Compressed PPTX")
    print("=" * 65)

    # 1. File sizes
    print("\n[1] FILE SIZE")
    orig_mb = get_size_mb(ORIGINAL)
    rep_mb = get_size_mb(REPAIRED)
    print(f"    Original:  {orig_mb:.2f} MB")
    print(f"    Repaired:  {rep_mb:.2f} MB")
    print(f"    Reduction: {((orig_mb - rep_mb) / orig_mb * 100):.1f}%")
    if rep_mb <= 5.0:
        print(f"    >> PASS: Under 5 MB target")
    else:
        print(f"    >> FAIL: Still over 5 MB target")

    # 2. Slide count
    print("\n[2] SLIDE COUNT")
    orig_slides = get_slides(ORIGINAL)
    rep_slides = get_slides(REPAIRED)
    print(f"    Original:  {len(orig_slides)} slides")
    print(f"    Repaired:  {len(rep_slides)} slides")
    if len(orig_slides) == len(rep_slides):
        print(f"    >> PASS: Slide count matches")
    else:
        print(f"    >> FAIL: Slide count mismatch!")
        missing = set(orig_slides) - set(rep_slides)
        extra = set(rep_slides) - set(orig_slides)
        if missing:
            print(f"       Missing: {missing}")
        if extra:
            print(f"       Extra:   {extra}")

    # 3. Text content per slide
    print("\n[3] TEXT CONTENT (per slide)")
    all_text_match = True
    for slide in orig_slides:
        orig_text = get_slide_text(ORIGINAL, slide)
        if slide in rep_slides:
            rep_text = get_slide_text(REPAIRED, slide)
            slide_num = slide.split("slide")[-1].replace(".xml", "")
            if orig_text.strip() == rep_text.strip():
                print(f"    Slide {slide_num}: MATCH")
            else:
                print(f"    Slide {slide_num}: MISMATCH")
                # Show diff summary
                orig_words = set(orig_text.split())
                rep_words = set(rep_text.split())
                lost = orig_words - rep_words
                added = rep_words - orig_words
                if lost:
                    print(f"      Lost words: {list(lost)[:10]}...")
                if added:
                    print(f"      Added words: {list(added)[:10]}...")
                all_text_match = False
        else:
            print(f"    Slide {slide.split('slide')[-1].replace('.xml', '')}: MISSING in repaired")
            all_text_match = False

    if all_text_match:
        print("    >> PASS: All slide text matches")
    else:
        print("    >> WARN: Some text differences detected")

    # 4. Media/images
    print("\n[4] MEDIA FILES")
    orig_media = get_media_files(ORIGINAL)
    rep_media = get_media_files(REPAIRED)
    print(f"    Original:  {len(orig_media)} files")
    print(f"    Repaired:  {len(rep_media)} files")

    missing_media = set(orig_media) - set(rep_media)
    extra_media = set(rep_media) - set(orig_media)
    # Check for renamed files (e.g. .png -> .jpg)
    orig_stems = {Path(m).stem for m in orig_media}
    rep_stems = {Path(m).stem for m in rep_media}

    if missing_media:
        print(f"    Missing from repaired:")
        for m in sorted(missing_media):
            stem = Path(m).stem
            if stem in rep_stems:
                # Find the renamed version
                renamed = [r for r in rep_media if Path(r).stem == stem]
                print(f"      {m} -> renamed to {renamed}")
            else:
                print(f"      {m} (LOST)")
    if extra_media:
        print(f"    Extra in repaired:")
        for m in sorted(extra_media):
            print(f"      {m}")

    if not missing_media and not extra_media:
        print("    >> PASS: All media files present")
    elif orig_stems == rep_stems:
        print("    >> PASS: All media present (some format-converted)")
    else:
        print("    >> WARN: Media file differences detected")

    # 5. XML validity
    print("\n[5] XML VALIDITY (repaired file)")
    errors = check_xml_validity(REPAIRED)
    if not errors:
        print("    >> PASS: All XML files parse correctly")
    else:
        print(f"    >> FAIL: {len(errors)} XML parse errors:")
        for name, err in errors:
            print(f"      {name}: {err}")

    # 6. Summary
    print("\n" + "=" * 65)
    print("SUMMARY")
    print("=" * 65)
    checks = {
        "Size <= 5MB": rep_mb <= 5.0,
        "Slide count": len(orig_slides) == len(rep_slides),
        "Text content": all_text_match,
        "Media files": orig_stems == rep_stems or (not missing_media and not extra_media),
        "XML validity": len(errors) == 0,
    }
    for check, passed in checks.items():
        status = "PASS" if passed else "FAIL"
        print(f"    [{status}] {check}")

    total_pass = sum(checks.values())
    print(f"\n    {total_pass}/{len(checks)} checks passed")


if __name__ == "__main__":
    main()
