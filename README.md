# 🤖 Bot Notifikasi Presensi ETHOL PENS -> Telegram (Cloud Runner)

Bot otomatis untuk memantau status presensi/absen kuliah di **ETHOL PENS** dan mengirimkan peringatan instan ke **Telegram**. Berjalan secara gratis dan otomatis di cloud via **GitHub Actions** (laptop tidak perlu menyala).

---

## 🔒 Fitur Keamanan
* **Repository Private:** Kodingan hanya dapat diakses oleh Anda pribadi.
* **Zero Hardcoded Password:** Tidak ada password, token, atau data akun yang ditulis di dalam file kodingan.
* **GitHub Secrets:** Semua data sensitif disimpan di brankas terenkripsi milik GitHub.
* **Perlindungan `.gitignore`:** File sensitif/lokal dicegah agar tidak terunggah ke repositori.

---

## 📋 4 Rahasia yang Perlu Diisi di GitHub Secrets

Masuk ke repositori Anda di GitHub $\rightarrow$ **Settings** $\rightarrow$ **Secrets and variables** $\rightarrow$ **Actions** $\rightarrow$ Klik **New repository secret**:

| Nama Secret | Nilai / Value |
| :--- | :--- |
| `PENS_NRP` | NRP Mahasiswa Anda (contoh: `2423600028`) |
| `PENS_PASSWORD` | Password Akun PENS / CAS Anda |
| `TELEGRAM_BOT_TOKEN` | Token Bot dari `@BotFather` |
| `TELEGRAM_CHAT_ID` | Angka Chat ID dari `@userinfobot` |

---

## 🚀 Panduan Mengunggah ke GitHub

Jalankan perintah berikut di terminal pada folder ini:

```bash
git init
git add .
git commit -m "feat: initial ethol telegram bot with github actions"
git branch -M main
git remote add origin https://github.com/USERNAME-ANDA/NAMA-REPO-ANDA.git
git push -u origin main
```

---

## ⏱️ Jadwal Otomatis
Bot ini dijadwalkan otomatis melalui GitHub Actions:
* **Hari:** Senin s.d. Jumat (Hari Perkuliahan)
* **Jam:** 07:00 – 18:00 WIB (00:00 – 11:00 UTC)
* **Frekuensi:** Dijalankan setiap **10 menit**
* **Manual Run:** Anda juga bisa memicunya kapan saja lewat tab **Actions** $\rightarrow$ **ETHOL Presence Monitor** $\rightarrow$ **Run workflow** (pilih mode `TEST`).
