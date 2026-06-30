"""
holiday.py
Cek hari libur nasional via API upset.dev/tanggalmerah.
"""

import logging
from datetime import date

import requests

logger = logging.getLogger(__name__)

API_URL = "https://tanggalmerah.upset.dev/api/check"


def is_holiday(check_date: date | None = None) -> tuple[bool, str]:
    """
    Mengembalikan tuple (True/False, nama_libur).
    Jika API gagal dihubungi, mengembalikan (False, "") agar reminder tetap jalan.
    """
    if check_date is None:
        check_date = date.today()

    date_str = check_date.strftime("%Y-%m-%d")

    try:
        response = requests.get(API_URL, params={"date": date_str}, timeout=10)
        response.raise_for_status()
        result = response.json()
        data = result.get("data", {})

        is_holiday_flag = data.get("is_holiday", False)
        is_leave = data.get("is_leave", False)

        if is_holiday_flag or is_leave:
            # Ambil nama hari libur dari array holidays jika ada
            holidays = data.get("holidays", [])
            name = holidays[0].get("name", "Libur") if holidays else "Libur"
            logger.info("Hari ini libur: %s (%s)", date_str, name)
            return True, name

        logger.info("Hari ini bukan hari libur: %s", date_str)
        return False, ""

    except requests.RequestException as e:
        logger.warning("Gagal cek API hari libur: %s. Anggap bukan hari libur.", e)
        return False, ""
