"""Fix slide 3 - enlarge text box and increase font size."""
from pptx import Presentation
from pptx.util import Pt, Emu
from pptx.enum.text import PP_ALIGN

prs = Presentation(r"d:\Project\SHIELD\SHIELD\SHIELD_ISRO_Submission.pptx")

slide3 = list(prs.slides)[2]
for shape in slide3.shapes:
    if shape.has_text_frame and 'Opportunity' in shape.text_frame.text:
        # Expand the text box to fill the available content area
        shape.top = Emu(863550)       # Keep same top
        shape.left = Emu(311700)      # Keep same left
        shape.width = Emu(8520600)    # Wider to match slide 1 text boxes
        shape.height = Emu(3800000)   # Much taller (~4.15 inches)
        
        tf = shape.text_frame
        tf.word_wrap = True
        
        # Clear existing paragraphs
        while len(tf.paragraphs) > 1:
            p = tf.paragraphs[-1]._p
            p.getparent().remove(p)
        
        # Rewrite with bigger font
        lines = [
            ("Opportunity:", True, Pt(18)),
            ("", False, Pt(10)),
            ("How different is it from existing ideas?", True, Pt(15)),
            ("Unlike most teams using NOAA's American GOES data, S.H.I.E.L.D. is built entirely on India's own Aditya-L1 mission. We use real SoLEXS (soft X-ray) + HEL1OS (hard X-ray) dual-instrument data — enabling Neupert Effect cross-validation that is physically impossible with GOES (single-band only).", False, Pt(14)),
            ("", False, Pt(10)),
            ("How will it solve the problem?", True, Pt(15)),
            ("Our 4-stage detection pipeline (Quiet Sun → Pre-Flare → Forecast Alert → Nowcast) achieved 95.9% precision on 8,149 real GOES-validated flares over 877 days. We deliver impact advisories mapped directly to Indian assets — Gaganyaan, NavIC/GAGAN, ISRO satellites, power grids, and aviation.", False, Pt(14)),
            ("", False, Pt(10)),
            ("USP of the proposed solution:", True, Pt(15)),
            ("First system using real Aditya-L1 data (not simulated). Physics + ML hybrid approach (XGBoost, not black-box LSTM). Neupert Effect validation unique to dual X-ray instruments. Built-for-India impact mapping. Live dashboard already built & running.", False, Pt(14)),
        ]
        
        for i, (text, bold, size) in enumerate(lines):
            if i == 0:
                para = tf.paragraphs[0]
                # Clear existing runs
                for run in para.runs:
                    run.text = ""
                if para.runs:
                    r = para.runs[0]
                else:
                    r = para.add_run()
                r.text = text
            else:
                para = tf.add_paragraph()
                r = para.add_run()
                r.text = text
            
            para.alignment = PP_ALIGN.LEFT
            r.font.name = "Google Sans Medium" if bold else "Google Sans"
            r.font.size = size
            r.font.bold = bold
            try:
                from pptx.dml.color import RGBColor
                r.font.color.rgb = RGBColor(0x20, 0x27, 0x29)  # Dark text matching template
            except:
                pass
        
        print(f"  Text box resized: {shape.width/914400:.2f}x{shape.height/914400:.2f} inches")
        print(f"  Content set with Pt(14-18) fonts")

prs.save(r"d:\Project\SHIELD\SHIELD\SHIELD_ISRO_Submission.pptx")
print("\nDone! Slide 3 text is now bigger and readable.")
