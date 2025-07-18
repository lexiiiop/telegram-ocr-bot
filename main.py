import logging
logging.basicConfig(level=logging.INFO)

from pyrogram import Client, filters
from config import API_ID, API_HASH, BOT_TOKEN, ADMIN_IDS
from ocr_utils import extract_text, gemini_ocr, SUPPORTED_LANGS
from pyrogram.types import Message, BotCommand, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from pyrogram.enums import ParseMode
from collections import defaultdict
import os
import asyncio
from html import escape
import time
import random
import datetime
import subprocess

# Track bot start time
BOT_START_TIME = time.time()

SATISFIED_ALTS = [
    "✅ Done", "🙌 All Good", "👍 Looks Good", "🎯 Accurate", "✅ Text is Correct", "💯 Perfect!", "✅ Satisfied"
]
USE_AI_ALTS = [
    "🤖 Ask AI", "🧠 Refine with AI", "✍️ Improve with AI", "🔍 Clarify with AI", "💬 AI Help", "🤔 Not Clear? Use AI", "🚀 Boost with AI"
]

#ADMIN_USERNAME = "@sardonic_001"
USERS_FILE = "users.txt"
LANG_PREF_FILE = "lang_prefs.txt"
STATS_FILE = "stats.txt"
AI_QUOTA_FILE = "ai_quota.txt"

# In-memory cache for user language preferences (persisted to file)
user_lang = defaultdict(lambda: "eng+hin")

# In-memory cache for file management
file_cache = {}  # key: (chat_id, message_id), value: {file_path, file_id, timestamp}
AI_QUOTA_LIMIT = 5  # per user per day

# Load language preferences from file
if os.path.exists(LANG_PREF_FILE):
    with open(LANG_PREF_FILE, "r", encoding="utf-8") as f:
        for line in f:
            parts = line.strip().split(":", 1)
            if len(parts) == 2:
                user_lang[parts[0]] = parts[1]

app = Client("ocrbot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Helper to update stats
async def update_stats(key):
    stats = {"total": 0, "satisfied": 0, "ai_used": 0}
    if os.path.exists(STATS_FILE):
        with open(STATS_FILE, "r", encoding="utf-8") as f:
            for line in f:
                k, v = line.strip().split(":")
                stats[k] = int(v)
    stats["total"] += 1 if key == "total" else 0
    stats["satisfied"] += 1 if key == "satisfied" else 0
    stats["ai_used"] += 1 if key == "ai_used" else 0
    with open(STATS_FILE, "w", encoding="utf-8") as f:
        for k, v in stats.items():
            f.write(f"{k}:{v}\n")

# Helper to manage AI quota
ai_quota = defaultdict(int)
def load_ai_quota():
    if os.path.exists(AI_QUOTA_FILE):
        with open(AI_QUOTA_FILE, "r", encoding="utf-8") as f:
            for line in f:
                uid, count = line.strip().split(":")
                ai_quota[uid] = int(count)
def save_ai_quota():
    with open(AI_QUOTA_FILE, "w", encoding="utf-8") as f:
        for uid, count in ai_quota.items():
            f.write(f"{uid}:{count}\n")
load_ai_quota()

def increment_ai_quota(user_id):
    ai_quota[str(user_id)] += 1
    save_ai_quota()

def get_ai_quota_left(user_id):
    if user_id in ADMIN_IDS:
        return float('inf')
    return max(0, AI_QUOTA_LIMIT - ai_quota.get(str(user_id), 0))

# Background cleanup for old files
def cleanup_files():
    now = time.time()
    to_delete = []
    for key, val in file_cache.items():
        if now - val["timestamp"] > 1800:  # 30 minutes
            try:
                os.remove(val["file_path"])
            except Exception:
                pass
            to_delete.append(key)
    for key in to_delete:
        del file_cache[key]
async def periodic_cleanup():
    while True:
        cleanup_files()
        await asyncio.sleep(600)  # every 10 minutes

# Async-safe file write
async def log_user(user):
    entry = f"UserID: {user.id} | First: {user.first_name} | Last: {user.last_name or ''} | Username: @{user.username or ''}\n"
    async with asyncio.Lock():
        if not os.path.exists(USERS_FILE):
            with open(USERS_FILE, "w", encoding="utf-8") as f:
                f.write(entry)
        else:
            with open(USERS_FILE, "r+", encoding="utf-8") as f:
                lines = f.readlines()
                if not any(str(user.id) in l for l in lines):
                    f.write(entry)

async def log_stats(user_id):
    async with asyncio.Lock():
        stats = {}
        if os.path.exists(STATS_FILE):
            with open(STATS_FILE, "r", encoding="utf-8") as f:
                for line in f:
                    uid, count = line.strip().split(":")
                    stats[uid] = int(count)
        stats[str(user_id)] = stats.get(str(user_id), 0) + 1
        with open(STATS_FILE, "w", encoding="utf-8") as f:
            for uid, count in stats.items():
                f.write(f"{uid}:{count}\n")

async def save_lang_pref(user_id, lang):
    user_lang[str(user_id)] = lang
    async with asyncio.Lock():
        with open(LANG_PREF_FILE, "w", encoding="utf-8") as f:
            for uid, l in user_lang.items():
                f.write(f"{uid}:{l}\n")

async def set_commands(client):
    await client.set_bot_commands([
        BotCommand("start", "Start the bot"),
        BotCommand("ocr", "Extract text from image"),
        BotCommand("help", "How to use the bot"),
        BotCommand("lang", "Set OCR language"),
        BotCommand("langlist", "List supported OCR languages"),
    ], language_code="en")
    await client.set_bot_commands([
        BotCommand("start", "बॉट शुरू करें"),
        BotCommand("ocr", "चित्र से टेक्स्ट निकालें"),
        BotCommand("help", "बॉट का उपयोग कैसे करें"),
        BotCommand("lang", "OCR भाषा सेट करें"),
        BotCommand("langlist", "समर्थित भाषाओं की सूची"),
    ], language_code="hi")

def get_media_file_id(msg):
    print("DEBUG: msg object =", msg)
    if getattr(msg, "photo", None):
        print("DEBUG: Detected msg.photo")
        return msg.photo.file_id
    elif getattr(msg, "document", None):
        print(f"DEBUG: Detected document with mime_type = {msg.document.mime_type}")
        if msg.document.mime_type and msg.document.mime_type.startswith("image/"):
            return msg.document.file_id
        else:
            print("DEBUG: Document is not an image")
    elif getattr(msg, "sticker", None):
        print("DEBUG: Detected sticker")
        return msg.sticker.file_id
    else:
        print("DEBUG: No image, document, or sticker found")
    return None

@app.on_message(filters.command("start"))
async def start_handler(client, message):
    # Start cleanup task if not already running
    if not hasattr(app, "_cleanup_task"):
        app._cleanup_task = asyncio.create_task(periodic_cleanup())
    await message.reply(
        "<b>👋 Hi! I'm your OCR bot.</b>\n\n"
        "Send me an image (in group or private) and I’ll extract the text from it.\n\n"
        "<b>Commands:</b>\n"
        "<code>/ocr</code> - Extract text from image (just send an image)\n"
        "<code>/lang &lt;lang&gt;</code> - Set OCR language (e.g., eng, hin, eng+hin)\n"
        "<code>/langlist</code> - List supported OCR languages\n"
        "<code>/help</code> - How to use the bot\n",
        parse_mode=ParseMode.HTML
    )

# OCR handler with inline buttons
@app.on_message((filters.command("ocr") & (filters.group | filters.private)))
async def handle_ocr(client, message: Message):
    media_msg = None
    # Check if the command message itself has media
    if message.photo or (message.document and getattr(message.document, 'mime_type', '').startswith('image/')) or message.sticker:
        media_msg = message
    # If not, check if it's a reply to a media message
    elif message.reply_to_message:
        m = message.reply_to_message
        if m.photo or (m.document and getattr(m.document, 'mime_type', '').startswith('image/')) or m.sticker:
            media_msg = m

    if not media_msg:
        await message.reply("⚠️ Please send or reply to an image (photo/document/sticker).")
        return

    # Debug info
    print("Media message found!")
    print("Message ID:", media_msg.id)
    print("Media types:", {
        "photo": bool(media_msg.photo),
        "document": bool(media_msg.document),
        "sticker": bool(media_msg.sticker)
    })

    # Download the media
    downloading = await message.reply("📥 Downloading image...")
    file_path = await media_msg.download(file_name="ocr_image")
    print("Downloaded to:", file_path)

    # OCR processing
    lang = user_lang.get(str(message.from_user.id), None)
    await log_user(message.from_user)
    await log_stats(message.from_user.id)
    await downloading.edit(f"🔍 Running OCR (lang: {lang or 'auto-detect'})...")
    try:
        text = extract_text(file_path, lang=lang)
    except Exception as e:
        text = f"OCR error: {str(e)}"
    await downloading.edit("📤 Sending result...")
    if not text.strip():
        text = "No text found."
    if len(text) > 3800:
        text = text[:3800] + "\n...truncated"
    escaped_text = escape(text)
    reply_text = (
        "<b>📝 Extracted Text:</b>\n\n"
        f"<pre>{escaped_text}</pre>\n"
        "<i>⚠️ This is auto-detected text. OCR may make mistakes.</i>"
    )
    sat_label = random.choice(SATISFIED_ALTS)
    ai_label = random.choice(USE_AI_ALTS)
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(sat_label, callback_data=f"satisfies|{message.chat.id}|{message.id}"),
            InlineKeyboardButton(ai_label, callback_data=f"useai|{message.chat.id}|{message.id}")
        ]
    ])
    await message.reply(reply_text, reply_to_message_id=message.id, parse_mode=ParseMode.HTML, reply_markup=keyboard)
    # Cache file info for 30min or until satisfied
    file_cache[(message.chat.id, message.id)] = {"file_path": file_path, "file_id": getattr(media_msg, 'file_id', None), "timestamp": time.time(), "ocr_text": text}
    await downloading.delete()
    await update_stats("total")

# OCR handler for direct media in private chats
@app.on_message(filters.private & (filters.photo | filters.document | filters.sticker))
async def handle_private_media_ocr(client, message: Message):
    media_msg = message
    # Only process documents if they are images
    if media_msg.document and not (getattr(media_msg.document, 'mime_type', '').startswith('image/')):
        return  # Not an image document, ignore
    # Debug info
    print("Private media message found!")
    print("Message ID:", media_msg.id)
    print("Media types:", {
        "photo": bool(media_msg.photo),
        "document": bool(media_msg.document),
        "sticker": bool(media_msg.sticker)
    })
    # Download the media
    downloading = await message.reply("📥 Downloading image...")
    file_path = await media_msg.download(file_name="ocr_image")
    print("Downloaded to:", file_path)
    # OCR processing
    lang = user_lang.get(str(message.from_user.id), None)
    await log_user(message.from_user)
    await log_stats(message.from_user.id)
    await downloading.edit(f"🔍 Running OCR (lang: {lang or 'auto-detect'})...")
    try:
        text = extract_text(file_path, lang=lang)
    except Exception as e:
        text = f"OCR error: {str(e)}"
    await downloading.edit("📤 Sending result...")
    if not text.strip():
        text = "No text found."
    if len(text) > 3800:
        text = text[:3800] + "\n...truncated"
    escaped_text = escape(text)
    reply_text = (
        "<b>📝 Extracted Text:</b>\n\n"
        f"<pre>{escaped_text}</pre>\n"
        "<i>⚠️ This is auto-detected text. OCR may make mistakes.</i>"
    )
    sat_label = random.choice(SATISFIED_ALTS)
    ai_label = random.choice(USE_AI_ALTS)
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(sat_label, callback_data=f"satisfies|{message.chat.id}|{message.id}"),
            InlineKeyboardButton(ai_label, callback_data=f"useai|{message.chat.id}|{message.id}")
        ]
    ])
    await message.reply(reply_text, reply_to_message_id=message.id, parse_mode=ParseMode.HTML, reply_markup=keyboard)
    # Cache file info for 30min or until satisfied
    file_cache[(message.chat.id, message.id)] = {"file_path": file_path, "file_id": getattr(media_msg, 'file_id', None), "timestamp": time.time(), "ocr_text": text}
    await downloading.delete()
    await update_stats("total")

# Callback handler for inline buttons
@app.on_callback_query()
async def handle_callback(client, callback_query: CallbackQuery):
    data = callback_query.data
    parts = data.split("|")
    action = parts[0]
    chat_id = int(parts[1])
    msg_id = int(parts[2])
    cache_key = (chat_id, msg_id)
    file_info = file_cache.get(cache_key)
    if action == "satisfies":
        await update_stats("satisfied")
        await callback_query.answer("Thank you for your feedback!", show_alert=True)
        await callback_query.message.edit_reply_markup(None)
        # Delete file immediately
        if file_info:
            try:
                os.remove(file_info["file_path"])
            except Exception:
                pass
            del file_cache[cache_key]
    elif action == "useai":
        user_id = callback_query.from_user.id
        is_admin = user_id in ADMIN_IDS
        quota_left = get_ai_quota_left(user_id)
        if not is_admin and quota_left <= 0:
            await callback_query.answer("AI quota exceeded. Please try again later.", show_alert=True)
            return
        await update_stats("ai_used")
        await callback_query.answer("Processing with Gemini AI...", show_alert=True)
        await callback_query.message.edit_reply_markup(None)
        if not file_info:
            await callback_query.message.reply("Image expired or not found. Please resend.")
            return
        # Delete the original OCR-only message
        try:
            await callback_query.message.delete()
        except Exception:
            pass
        # Show loading message
        loading_msg = await client.send_message(
            chat_id=callback_query.message.chat.id,
            text="<i>Processing with Gemini AI...</i>",
            parse_mode=ParseMode.HTML
        )
        try:
            gemini_text = gemini_ocr(file_info["file_path"])
        except Exception as e:
            await loading_msg.edit(f"<b>Gemini AI error:</b> {e}")
            return
        if not gemini_text.strip():
            gemini_text = "No text found."
        # Show both results in two boxes
        MAX_BOX_LEN = 1800
        ocr_text = file_info['ocr_text']
        if len(ocr_text) > MAX_BOX_LEN:
            ocr_text = ocr_text[:MAX_BOX_LEN] + "\n...truncated"
        if len(gemini_text) > MAX_BOX_LEN:
            gemini_text = gemini_text[:MAX_BOX_LEN] + "\n...truncated"
        ocr_box = f"<b>📝 Extracted Text:</b>\n<pre>{escape(ocr_text)}</pre>"
        gemini_box = f"<b>🤖 Gemini AI Processed Text:</b>\n<pre>{escape(gemini_text)}</pre>"
        if is_admin:
            quota_display = "∞"
        else:
            quota_left -= 1
            increment_ai_quota(user_id)
            quota_display = str(quota_left)
        await loading_msg.edit(
            f"{ocr_box}\n\n{gemini_box}\n\n<i>⚠️ This is auto-detected text. OCR may make mistakes.</i>\n"
            f"<b>AI requests left today:</b> {quota_display}"
        )
        # Keep file until satisfied or timeout

@app.on_message(filters.command("lang"))
async def set_lang(_, message):
    if len(message.command) < 2:
        await message.reply("Usage: /lang eng, /lang hin, or /lang eng+hin")
        return
    lang = message.text.split(" ", 1)[1].strip()
    await save_lang_pref(message.from_user.id, lang)
    await message.reply(f"OCR language set to: {lang}")

@app.on_message(filters.command("langlist"))
async def langlist(_, message):
    langs = ', '.join(SUPPORTED_LANGS)
    await message.reply(f"Supported OCR languages:\n{langs}")

@app.on_message(filters.command("db"))
async def send_db(client, message):
    if message.from_user.id not in ADMIN_IDS:
        return
    if os.path.exists(USERS_FILE):
        await client.send_document(
            chat_id=message.chat.id,
            document=USERS_FILE,
            caption="User database (admin only)"
        )
    else:
        await message.reply("No user database found.")

# Update /stats to show satisfaction and AI usage rates
@app.on_message(filters.command("stats"))
async def stats(_, message):
    stats = {"total": 0, "satisfied": 0, "ai_used": 0}
    if os.path.exists(STATS_FILE):
        with open(STATS_FILE, "r", encoding="utf-8") as f:
            for line in f:
                k, v = line.strip().split(":")
                stats[k] = int(v)
    total = stats["total"]
    satisfied = stats["satisfied"]
    ai_used = stats["ai_used"]
    satisfied_pct = (satisfied / total * 100) if total else 0
    ai_used_pct = (ai_used / total * 100) if total else 0
    await message.reply(
        f"<b>Bot Usage Stats:</b>\n"
        f"Total OCR requests: <b>{total}</b>\n"
        f"Satisfied: <b>{satisfied}</b> ({satisfied_pct:.1f}%)\n"
        f"Used AI: <b>{ai_used}</b> ({ai_used_pct:.1f}%)\n",
        parse_mode=ParseMode.HTML
    )

@app.on_message(filters.command("broadcast"))
async def broadcast(_, message):
    if message.from_user.id not in ADMIN_IDS:
        return
    if len(message.command) < 2:
        await message.reply("Usage: /broadcast <message>")
        return
    text = message.text.split(" ", 1)[1]
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            for line in f:
                uid = line.split("|")[0].replace("UserID:", "").strip()
                try:
                    await app.send_message(int(uid), text)
                except Exception:
                    pass
        await message.reply("Broadcast sent.")
    else:
        await message.reply("No users to broadcast to.")

@app.on_message(filters.command("help"))
async def help(_, message):
    await message.reply(
        "<b>How to use the OCR Bot:</b>\n\n"
        "1. <b>Send an image</b> — I’ll extract the text and reply.\n"
        "2. <b>Change OCR language</b> — Use <code>/lang &lt;lang&gt;</code> (e.g., <code>/lang eng</code>, <code>/lang hin</code>, <code>/lang eng+hin</code>).\n"
        "3. <b>See supported languages</b> — Use <code>/langlist</code>.\n\n"
        "<b>Commands:</b>\n"
        "<code>/ocr</code> - Extract text from image (just send an image)\n"
        "<code>/lang &lt;lang&gt;</code> - Set OCR language (e.g., eng, hin, eng+hin)\n"
        "<code>/langlist</code> - List supported OCR languages\n"
        "<code>/help</code> - How to use the bot\n"
        "<i>⚠️ This is auto-detected text. OCR may make mistakes.</i>"
        , parse_mode=ParseMode.HTML
    )

@app.on_message(filters.command("ping"))
async def ping_handler(client, message: Message):
    start = time.time()
    sent = await message.reply("Pinging...")
    latency = (time.time() - start) * 1000
    uptime = str(datetime.timedelta(seconds=int(time.time() - BOT_START_TIME)))
    await sent.edit(f"🏓 Pong!\n<b>Latency:</b> <code>{latency:.0f} ms</code>\n<b>Uptime:</b> <code>{uptime}</code>", parse_mode=ParseMode.HTML)

@app.on_message(filters.command("sysd"))
async def sysd_handler(client, message: Message):
    if message.from_user.id not in ADMIN_IDS:
        await message.reply("❌ You are not authorized to use this command.")
        return
    try:
        proc = await asyncio.create_subprocess_exec(
            "neofetch", "--stdout",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await proc.communicate()
        if proc.returncode != 0:
            await message.reply(f"❌ neofetch error:\n<code>{stderr.decode().strip()}</code>", parse_mode=ParseMode.HTML)
            return
        output = stdout.decode().strip()
        if len(output) > 4000:
            output = output[:4000] + "\n...truncated"
        await message.reply(f"<b>System Info:</b>\n<pre>{escape(output)}</pre>", parse_mode=ParseMode.HTML)
    except Exception as e:
        await message.reply(f"❌ Error running neofetch:\n<code>{e}</code>", parse_mode=ParseMode.HTML)

if __name__ == "__main__":
    app.run() 