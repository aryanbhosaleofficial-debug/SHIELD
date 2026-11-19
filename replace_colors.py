import sys
from pathlib import Path

f = Path('build_submission_pdf.py')
text = f.read_text(encoding='utf-8')
text = text.replace('HexColor("#1f2937")', 'BODY_TEXT')
text = text.replace('HexColor("#374151")', 'BODY_TEXT')
text = text.replace('HexColor("#1a1a2e")', 'BLACK')
text = text.replace('HexColor("#6b7280")', 'DESC_TEXT')
f.write_text(text, encoding='utf-8')
print("Replaced colors successfully.")
