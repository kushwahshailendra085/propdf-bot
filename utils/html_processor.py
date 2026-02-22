"""
html_processor.py
-----------------
Converts HTML files to A4 PDF using Playwright and then applies the same 
watermarking and linking logic from pdf_processor.py.
"""

import asyncio
from pathlib import Path
from playwright.async_api import async_playwright
from utils.pdf_processor import process_pdf

async def convert_html_to_pdf(html_path: str, output_pdf_path: str) -> str:
    """
    Converts HTML file to a high-quality A4 PDF with background graphics.
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        # Open the local HTML file using proper URI formatting
        html_src = Path(html_path)
        uri = html_src.absolute().as_uri()
        await page.goto(uri, wait_until="networkidle")
        
        # Emulate print media for better layout
        await page.emulate_media(media="print")
        
        # Generate PDF (A4 size, include backgrounds)
        await page.pdf(
            path=output_pdf_path,
            format="A4",
            print_background=True,
            margin={"top": "0px", "right": "0px", "bottom": "0px", "left": "0px"}
        )
        
        await browser.close()
    return output_pdf_path

async def process_html(input_html_path: str, branding_type: str = "topper_view") -> tuple[str, str]:
    """
    1. Converts HTML to a temporary PDF.
    2. Applies ProPDF/TopperView watermarks and links to that PDF.
    3. Returns the final path and promo caption.
    """
    html_src = Path(input_html_path)
    # Temporary PDF name
    temp_pdf_name = html_src.parent / f"temp_{html_src.stem}.pdf"
    
    # Step 1: HTML -> PDF
    await convert_html_to_pdf(str(html_src), str(temp_pdf_name))
    
    # Step 2: Use existing pdf_processor to apply all rules
    # This will handle renaming, watermarking, and promotional text
    final_pdf_path, promo = process_pdf(str(temp_pdf_name), branding_type=branding_type)
    
    # Step 3: Cleanup temporary PDF if it's different from final
    if temp_pdf_name.exists() and str(temp_pdf_name) != str(final_pdf_path):
        temp_pdf_name.unlink()
        
    return final_pdf_path, promo
