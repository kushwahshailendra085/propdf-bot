from PIL import Image, ImageDraw, ImageFont
import logging
import math
from pathlib import Path
from config import WATERMARK_ANGLE, WATERMARK_OPACITY, IMAGE_STROKE_WIDTH, IMAGE_STROKE_COLOR

logger = logging.getLogger(__name__)

def apply_watermark(input_image_path, output_image_path, text="Topper View"):
    """
    Main entry point for watermarking an image with adaptive font sizing
    and rotation defined in config.
    """
    logger.info(f"Applying adaptive text watermark '{text}' to {input_image_path}")
    
    img = Image.open(input_image_path).convert("RGBA")
    width, height = img.size
    
    # Create an overlay layer
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    
    # Load Font
    font_dir = Path(__file__).parent
    font_path_bold = font_dir / "Poppins-Bold.ttf"
    
    # Text and Color (Opacity from config)
    alpha = int(WATERMARK_OPACITY * 255)
    text_color = (0, 0, 0, alpha) 
    
    # --- Adaptive Font Sizing ---
    target_fit = min(width, height) * 0.8
    
    def get_rotated_size(f_size):
        try:
            if font_path_bold.exists():
                font = ImageFont.truetype(str(font_path_bold), f_size)
            else:
                font = ImageFont.load_default(size=f_size)
        except:
            font = ImageFont.load_default()
        
        bbox = draw.textbbox((0, 0), text, font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        
        angle_rad = math.radians(WATERMARK_ANGLE)
        cos_val = abs(math.cos(angle_rad))
        sin_val = abs(math.sin(angle_rad))
        
        rotated_w = tw * cos_val + th * sin_val
        rotated_h = tw * sin_val + th * cos_val
        return rotated_w, rotated_h

    font_size = int(target_fit * 0.15)
    
    rw, rh = get_rotated_size(font_size)
    while (rw < target_fit and rh < target_fit) and font_size < 1000:
        font_size += 5
        rw, rh = get_rotated_size(font_size)
    while (rw > target_fit or rh > target_fit) and font_size > 10:
        font_size -= 2
        rw, rh = get_rotated_size(font_size)

    try:
        if font_path_bold.exists():
            font = ImageFont.truetype(str(font_path_bold), font_size)
        else:
            font = ImageFont.load_default(size=font_size)
    except:
        font = ImageFont.load_default()

    bbox = draw.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    
    txt_img = Image.new("RGBA", (int(tw * 1.3), int(th * 2.5)), (0, 0, 0, 0))
    d_tmp = ImageDraw.Draw(txt_img)
    
    # Draw Text with stroke using config values
    d_tmp.text(
        ((txt_img.size[0]-tw)//2, (txt_img.size[1]-th)//2), 
        text, 
        font=font, 
        fill=text_color,
        stroke_width=IMAGE_STROKE_WIDTH,
        stroke_fill=IMAGE_STROKE_COLOR
    )
    
    # Rotate using angle from config
    rotated_txt = txt_img.rotate(WATERMARK_ANGLE, expand=True, resample=Image.BICUBIC)
    
    px = (width - rotated_txt.size[0]) // 2
    py = (height - rotated_txt.size[1]) // 2
    overlay.paste(rotated_txt, (px, py), rotated_txt)

    result = Image.alpha_composite(img, overlay)
    final = result.convert("RGB")
    
    if str(output_image_path).lower().endswith((".jpg", ".jpeg")):
        final.save(output_image_path, "JPEG", quality=95)
    else:
        final.save(output_image_path, "PNG")
        
    logger.info(f"Watermarked image saved: {output_image_path} (Font: {font_size})")
    return output_image_path
