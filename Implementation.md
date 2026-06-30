# Implementation.md

# Bot Telegram Pengingat Absensi

## Tujuan

Membuat bot Telegram sederhana yang berfungsi sebagai pengingat absensi harian.

Bot berjalan menggunakan satu proses Python saja:

```bash
python bot.py
```

Tanpa menggunakan database.

Seluruh status absensi hanya disimpan di memori (in-memory) dan akan di-reset setiap pergantian hari.

---

# Teknologi

* Python 3.11+
* python-telegram-bot
* APScheduler
* requests
* timezone Asia/Jakarta
* API Hari Libur Indonesia

API yang digunakan:

```
https://upset.dev/tanggalmerah
```

---

# Alur Utama

Bot akan melakukan pengecekan setiap hari pada pukul 00.00 WIB.

Flow:

```
Mulai Hari Baru
        │
        ▼
Hari ini Senin–Jumat?
        │
   ┌────┴────┐
   │         │
 Tidak      Ya
   │         │
 Stop        ▼
      Cek API Tanggal Merah
              │
      ┌───────┴────────┐
      │                │
 Hari Libur        Bukan Libur
      │                │
 Stop        Aktifkan Scheduler Hari Ini
```

---

# Penentuan Hari Kerja

Hari kerja hanya:

* Senin
* Selasa
* Rabu
* Kamis
* Jumat

Jika hari:

* Sabtu
* Minggu

Maka bot tidak mengirim reminder apa pun.

---

# Cek Hari Libur Nasional

Setelah dipastikan hari kerja, bot melakukan request ke API:

Contoh:

```
GET https://upset.dev/tanggalmerah/api?date=2026-07-01
```

Contoh response:

```json
{
  "date": "2026-07-01",
  "name": "Tahun Baru Islam",
  "isHoliday": true,
  "isCuti": false
}
```

Logika:

```
Jika isHoliday == true
        atau
isCuti == true

↓

Tidak ada reminder hari itu
```

Jika bukan hari libur:

```
Scheduler reminder diaktifkan
```

---

# Status Harian

Karena tidak menggunakan database, status cukup menggunakan variabel global.

Contoh:

```python
attendance = {
    "morning": False,
    "evening": False
}
```

Artinya:

```
False
=
Belum konfirmasi

True
=
Sudah menekan tombol
```

Setiap pukul 00.00 status di-reset.

---

# Flow Reminder Pagi

Batas absensi:

```
07.30 WIB
```

Urutan reminder:

| Jam   | Aksi                                 |
| ----- | ------------------------------------ |
| 07.15 | Reminder pertama                     |
| 07.25 | Reminder kedua                       |
| 07.30 | Reminder batas waktu                 |
| 07.35 | Reminder ulang jika belum konfirmasi |
| 07.40 | Reminder ulang                       |
| 07.45 | Reminder ulang                       |
| ...   | Lanjut setiap 5 menit                |

Flow:

```
07.15
    │
Kirim Reminder
    │
Sudah Absen?
    │
 ┌──┴──┐
 │     │
Ya    Tidak
 │      │
Stop    ▼
    07.25
         │
 Sudah Absen?
         │
      ┌──┴──┐
      │     │
     Ya   Tidak
      │      │
    Stop   07.30
               │
      Belum?
               │
      Reminder tiap 5 menit
               │
      Sampai tombol ditekan
```

---

# Flow Reminder Pulang

Jam pulang:

```
16.00 WIB
```

Urutan reminder:

| Jam   | Aksi                   |
| ----- | ---------------------- |
| 16.00 | Reminder pertama       |
| 16.10 | Reminder ulang         |
| 16.20 | Reminder ulang         |
| 16.30 | Reminder ulang         |
| ...   | Lanjut setiap 10 menit |

Flow:

```
16.00
    │
Reminder
    │
Sudah Absen?
    │
 ┌──┴──┐
 │     │
Ya    Tidak
 │      │
Stop    ▼
 Reminder tiap 10 menit
       │
 Sampai tombol ditekan
```

---

# Tombol Telegram

Reminder pagi

```
🌅 Pengingat Absen Masuk

Batas absensi:
07.30 WIB

Status:
❌ Belum dikonfirmasi

[✅ Sudah Absen]
```

Reminder sore

```
🏠 Pengingat Absen Pulang

Status:
❌ Belum dikonfirmasi

[✅ Sudah Absen Pulang]
```

---

# Callback Button

Saat tombol ditekan:

```
attendance["morning"] = True
```

atau

```
attendance["evening"] = True
```

Kemudian bot membalas:

```
✅ Konfirmasi diterima.

Pengingat dihentikan.
```

Scheduler berikutnya akan mengecek status tersebut.

Jika sudah True:

```
Tidak mengirim reminder lagi.
```

---

# Scheduler

Scheduler berjalan menggunakan APScheduler.

Scheduler yang diperlukan:

## Scheduler Harian

```
00.00
```

Fungsi:

* reset status
* cek hari kerja
* cek hari libur
* membuat scheduler reminder hari itu

---

## Scheduler Reminder Pagi

```
07.15

07.25

07.30
```

Setelah 07.30:

```
Setiap 5 menit
```

Berhenti ketika:

```
attendance["morning"] == True
```

---

## Scheduler Reminder Sore

```
16.00
```

Setelah itu:

```
Setiap 10 menit
```

Berhenti ketika:

```
attendance["evening"] == True
```

---

# Struktur Project

```
project/

│
├── bot.py
├── config.py
├── scheduler.py
├── holiday.py
├── reminder.py
├── handlers.py
├── requirements.txt
└── implementation.md
```

---

# config.py

Berisi:

* BOT_TOKEN
* CHAT_ID
* Timezone Asia/Jakarta

---

# holiday.py

Tugas:

* request API tanggal merah
* mengembalikan:

```
True
```

jika hari libur

atau

```
False
```

jika bukan hari libur

---

# reminder.py

Berisi fungsi:

```
send_morning_reminder()
```

```
send_evening_reminder()
```

Kedua fungsi akan mengecek status konfirmasi sebelum mengirim pesan.

---

# handlers.py

Menangani:

Inline Keyboard Callback

```
morning_done
```

```
evening_done
```

Kemudian mengubah status menjadi True.

---

# scheduler.py

Berisi seluruh konfigurasi APScheduler.

Bertugas:

* reset status harian
* cek hari kerja
* cek API hari libur
* membuat job reminder
* menghentikan reminder jika status sudah True

---

# bot.py

Entry point aplikasi.

Flow:

```
Load Config

↓

Start Telegram Bot

↓

Start APScheduler

↓

Register Callback Handler

↓

Idle
```

Bot akan terus berjalan selama proses Python aktif dan tidak memerlukan database maupun service tambahan.
