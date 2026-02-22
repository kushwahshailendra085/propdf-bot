"""
config.py
---------
Central configuration for ProPDF & TopperView Bot.
Change settings here to update the bot's behavior.
"""

from pathlib import Path

# ─── Bot Security & IDs ──────────────────────────────────────────────────────
BOT_TOKEN = "7730777263:AAEsJDHQa_Cj5zqmsusZvWxVhLzRfgenHgo"
ALLOWED_USERS = [2141959380, 8581064143]

# ─── Directories ─────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent
DOWNLOAD_DIR = BASE_DIR / "downloads"

# ─── Watermark Settings (Shared) ─────────────────────────────────────────────
WATERMARK_OPACITY = 0.30  # 30%
WATERMARK_SIZE = 60
WATERMARK_ANGLE = 45
WATERMARK_COLOR = (0, 0, 0) # Black

# ─── Branding Configurations ─────────────────────────────────────────────────
BRANDING = {
    "pro_pdf": {
        "watermark": "Join - Pro PDF",
        "link": "https://t.me/ProPDF",
        "prefix": "By @ProPDF - ",
        "promo": "🔥 *PDF shared via @ProPDF*\n Share this PDF with your friends, groups & channels!",
        "caption": "" # No specific caption for ProPDF photos
    },
    "topper_view": {
        "watermark": "Topper View",
        "link": "https://t.me/TopperView",
        "prefix": "By @TopperView - ",
        "promo": "🔥 Join - @TopperView ✅❤️\nGive One 👉 ❤️ Like Share And Follow For More amazing content!",
        "caption": (
            "Join - @TopperView ✅❤️\n\n"
            "Give One 👉 ❤️ Like Share And Follow For More such amazing content \n\n"
            "https://t.me/TopperView"
        )
    }
}

# ─── Network Settings ────────────────────────────────────────────────────────
# Increased timeouts for large file support
TIMEOUT_READ = 300
TIMEOUT_WRITE = 600
TIMEOUT_CONNECT = 60

# ─── Image Specific ─────────────────────────────────────────────────────────
IMAGE_STROKE_WIDTH = 2
IMAGE_STROKE_COLOR = (255, 255, 255, 77) # White with 30% alpha
