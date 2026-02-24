"""
bot.py
------
ProPDF & Topper View Telegram Bot
Handles PDF, HTML, and Photo processing with selectable branding.
"""

import logging
import asyncio
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from collections import defaultdict

from telegram import Update, InputMediaPhoto, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes,
)

from config import (
    BOT_TOKEN, ALLOWED_USERS, DOWNLOAD_DIR, 
    TIMEOUT_READ, TIMEOUT_WRITE, TIMEOUT_CONNECT,
    BRANDING
)
from utils.pdf_processor import process_pdf
from utils.image_processor import apply_watermark
from utils.html_processor import process_html

# ─── Keep-Alive Server ────────────────────────────────────────────────────────
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(b"Bot is Running!")

def run_health_server():
    # Hugging Face Spaces provides PORT=7860, Render uses PORT=8080
    import os
    port = int(os.environ.get("PORT", 7860))
    server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
    logger.info(f"🕸️ Health check server started on port {port}")
    server.serve_forever()

def start_server():
    thread = threading.Thread(target=run_health_server, daemon=True)
    thread.start()

# ─── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# Silence frequent polling logs
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("telegram.ext").setLevel(logging.WARNING)
logging.getLogger("telegram.vendor").setLevel(logging.WARNING)

# ─── Global State ────────────────────────────────────────────────────────────
media_group_buffer = defaultdict(list)
media_group_locks = defaultdict(asyncio.Lock)

def cleanup_old_files():
    """Deletes only files older than 1 hour to keep storage clean."""
    import time
    if not DOWNLOAD_DIR.exists(): return
    now = time.time()
    for item in DOWNLOAD_DIR.iterdir():
        try:
            if item.stat().st_mtime < (now - 3600): # 1 hour
                if item.is_file(): item.unlink()
                elif item.is_dir():
                    import shutil
                    shutil.rmtree(item)
        except: pass

# ─── Handlers ─────────────────────────────────────────────────────────────────

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Welcome message."""
    user_id = update.effective_user.id
    if user_id not in ALLOWED_USERS:
        logger.warning(f"Unauthorized access attempt by {user_id}")
        return

    await update.message.reply_text(
        "👋 *Welcome to ProPDF & TopperView Bot!*\n\n"
        "📤 *PDF/HTML/Image भेजें:*\n"
        "मैं आपसे पूछूँगा कि आपको कौन सी ब्रांडिंग चाहिए (ProPDF या Topper View)।\n\n"
        "🔗 Channel: https://t.me/ProPDF",
        parse_mode="Markdown",
    )


def get_branding_keyboard(file_id: str, file_type: str):
    """Generates buttons for ProPDF vs Topper View selection."""
    keyboard = [
        [
            InlineKeyboardButton("🚀 ProPDF Branding", callback_data=f"brand:pro_pdf:{file_type}:{file_id}"),
            InlineKeyboardButton("🎓 Topper View Branding", callback_data=f"brand:topper_view:{file_type}:{file_id}"),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Entry point for PDF and HTML documents."""
    user_id = update.effective_user.id
    if user_id not in ALLOWED_USERS: return

    cleanup_old_files()

    doc = update.message.document
    f_name = doc.file_name.lower()
    
    if f_name.endswith(".pdf"):
        f_type = "pdf"
    elif f_name.endswith(".html"):
        f_type = "html"
    else:
        return

    DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
    file_dir = DOWNLOAD_DIR / doc.file_unique_id
    file_dir.mkdir(parents=True, exist_ok=True)
    file_path = file_dir / doc.file_name
    
    tg_file = await doc.get_file()
    await tg_file.download_to_drive(custom_path=str(file_path))
    
    await update.message.reply_text(
        f"📂 *File:* `{doc.file_name}`\n\n"
        "कृपया ब्रांडिंग चुनें:",
        reply_markup=get_branding_keyboard(doc.file_unique_id, f_type),
        parse_mode="Markdown"
    )
    
    context.user_data[doc.file_unique_id] = {
        "path": str(file_path),
        "name": doc.file_name,
        "type": f_type
    }


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle incoming photos."""
    user_id = update.effective_user.id
    if user_id not in ALLOWED_USERS: return

    if not update.message.media_group_id:
        cleanup_old_files()

    message = update.message
    mg_id = message.media_group_id
    DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

    if not mg_id:
        photo = message.photo[-1]
        tg_file = await photo.get_file()
        file_id = photo.file_unique_id
        path = DOWNLOAD_DIR / f"img_{file_id}.png"
        await tg_file.download_to_drive(custom_path=str(path))
        
        await message.reply_text(
            "📸 *Image प्राप्त हुई!*\nब्रैंडिंग चुनें:",
            reply_markup=get_branding_keyboard(file_id, "photo"),
            parse_mode="Markdown"
        )
        context.user_data[file_id] = {"path": str(path), "type": "photo"}
        return

    async with media_group_locks[mg_id]:
        media_group_buffer[mg_id].append(message)
        if len(media_group_buffer[mg_id]) == 1:
            async def wait_for_group():
                await asyncio.sleep(2)
                async with media_group_locks[mg_id]:
                    msgs = media_group_buffer.pop(mg_id)
                    media_group_locks.pop(mg_id)
                
                first_msg = msgs[0]
                group_key = f"group_{mg_id}"
                
                paths = []
                for m in msgs:
                    p = m.photo[-1]
                    tf = await p.get_file()
                    out = DOWNLOAD_DIR / f"img_{p.file_unique_id}.png"
                    await tf.download_to_drive(custom_path=str(out))
                    paths.append(str(out))
                
                await first_msg.reply_text(
                    f"📸 *{len(msgs)} Images प्राप्त हुईं!*\nब्रैंडिंग चुनें:",
                    reply_markup=get_branding_keyboard(group_key, "photo_group"),
                    parse_mode="Markdown"
                )
                context.user_data[group_key] = {"paths": paths, "type": "photo_group"}
            
            asyncio.create_task(wait_for_group())


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle branding selection buttons."""
    query = update.callback_query
    await query.answer()
    
    data = query.data.split(":") # brand:TYPE:FILE_TYPE:ID
    brand_choice = data[1]
    file_type = data[2]
    file_id = data[3]
    
    file_info = context.user_data.get(file_id)
    if not file_info:
        await query.edit_message_text("❌ Error: फाइल डेटा खो गया है।")
        return

    brand_cfg = BRANDING.get(brand_choice, BRANDING["pro_pdf"])
    await query.edit_message_text(f"⏳ {brand_choice.replace('_',' ').title()} ब्रांडिंग प्रोसेस हो रही है...")

    try:
        if file_type == "pdf":
            out_path, promo = process_pdf(file_info["path"], branding_type=brand_choice)
            with open(out_path, "rb") as f:
                await query.message.reply_document(document=f, caption=promo, parse_mode="Markdown")
        
        elif file_type == "html":
            out_path, promo = await process_html(file_info["path"], branding_type=brand_choice)
            with open(out_path, "rb") as f:
                await query.message.reply_document(document=f, caption=promo, parse_mode="Markdown")
        
        elif file_type == "photo":
            out_path = DOWNLOAD_DIR / f"wm_{file_id}.png"
            apply_watermark(file_info["path"], str(out_path), text=brand_cfg["watermark"])
            
            with open(out_path, "rb") as f:
                await query.message.reply_photo(photo=f, caption=brand_cfg["caption"])
            if out_path.exists(): out_path.unlink()

        elif file_type == "photo_group":
            processed_paths = []
            for p in file_info["paths"]:
                out = DOWNLOAD_DIR / f"wm_{Path(p).name}"
                apply_watermark(p, str(out), text=brand_cfg["watermark"])
                processed_paths.append(out)
            
            media = []
            for i, p in enumerate(processed_paths):
                media.append(InputMediaPhoto(open(p, "rb"), caption=brand_cfg["caption"] if i == 0 else ""))
            
            await query.message.reply_media_group(media=media)
            for m in media: m.media.close()
            for p in processed_paths: 
                if p.exists(): p.unlink()

        # Cleanup
        if "path" in file_info:
            p = Path(file_info["path"])
            if p.exists(): p.unlink()
            try: p.parent.rmdir()
            except: pass
        if "paths" in file_info:
            for p in file_info["paths"]:
                if Path(p).exists(): Path(p).unlink()
        
        del context.user_data[file_id]
        await query.message.delete()

    except Exception as exc:
        logger.exception("Error in callback handler")
        await query.message.reply_text(f"❌ Error: {exc}")


async def handle_non_supported(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    if user_id not in ALLOWED_USERS: return
    await update.message.reply_text("⚠️ मैं केवल PDF, HTML और Photos प्रोसेस कर सकता हूँ।")


def main() -> None:
    # Start the health check server for Render/UptimeRobot
    start_server()

    app = ApplicationBuilder().token(BOT_TOKEN).read_timeout(TIMEOUT_READ).write_timeout(TIMEOUT_WRITE).connect_timeout(TIMEOUT_CONNECT).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(MessageHandler(filters.Document.PDF | filters.Document.FileExtension("html"), handle_document))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle_non_supported))

    logger.info("🤖 Bot started using config.py — polling...")
    app.run_polling()

if __name__ == "__main__":
    main()
