"""
config.py
Konfigurasi bot: token dan timezone.
"""

import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
TIMEZONE: str = "Asia/Jakarta"

# Hardcode ID Grup & Topic agar tidak perlu /start lagi
TARGET_CHAT_ID: int = int(os.getenv("TARGET_CHAT_ID", "-1003966896650"))
TARGET_THREAD_ID: int = int(os.getenv("TARGET_THREAD_ID", "357"))
