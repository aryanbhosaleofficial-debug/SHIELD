import re

with open('build_submission_pdf.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Update global colors
content = content.replace('BODY_TEXT = HexColor("#000000")       # Solid black for max readability', 'BODY_TEXT = HexColor("#FFFFFF")       # White for dark background')
content = content.replace('DESC_TEXT = HexColor("#222222")       # Very dark gray for descriptions', 'DESC_TEXT = HexColor("#e2e8f0")       # Light gray for dark background')
content = content.replace('color = BLACK', 'color = WHITE')

# 2. Page 3 USPs (dark bg) -> BODY_TEXT
# No change needed because it uses BODY_TEXT, which is now WHITE

# 3. Page 4 Key Features Cards (light bg) -> Need dark text
content = content.replace("text_color = BODY_TEXT", "text_color = HexColor('#1f2937')", 1)
content = content.replace("textColor=DESC_TEXT", "textColor=HexColor('#6b7280')", 1)

# 4. Page 5 Stages (dark bg)
content = content.replace('draw_text(c, line, sx + 10, stage_y + stage_h - 28 - j*11, FONT_REG, 8, DESC_TEXT)', 'draw_text(c, line, sx + 10, stage_y + stage_h - 28 - j*11, FONT_REG, 8, HexColor("#e2e8f0"))')

# 5. Page 6 Dashboard (subtitle on dark bg)
content = content.replace('FONT_REG, 10, DESC_TEXT, leading=13)', 'FONT_REG, 10, HexColor("#e2e8f0"), leading=13)')
# Page 6 metrics label (light bg)
content = content.replace('draw_text(c, label, right_x + 12, my + 8, FONT_REG, 8, DESC_TEXT)', 'draw_text(c, label, right_x + 12, my + 8, FONT_REG, 8, HexColor("#6b7280"))')

# 6. Page 7 Architecture (dark bg) -> uses text_color
content = content.replace("text_color = BODY_TEXT", "text_color = HexColor('#FFFFFF')", 1)

# 7. Page 8 Technologies (dark bg) -> uses text_color and DESC_TEXT
content = content.replace("text_color = BODY_TEXT", "text_color = HexColor('#FFFFFF')", 1)
content = content.replace('draw_text(c, f"  --  {tech_desc}", cx + 22 + name_w, ty, FONT_REG, 9, DESC_TEXT)', 'draw_text(c, f"  --  {tech_desc}", cx + 22 + name_w, ty, FONT_REG, 9, HexColor("#e2e8f0"))')

# 8. Page 9 Cost/Roadmap (light bg) -> uses text_color and DESC_TEXT
content = content.replace("text_color = BODY_TEXT", "text_color = HexColor('#1f2937')", 1)
content = content.replace('draw_text(c, line, right_x + 22, ry - 12 - j*12, FONT_REG, 8.5, DESC_TEXT)', 'draw_text(c, line, right_x + 22, ry - 12 - j*12, FONT_REG, 8.5, HexColor("#6b7280"))')

with open('build_submission_pdf.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("Updated text colors for perfect readability!")
