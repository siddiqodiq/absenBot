"""
handlers.py
Handler untuk callback inline keyboard dan command Telegram.
Mendukung registrasi chat/grup via /start dan /stop.
"""

import logging

from telegram import Update
from telegram.ext import ContextTypes

from reminder import (
    attendance,
    register_chat,
    unregister_chat,
    is_registered,
    get_attendance,
)

logger = logging.getLogger(__name__)


# ── Command handlers ─────────────────────────────────────────────────────────

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    /start — Daftarkan chat/grup ini untuk menerima reminder absensi.
    Bisa digunakan di personal chat maupun grup.
    """
    if update.effective_chat is None or update.message is None:
        return

    chat_id = update.effective_chat.id
    chat_type = update.effective_chat.type  # "private", "group", "supergroup"
    chat_title = update.effective_chat.title or "Private Chat"
    thread_id = update.message.message_thread_id

    if is_registered(chat_id, thread_id):
        await update.message.reply_text(
            "ℹ️ Chat/Topik ini sudah terdaftar untuk reminder absensi."
        )
        return

    register_chat(chat_id, thread_id)

    if chat_type == "private":
        msg = (
            "✅ *Berhasil\\!*\n\n"
            "Chat ini sekarang akan menerima reminder absensi\\.\n\n"
            "📋 *Perintah:*\n"
            "/start \\— Daftar reminder\n"
            "/stop \\— Berhenti reminder\n"
            "/status \\— Cek status absensi hari ini"
        )
    else:
        topic_msg = "Topik ini" if thread_id else "Grup ini"
        msg = (
            f"✅ *Berhasil\\!*\n\n"
            f"{topic_msg} sekarang akan menerima reminder absensi\\.\n\n"
            "📋 *Perintah:*\n"
            "/start \\— Daftar reminder\n"
            "/stop \\— Berhenti reminder\n"
            "/status \\— Cek status absensi hari ini"
        )

    await update.message.reply_text(msg, parse_mode="MarkdownV2")
    logger.info("Chat/Topic %s (%s) terdaftar. Tipe: %s", (chat_id, thread_id), chat_title, chat_type)


async def stop_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    /stop — Hapus chat/grup ini dari daftar reminder.
    """
    if update.effective_chat is None or update.message is None:
        return

    chat_id = update.effective_chat.id
    thread_id = update.message.message_thread_id

    if not is_registered(chat_id, thread_id):
        await update.message.reply_text(
            "ℹ️ Chat/Topik ini belum terdaftar. Gunakan /start untuk mendaftar."
        )
        return

    unregister_chat(chat_id, thread_id)
    await update.message.reply_text(
        "🛑 Chat/Topik ini dihapus dari daftar reminder absensi.\n"
        "Gunakan /start untuk mendaftar kembali."
    )
    logger.info("Chat/Topic %s dihapus dari daftar.", (chat_id, thread_id))


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    /status — Tampilkan status absensi hari ini untuk chat ini.
    """
    if update.effective_chat is None or update.message is None:
        return

    chat_id = update.effective_chat.id
    thread_id = update.message.message_thread_id

    if not is_registered(chat_id, thread_id):
        await update.message.reply_text(
            "ℹ️ Chat/Topik ini belum terdaftar. Gunakan /start untuk mendaftar."
        )
        return

    status = get_attendance(chat_id, thread_id)
    morning_icon = "✅" if status.get("morning") else "❌"
    evening_icon = "✅" if status.get("evening") else "❌"

    text = (
        "📊 *Status Absensi Hari Ini*\n"
        "\n"
        f"Absen Masuk:  {morning_icon}\n"
        f"Absen Pulang: {evening_icon}"
    )

    await update.message.reply_text(text, parse_mode="Markdown")


# ── Callback handler ─────────────────────────────────────────────────────────

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle tombol inline keyboard yang ditekan user."""
    query = update.callback_query
    if query is None:
        return

    try:
        await query.answer()

        chat_id = query.message.chat.id
        thread_id = query.message.message_thread_id
        data = query.data
        target = (chat_id, thread_id)

        # Pastikan chat terdaftar
        if not is_registered(chat_id, thread_id):
            await query.edit_message_text("⚠️ Chat/Topik ini belum terdaftar. Gunakan /start.")
            return

        chat_attendance = attendance.get(target)
        if chat_attendance is None:
            await query.edit_message_text("⚠️ Data absensi tidak ditemukan.")
            return

        if data == "morning_done":
            chat_attendance["morning"] = True
            await query.edit_message_text(
                "✅ Konfirmasi absen *masuk* diterima\\.\n\nPengingat dihentikan\\.",
                parse_mode="MarkdownV2",
            )
            logger.info("Chat/Topic %s mengkonfirmasi absen pagi.", target)

        elif data == "evening_done":
            chat_attendance["evening"] = True
            await query.edit_message_text(
                "✅ Konfirmasi absen *pulang* diterima\\.\n\nPengingat dihentikan\\.",
                parse_mode="MarkdownV2",
            )
            logger.info("Chat/Topic %s mengkonfirmasi absen sore.", target)

    except Exception as e:
        logger.error("Terjadi error saat memproses tombol callback: %s", e)
