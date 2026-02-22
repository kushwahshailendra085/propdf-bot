"""
pdf_processor.py
----------------
Processes PDF files with dynamic branding (ProPDF vs Topper View).
Uses PyMuPDF (fitz) for high performance.
"""

import re
import fitz  # PyMuPDF
from pathlib import Path
from config import BRANDING, WATERMARK_OPACITY, WATERMARK_SIZE, WATERMARK_ANGLE, WATERMARK_COLOR

# Regex to detect @channelname patterns
_CHANNEL_RE = re.compile(r'@[A-Za-z0-9_]+')

def process_pdf(input_path: str, branding_type: str = "pro_pdf") -> tuple[str, str]:
    """
    Process the PDF with specified branding.
    branding_type: 'pro_pdf' or 'topper_view'
    """
    brand = BRANDING.get(branding_type, BRANDING["pro_pdf"])
    
    src = Path(input_path)
    if not src.is_file():
        raise FileNotFoundError(f"File not found: {src}")

    doc = fitz.open(str(src))
    
    for page in doc:
        # Step 1: Remove existing links
        for link in page.get_links():
            if link.get("kind") == fitz.LINK_URI:
                page.delete_link(link)

        # Step 2: Add dynamic link
        page.insert_link({
            "kind": fitz.LINK_URI,
            "from": page.rect,
            "uri": brand["link"]
        })

        # Step 3: Dynamic Watermark with rotation and White Border
        text = brand["watermark"]
        font_name = "hebo"
        tw = fitz.get_text_length(text, fontname=font_name, fontsize=WATERMARK_SIZE)
        th = WATERMARK_SIZE
        
        # Center point
        cp = fitz.Point(page.rect.width / 2, page.rect.height / 2)
        
        # Matrix for rotation from config
        m = fitz.Matrix(WATERMARK_ANGLE) 
        
        # Point to start drawing text centered at cp after rotation
        start_pt = cp - fitz.Point(tw/2, -th/4) 
        
        stroke_color = (1, 1, 1) # White
        fill_color = WATERMARK_COLOR
        
        # Draw stroke (4 directions)
        for dx, dy in [(-1, -1), (1, -1), (-1, 1), (1, 1)]:
            page.insert_text(
                start_pt + fitz.Point(dx, dy),
                text,
                fontsize=WATERMARK_SIZE,
                fontname=font_name,
                color=stroke_color,
                fill_opacity=WATERMARK_OPACITY,
                morph=(cp, m),
                overlay=True
            )
            
        # Draw Main Text
        page.insert_text(
            start_pt,
            text,
            fontsize=WATERMARK_SIZE,
            fontname=font_name,
            color=fill_color,
            fill_opacity=WATERMARK_OPACITY,
            morph=(cp, m),
            overlay=True
        )

    # Step 4: Rename filename
    clean_stem = _CHANNEL_RE.sub("", src.stem)
    clean_stem = re.sub(r'[\s\-_]+$', '', clean_stem.strip())
    clean_stem = re.sub(r'\s{2,}', ' ', clean_stem).strip() or src.stem
    
    new_name = f"{brand['prefix']}{clean_stem}{src.suffix}"
    out_path = src.parent / new_name

    doc.save(str(out_path), garbage=4, deflate=True)
    doc.close()

    promo = f"📄 *{clean_stem}*\n\n{brand['promo']}"
    return str(out_path), promo
