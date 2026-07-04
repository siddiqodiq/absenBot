"""
scheduler.py
Konfigurasi APScheduler untuk reminder harian.
"""

import logging
from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from config import TIMEZONE
from holiday import is_holiday
from reminder import reset_attendance, send_morning_reminder, send_evening_reminder, send_holiday_announcement, registered_chats

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler(timezone=TIMEZONE)

# ── Prefiks ID job ───────────────────────────────────────────────────────────
MORNING_TAG = "morning_reminder"
EVENING_TAG = "evening_reminder"


def _remove_jobs_by_prefix(prefix: str) -> None:
    """Hapus semua job yang ID-nya dimulai dengan prefix tertentu."""
    jobs_to_remove = [j for j in scheduler.get_jobs() if j.id.startswith(prefix)]
    for job in jobs_to_remove:
        job.remove()
        logger.info("Job dihapus: %s", job.id)


def _schedule_morning_jobs() -> None:
    """Buat job-job reminder pagi."""
    # 07:15 — reminder pertama
    scheduler.add_job(
        _run_async_reminder,
        CronTrigger(hour=7, minute=15, timezone=TIMEZONE),
        id=f"{MORNING_TAG}_0715",
        args=[send_morning_reminder],
        replace_existing=True,
    )

    # 07:25 — reminder kedua
    scheduler.add_job(
        _run_async_reminder,
        CronTrigger(hour=7, minute=25, timezone=TIMEZONE),
        id=f"{MORNING_TAG}_0725",
        args=[send_morning_reminder],
        replace_existing=True,
    )

    # 07:30 — reminder batas waktu
    scheduler.add_job(
        _run_async_reminder,
        CronTrigger(hour=7, minute=30, timezone=TIMEZONE),
        id=f"{MORNING_TAG}_0730",
        args=[send_morning_reminder],
        replace_existing=True,
    )

    # Setelah 07:30, setiap 5 menit: 07:35, 07:40, 07:45, 07:50, 07:55
    # Lalu 08:00, 08:05, ... sampai akhir hari (aman karena attendance check akan skip)
    scheduler.add_job(
        _run_async_reminder,
        CronTrigger(
            hour="7-11",
            minute="0,5,10,15,20,25,30,35,40,45,50,55",
            timezone=TIMEZONE,
        ),
        id=f"{MORNING_TAG}_repeat",
        args=[send_morning_reminder],
        replace_existing=True,
    )
    # Catatan: duplikasi trigger di 07:15, 07:25, 07:30 tidak masalah
    # karena reminder.send_morning_reminder() akan skip chat yang sudah True.

    logger.info("Job reminder pagi dijadwalkan.")


def _schedule_evening_jobs() -> None:
    """Buat job-job reminder sore."""
    # 16:00 — reminder pertama
    scheduler.add_job(
        _run_async_reminder,
        CronTrigger(hour=16, minute=0, timezone=TIMEZONE),
        id=f"{EVENING_TAG}_1600",
        args=[send_evening_reminder],
        replace_existing=True,
    )

    # Setelah 16:00, setiap 10 menit: 16:10, 16:20, 16:30, ...
    scheduler.add_job(
        _run_async_reminder,
        CronTrigger(
            hour="16-21",
            minute="0,10,20,30,40,50",
            timezone=TIMEZONE,
        ),
        id=f"{EVENING_TAG}_repeat",
        args=[send_evening_reminder],
        replace_existing=True,
    )
    # Catatan: duplikasi trigger di 16:00 tidak masalah karena attendance check akan skip.

    logger.info("Job reminder sore dijadwalkan.")


async def _run_async_reminder(reminder_func) -> None:
    """Wrapper untuk menjalankan fungsi async reminder dari APScheduler."""
    await reminder_func()

async def _run_holiday_announcement(holiday_name: str) -> None:
    """Wrapper untuk menjalankan fungsi pengumuman libur."""
    await send_holiday_announcement(holiday_name)

import pytz

async def daily_check() -> None:
    """
    Pengecekan harian pada pukul 00:00 WIB.
    - Reset status absensi semua chat
    - Cek hari kerja (Senin-Jumat)
    - Cek hari libur nasional
    - Jadwalkan reminder jika hari kerja biasa
    """
    reset_attendance()

    tz = pytz.timezone(TIMEZONE)
    today = datetime.now(tz)

    # Cek hari kerja (0=Senin, 6=Minggu)
    weekday = today.weekday()
    if weekday >= 5:  # Sabtu atau Minggu
        weekend_name = "Hari Sabtu" if weekday == 5 else "Hari Minggu"
        logger.info("Hari ini weekend (%s). Tidak ada reminder, mengirim sapaan.", weekend_name)
        _remove_jobs_by_prefix(MORNING_TAG)
        _remove_jobs_by_prefix(EVENING_TAG)
        
        # Jadwalkan pengumuman akhir pekan pada pukul 07:15
        scheduler.add_job(
            _run_holiday_announcement,
            CronTrigger(hour=7, minute=15, timezone=TIMEZONE),
            id="weekend_announcement",
            args=[f"Akhir Pekan {weekend_name}"],
            replace_existing=True,
        )
        return

    # Cek hari libur nasional
    is_hol, hol_name = is_holiday(today.date())
    if is_hol:
        logger.info("Hari ini libur nasional: %s. Tidak ada reminder, mengirim pengumuman.", hol_name)
        _remove_jobs_by_prefix(MORNING_TAG)
        _remove_jobs_by_prefix(EVENING_TAG)
        
        # Jadwalkan pengumuman dikirim pada pukul 07:15 agar tidak membangunkan orang di tengah malam
        scheduler.add_job(
            _run_holiday_announcement,
            CronTrigger(hour=7, minute=15, timezone=TIMEZONE),
            id="holiday_announcement",
            args=[hol_name],
            replace_existing=True,
        )
        # Jika bot baru dijalankan (startup) setelah 07:15 di hari libur, pengumuman tidak akan dikirim,
        # tapi Anda dapat menambahkan logika khusus jika diperlukan.
        return

    # Cek apakah ada chat terdaftar
    if not registered_chats:
        logger.info("Tidak ada chat terdaftar, skip penjadwalan reminder.")
        return

    # Hari kerja biasa — jadwalkan reminder
    logger.info("Hari kerja biasa. Menjadwalkan reminder untuk %d chat...", len(registered_chats))
    _schedule_morning_jobs()
    _schedule_evening_jobs()


def setup_scheduler() -> AsyncIOScheduler:
    """Setup dan kembalikan scheduler."""
    # Job harian pukul 00:00
    scheduler.add_job(
        daily_check,
        CronTrigger(hour=0, minute=0, timezone=TIMEZONE),
        id="daily_check",
        replace_existing=True,
    )

    logger.info("Scheduler utama dikonfigurasi.")
    return scheduler


async def run_startup_check() -> None:
    """
    Jalankan pengecekan saat bot pertama kali start.
    Agar tidak perlu menunggu sampai 00:00 untuk mulai reminder.
    """
    logger.info("Menjalankan pengecekan startup...")
    await daily_check()
