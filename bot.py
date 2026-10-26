import os
import sys
import json
import re
import urllib.request
import urllib.parse
import http.cookiejar
from datetime import datetime, timezone

HISTORY_FILE = os.path.join(os.path.dirname(__file__), "history.json")

def load_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return set(json.load(f))
        except Exception:
            return set()
    return set()

def save_history(history_set):
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(list(history_set), f, indent=2)

def send_telegram(bot_token, chat_id, text):
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": False
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=15) as res:
            return json.loads(res.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8")
        print(f"[TELEGRAM ERROR] HTTP {e.code}: {err_body}")
        return None
    except Exception as e:
        print(f"[TELEGRAM ERROR] {e}")
        return None

class EtholClient:
    def __init__(self, nrp, password):
        self.nrp = nrp.strip() if nrp else ""
        self.password = password.strip() if password else ""
        self.token = None
        self.cookie_jar = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(self.cookie_jar),
            urllib.request.HTTPRedirectHandler()
        )

    def login_cas(self):
        print(f"[INFO] Menghubungi CAS PENS untuk autentikasi NRP: {self.nrp}...")
        cas_url = "https://login.pens.ac.id/cas/login?service=https%3A%2F%2Fethol.pens.ac.id%2Fapi%2Fauth%2Fcas-callback"
        
        req = urllib.request.Request(cas_url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })
        try:
            resp = self.opener.open(req)
            html = resp.read().decode("utf-8", errors="ignore")
        except Exception as e:
            print(f"[ERROR] Tidak dapat membuka halaman login CAS PENS: {e}")
            return False

        lt_match = re.search(r'name="lt"\s+value="([^"]+)"', html)
        action_match = re.search(r'action="([^"]+)"', html)

        if not lt_match or not action_match:
            print("[ERROR] Formulir login CAS PENS tidak dikenali.")
            return False

        lt = lt_match.group(1)
        action = action_match.group(1)
        post_url = urllib.parse.urljoin("https://login.pens.ac.id", action)

        data = urllib.parse.urlencode({
            "username": self.nrp,
            "password": self.password,
            "lt": lt,
            "_eventId": "submit",
            "submit": "LOGIN"
        }).encode("utf-8")

        req_post = urllib.request.Request(post_url, data=data, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": resp.geturl()
        })

        try:
            resp_post = self.opener.open(req_post)
            final_url = resp_post.geturl()
            post_html = resp_post.read().decode("utf-8", errors="ignore")
        except Exception as e:
            print(f"[ERROR] Kendala saat mengirim data login ke CAS: {e}")
            return False

        print(f"[INFO] URL setelah login: {final_url}")

        for cookie in self.cookie_jar:
            if cookie.name == "token":
                self.token = cookie.value
                print("[SUCCESS] Berhasil login ke ETHOL! Token sesi aktif.")
                return True

        if "login.pens.ac.id" in final_url:
            print("[ERROR] Login gagal ditolak oleh CAS PENS. Pastikan PENS_NRP dan PENS_PASSWORD di GitHub Secrets sudah sesuai.")
        else:
            print("[ERROR] Login berhasil diarahkan, tetapi cookie token tidak ditemukan.")
        return False

    def fetch_presensi_notifikasi(self):
        if not self.token:
            if not self.login_cas():
                return None

        url = "https://ethol.pens.ac.id/api/notifikasi/mahasiswa?filterNotif=PRESENSI"
        req = urllib.request.Request(url, headers={
            "Accept": "application/json, text/plain, */*",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Cookie": f"token={self.token}",
            "Referer": "https://ethol.pens.ac.id/mahasiswa/beranda"
        })

        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code == 401:
                print("[INFO] Token kedaluwarsa. Login ulang otomatis...")
                if self.login_cas():
                    return self.fetch_presensi_notifikasi()
            else:
                print(f"[ERROR] HTTP Error {e.code}: {e}")
        except Exception as e:
            print(f"[ERROR] Gagal menghubungi API ETHOL: {e}")
        return None

def parse_iso_datetime(iso_str):
    try:
        clean_str = iso_str.replace("Z", "+00:00")
        return datetime.fromisoformat(clean_str)
    except Exception:
        return None

def main():
    nrp = os.environ.get("PENS_NRP")
    password = os.environ.get("PENS_PASSWORD")
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    lookback_minutes = int(os.environ.get("LOOKBACK_MINUTES", "120"))
    bot_mode = os.environ.get("BOT_MODE", "CRON").upper()

    print("=" * 60)
    print("🤖 ETHOL PENS PRESENCE BOT (GITHUB ACTIONS RUNNER)")
    print(f"🕒 UTC Now: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"⏱️ Jendela Pengecekan: {lookback_minutes} menit terakhir")
    print(f"⚙️ Mode: {bot_mode}")
    print("=" * 60)

    missing = []
    if not nrp: missing.append("PENS_NRP")
    if not password: missing.append("PENS_PASSWORD")
    if not bot_token: missing.append("TELEGRAM_BOT_TOKEN")
    if not chat_id: missing.append("TELEGRAM_CHAT_ID")

    if missing:
        print(f"[FATAL] Variabel Environment / Secrets berikut belum diisi: {', '.join(missing)}")
        sys.exit(1)

    client = EtholClient(nrp, password)
    notif_list = client.fetch_presensi_notifikasi()

    if notif_list is None:
        print("[ERROR] Gagal mengambil data notifikasi dari ETHOL.")
        sys.exit(1)

    print(f"[INFO] Ditemukan {len(notif_list)} riwayat presensi di akun ETHOL.")

    history = load_history()
    now_utc = datetime.now(timezone.utc)
    new_notif_count = 0

    if bot_mode == "TEST":
        print("[INFO] Menjalankan Mode TEST: Mengirim pesan konfirmasi koneksi ke Telegram...")
        test_msg = (
            "🎉 <b>Bot ETHOL PENS Berhasil Terhubung ke GitHub Actions!</b>\n\n"
            f"👤 <b>Mahasiswa:</b> {nrp}\n"
            f"🕒 <b>Waktu Server:</b> {now_utc.strftime('%Y-%m-%d %H:%M:%S UTC')}\n"
            "✅ <b>Status:</b> GitHub Secrets valid & siap memantau presensi otomatis di Cloud!"
        )
        res = send_telegram(bot_token, chat_id, test_msg)
        if res and res.get("ok"):
            print("[SUCCESS] Pesan tes berhasil dikirim ke Telegram!")
        else:
            print("[ERROR] Gagal mengirim pesan ke Telegram.")
        return

    # Inisialisasi awal jika history masih kosong
    if not history:
        print("[INFO] History kosong. Menandai notifikasi lama agar tidak spam...")
        for item in notif_list:
            nid = item.get("idNotifikasi")
            if nid:
                history.add(nid)
        save_history(history)
        print(f"[INFO] {len(history)} notifikasi awal disimpan di history.")
        return

    for item in notif_list:
        notif_id = item.get("idNotifikasi")
        if not notif_id or notif_id in history:
            continue

        created_at_str = item.get("createdAt")
        if not created_at_str:
            continue

        created_dt = parse_iso_datetime(created_at_str)
        if not created_dt:
            continue

        diff_seconds = (now_utc - created_dt).total_seconds()
        diff_minutes = diff_seconds / 60.0

        if 0 <= diff_minutes <= lookback_minutes:
            keterangan = item.get("keterangan", "Presensi dibuka")
            waktu = item.get("createdAtIndonesia", item.get("waktuNotifikasi", "-"))
            url_web = item.get("urlWeb", "")
            full_url = f"https://ethol.pens.ac.id{url_web}" if url_web.startswith("/") else "https://ethol.pens.ac.id"

            alert_text = (
                "🚨 <b>PRESENSI ETHOL DIBUKA!</b>\n\n"
                f"📌 <b>Keterangan:</b> {keterangan}\n"
                f"🕒 <b>Waktu:</b> {waktu}\n\n"
                f"👉 <a href='{full_url}'>Klik di sini untuk langsung Presensi di ETHOL</a>"
            )

            print(f"[ALERT] Presensi baru terdeteksi ({int(diff_minutes)} menit yang lalu): {keterangan}")
            res = send_telegram(bot_token, chat_id, alert_text)
            if res and res.get("ok"):
                print("[SUCCESS] Notifikasi presensi terkirim ke Telegram!")
                history.add(notif_id)
                new_notif_count += 1
            else:
                print("[ERROR] Gagal mengirim notifikasi ke Telegram.")

    if new_notif_count > 0:
        save_history(history)
        print(f"[DONE] Sukses mengirim {new_notif_count} notifikasi presensi baru.")
    else:
        print("[INFO] Tidak ada presensi baru yang dibuka dalam kurun waktu pemantauan.")

if __name__ == "__main__":
    main()
