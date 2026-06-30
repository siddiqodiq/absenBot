"""
config.py
Konfigurasi bot: token dan timezone.
"""

import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
TIMEZONE: str = "Asia/Jakarta"
