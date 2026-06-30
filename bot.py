"""
bot.py
Entry point aplikasi Bot Telegram Pengingat Absensi.

Mendukung personal chat dan grup.

Jalankan:
    python bot.py
"""

import logging

from telegram.ext import ApplicationBuilder, CallbackQueryHandler, CommandHandler

from config import BOT_TOKEN
from handlers import (
    button_callback, 
    start_command, 
    stop_command, 
    status_command
)
from scheduler import setup_scheduler, run_startup_check

# ── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    format="%(asctime)s | %(name)-20s | %(levelname)-7s | %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


async def post_init(application) -> None:
    """Dipanggil setelah Application di-init, sebelum polling dimulai."""
    # Setup & start scheduler
    sched = setup_scheduler()
    sched.start()
    logger.info("APScheduler started.")

    # Jalankan pengecekan awal agar reminder langsung aktif jika hari kerja
    await run_startup_check()


def main() -> None:
    """Entry point utama."""
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN belum diisi! Buat file .env dan isi BOT_TOKEN.")
        return

    logger.info("Memulai bot...")

    app = (
        ApplicationBuilder()
        .token(BOT_TOKEN)
        .connect_timeout(30.0)
        .read_timeout(30.0)
        .write_timeout(30.0)
        .post_init(post_init)
        .build()
    )

    # ── Command handlers ─────────────────────────────────────────────────
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("stop", stop_command))
    app.add_handler(CommandHandler("status", status_command))


    # ── Callback handler untuk inline keyboard ───────────────────────────
    app.add_handler(CallbackQueryHandler(button_callback))

    # Mulai polling (blocking)
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
