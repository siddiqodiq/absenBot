"""
reminder.py
Fungsi pengiriman pesan reminder pagi dan sore ke Telegram.
Mendukung multi-chat (personal chat & grup).
"""

import logging

from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.request import HTTPXRequest

from config import BOT_TOKEN, TARGET_CHAT_ID, TARGET_THREAD_ID

logger = logging.getLogger(__name__)

# Konfigurasi timeout khusus untuk instance Bot terpisah (agar tidak kena default 5 detik)
_request = HTTPXRequest(connect_timeout=30.0, read_timeout=30.0, write_timeout=30.0)
bot = Bot(token=BOT_TOKEN, request=_request)

# ── Registered chats ─────────────────────────────────────────────────────────
# Set berisi target (chat_id, message_thread_id) yang sudah register via /start
registered_chats: set[tuple[int, int | None]] = set()

# ── Status absensi in-memory per target ────────────────────────────────────────
# Format: {(chat_id, message_thread_id): {"morning": False, "evening": False}}
attendance: dict[tuple[int, int | None], dict[str, bool]] = {}

# Otomatis daftarkan target chat utama
if TARGET_CHAT_ID:
    _target = (TARGET_CHAT_ID, TARGET_THREAD_ID)
    registered_chats.add(_target)
    attendance[_target] = {"morning": False, "evening": False}


def register_chat(chat_id: int, message_thread_id: int | None = None) -> None:
    """Daftarkan chat (dan topik spesifik) untuk menerima reminder."""
    target = (chat_id, message_thread_id)
    registered_chats.add(target)
    if target not in attendance:
        attendance[target] = {"morning": False, "evening": False}
    logger.info("Chat/Topic %s terdaftar.", target)


def unregister_chat(chat_id: int, message_thread_id: int | None = None) -> None:
    """Hapus chat (dan topik spesifik) dari daftar reminder."""
    target = (chat_id, message_thread_id)
    registered_chats.discard(target)
    attendance.pop(target, None)
    logger.info("Chat/Topic %s dihapus dari daftar.", target)


def is_registered(chat_id: int, message_thread_id: int | None = None) -> bool:
    """Cek apakah chat/topik sudah terdaftar."""
    return (chat_id, message_thread_id) in registered_chats


def reset_attendance() -> None:
    """Reset seluruh status absensi menjadi False (dijalankan tiap tengah malam)."""
    for target in attendance:
        attendance[target]["morning"] = False
        attendance[target]["evening"] = False
    logger.info("Status absensi di-reset untuk %d chat/topik.", len(attendance))


def get_attendance(chat_id: int, message_thread_id: int | None = None) -> dict[str, bool]:
    """Mengambil status absensi untuk sebuah chat/topik. Kembalikan default jika tidak ada."""
    target = (chat_id, message_thread_id)
    return attendance.get(target, {"morning": False, "evening": False})


# ── Reminder pagi ────────────────────────────────────────────────────────────
async def send_morning_reminder() -> None:
    """Kirim reminder absen masuk ke semua chat yang belum konfirmasi."""
    if not registered_chats:
        logger.info("Tidak ada chat terdaftar, skip reminder pagi.")
        return

    text = (
        "🌅 *Pengingat Absen Masuk*\n"
        "\n"
        "Batas absensi:\n"
        "07\\.30 WIB\n"
        "\n"
        "Status:\n"
        "❌ Belum dikonfirmasi"
    )

    keyboard = InlineKeyboardMarkup(
        [[InlineKeyboardButton("✅ Sudah Absen", callback_data="morning_done")]]
    )

    for target in list(registered_chats):
        chat_id, thread_id = target
        if attendance[target].get("morning"):
            continue

        try:
            await bot.send_message(
                chat_id=chat_id,
                message_thread_id=thread_id,
                text=text,
                parse_mode="MarkdownV2",
                reply_markup=keyboard,
            )
            logger.info("Reminder pagi terkirim ke chat/topik %s.", target)
        except Exception as e:
            logger.error("Gagal kirim reminder pagi ke chat/topik %s: %s", target, e)


# ── Reminder sore ────────────────────────────────────────────────────────────
async def send_evening_reminder() -> None:
    """Kirim pesan pengingat absen pulang."""
    if not registered_chats:
        logger.info("Tidak ada chat terdaftar, skip reminder sore.")
        return

    keyboard = InlineKeyboardMarkup(
        [[InlineKeyboardButton("✅ Sudah Absen Pulang", callback_data="evening_done")]]
    )
    text = (
        "🌆 *Pengingat Absen Pulang*\n"
        "\n"
        "Saatnya absen pulang\\!\n"
        "Silakan klik tombol di bawah ini jika sudah melakukan absen di sistem\\."
    )

    for target in list(registered_chats):
        chat_id, thread_id = target
        if attendance[target].get("evening"):
            continue

        try:
            await bot.send_message(
                chat_id=chat_id,
                message_thread_id=thread_id,
                text=text,
                parse_mode="MarkdownV2",
                reply_markup=keyboard,
            )
            logger.info("Reminder sore terkirim ke chat/topik %s.", target)
        except Exception as e:
            logger.error("Gagal kirim reminder sore ke chat/topik %s: %s", target, e)

# ── Pengumuman Libur ─────────────────────────────────────────────────────────
async def send_holiday_announcement(holiday_name: str) -> None:
    """Kirim pesan pengumuman hari libur ke semua chat terdaftar."""
    if not registered_chats:
        logger.info("Tidak ada chat terdaftar, skip pengumuman libur.")
        return

    text = (
        f"🎉 *Hari Libur Nasional*\n"
        f"\n"
        f"Hari ini adalah: *{holiday_name}*\n"
        f"Tidak ada pengingat absensi hari ini\\. Selamat berlibur\\!"
    )

    for target in list(registered_chats):
        chat_id, thread_id = target
        try:
            await bot.send_message(
                chat_id=chat_id,
                message_thread_id=thread_id,
                text=text,
                parse_mode="MarkdownV2",
            )
            logger.info("Pengumuman libur terkirim ke chat/topik %s.", target)
        except Exception as e:
            logger.error("Gagal kirim pengumuman libur ke chat/topik %s: %s", target, e)
