# Telegram OCR Bot

[![Python](https://img.shields.io/badge/python-3.9%2B-blue?logo=python)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> **Description:** Telegram OCR Bot with Gemini AI feedback, multi-language, inline feedback, stats, and Railway deploy. Supports English, Hindi, and more. Open source, modern, and user-friendly.

> **Tags:** telegram-bot, ocr, gemini, python, tesseract, ai, vision, open-source, railway, telegram, image-to-text

---

Extract text from images/screenshots sent to your Telegram bot — supports English, Hindi, and handwriting! Replies in groups and private chats. Powered by pytesseract and Gemini AI.

## Features
- Send any image, image document, or static sticker (in private chat, no /ocr needed)
- Bot replies with clean extracted text
- Inline feedback: Satisfies / Use AI (Gemini) — button names are randomized for each query
- Gemini AI fallback for advanced OCR (5 uses/day per user, unlimited for admin)
- Dual result display: Tesseract and Gemini AI results, both copyable
- Tracks user satisfaction and AI usage stats
- Auto-deletes images after feedback or 30 minutes
- Multiple admins supported (set ADMIN_IDS as comma-separated list)
- /ping command: shows bot latency and uptime
- /sysd command: shows system info using neofetch (admin only)
- Open source, ready for Railway deployment

## Tech Stack
- Python
- [Pyrogram](https://docs.pyrogram.org/) (Telegram Bot API)
- [pytesseract](https://pypi.org/project/pytesseract/)
- [Pillow](https://pillow.readthedocs.io/)
- [autocorrect](https://pypi.org/project/autocorrect/)
- [google-generativeai](https://pypi.org/project/google-generativeai/) (Gemini API)
- [neofetch](https://github.com/dylanaraps/neofetch) (for /sysd)
- [![Open in GitHub](https://img.shields.io/badge/GitHub-Repo-black?logo=github)](https://github.com/lexiiiop/telegram-ocr-bot)

## Setup

1. **Clone the repo:**
   ```bash
   git clone https://github.com/yourusername/telegram-ocr-bot.git
   cd telegram-ocr-bot/ocr_bot
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables:**
   - Copy `.env.example` to `.env` and fill in your Telegram API credentials, Gemini API key, and your Telegram user IDs as ADMIN_IDS (comma-separated):
     ```ini
     API_ID=your_api_id
     API_HASH=your_api_hash
     BOT_TOKEN=your_bot_token
     GEMINI_API_KEY=your_gemini_api_key
     ADMIN_IDS=5239100362,5239100363
     ```

4. **Install Tesseract OCR (for local use):**
   - **Linux:**
     ```bash
     sudo apt update && sudo apt install -y tesseract-ocr tesseract-ocr-all neofetch
     ```
   - **Windows:** [Download installer](https://github.com/tesseract-ocr/tesseract/wiki)
   - **Note:** neofetch is required for the /sysd command and is installed automatically in the Dockerfile.

5. **Run the bot:**
   ```bash
   python main.py
   ```

## Deploy on Railway

[![Deploy on Railway](https://railway.com/button.svg)](https://railway.com/deploy/pDBNVF?referralCode=TO-Ttj)

1. Push your code to GitHub.
2. Go to [Railway](https://railway.app) and create a new project from your repo.
3. Set environment variables (`API_ID`, `API_HASH`, `BOT_TOKEN`, `GEMINI_API_KEY`, `ADMIN_IDS`) in Railway dashboard.
4. Deploy!

## Usage
- **/start** — Get a welcome message
- **Send an image, image document, or static sticker (private chat)** — Bot replies with extracted text and feedback buttons
- **/ocr** — Extract text from image (in groups, use as a reply to a media message)
- **/lang <lang>** — Set OCR language (e.g., eng, hin, eng+hin)
- **/langlist** — List supported OCR languages
- **/help** — How to use the bot
- **/stats** — See satisfaction and AI usage rates
- **/ping** — Show bot latency and uptime
- **/sysd** — Show system info using neofetch (admin only)

## Feedback Flow
- After OCR, bot shows two buttons: **Satisfies** and **Use AI**
- Button names are randomized for each query:
  - Satisfied: ✅ Done, 🙌 All Good, 👍 Looks Good, 🎯 Accurate, ✅ Text is Correct, 💯 Perfect!, ✅ Satisfied
  - Use AI: 🤖 Ask AI, 🧠 Refine with AI, ✍️ Improve with AI, 🔍 Clarify with AI, 💬 AI Help, 🤔 Not Clear? Use AI, 🚀 Boost with AI
- If satisfied, feedback is recorded and file is deleted
- If "Use AI" is pressed, Gemini AI processes the image and both results are shown
- Each user can use Gemini AI 5 times per day (admins: unlimited)
- Files are auto-deleted after 30 minutes if no feedback

## Admin Features
- Multiple admins supported via `ADMIN_IDS` (comma-separated list)
- Admins have unlimited Gemini AI quota
- /sysd command is admin-only

## Development & Commit Policy
- Please squash commits before merging to keep the history clean (e.g., `git rebase -i` or GitHub squash merge)
- All major features and admin logic are documented in this README

## License
MIT 