"""
لاگین دو مرحله‌ای — برای وقتی که Freebuff نمی‌تواند ورودی تعاملی بگیرد

استفاده:
    python login.py send_code   → کد ورود به گوشی تو ارسال می‌شود
    python login.py verify 12345  → کدی که گرفتی را همینطور بده
    python login.py status      → چک اینکه لاگین انجام شده یا نه

بعد از verify، فایل my_telegram.session ساخته می‌شود و دیگر هرگز لازم نیست لاگین کنی.
"""
import asyncio
import os
import sys
import threading
import time

# ⚠️ ویندوز: کنسول cp1256 است، برای چاپ فارسی/ایموجی حتماً UTF-8 کن
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if sys.stderr and sys.stderr.encoding and sys.stderr.encoding.lower() not in ("utf-8", "utf8"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import qrcode
from telethon import TelegramClient, functions, password as telethon_password

from telethon_config import API_ID, API_HASH, SESSION_NAME, PHONE_NUMBER
from system_proxy import get_telethon_proxy_args, get_windows_proxy, check_telegram_through_proxy

STATE_FILE = "login_state.txt"


def save_state(data: dict):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(f"{k}={v}" for k, v in data.items()))


def load_state() -> dict:
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            lines = [l.strip() for l in f if "=" in l]
            return dict(l.split("=", 1) for l in lines)
    except FileNotFoundError:
        return {}


def get_client() -> TelegramClient:
    proxy_args = get_telethon_proxy_args()
    if proxy_args:
        print(f"→ استفاده از پراکسی سیستم: {proxy_args['proxy']}")
    return TelegramClient(
        SESSION_NAME,
        API_ID,
        API_HASH,
        **proxy_args,
        connection_retries=3,
        timeout=15,
        request_retries=3,
    )


async def send_code():
    client = get_client()
    await client.connect()

    if await client.is_user_authorized():
        me = await client.get_me()
        print(f"ALREADY_LOGGED_IN: {me.first_name} ({me.phone})")
        await client.disconnect()
        return

    result = await client.send_code_request(PHONE_NUMBER)
    # ذخیره phone_code_hash — بدون این، verify کار نمی‌کند
    save_state({
        "phone_code_hash": result.phone_code_hash,
        "sent_at": str(result.timeout or ""),
    })
    print(f"CODE_SENT_TO: {PHONE_NUMBER}")
    print("→ کد ۵ رقمی الان به تلگرام گوشی تو رسید (از تلگرام رسمی، نه از کسی دیگر)")
    print("→ فقط کافیه عدد کد را برایم بفرستی")
    await client.disconnect()


async def verify(code: str):
    state = load_state()
    if not state.get("phone_code_hash"):
        print("ERROR: اول دستور send_code را اجرا کن")
        sys.exit(1)

    client = get_client()
    await client.connect()

    try:
        await client.sign_in(
            phone=PHONE_NUMBER,
            code=code.strip(),
            phone_code_hash=state["phone_code_hash"],
        )
    except Exception as e:
        print(f"LOGIN_FAILED: {type(e).__name__}: {e}")
        await client.disconnect()
        sys.exit(1)

    me = await client.get_me()
    print(f"LOGIN_OK: {me.first_name} ({me.phone})")
    print("→ لاگین کامل شد! دیگر هیچ‌وقت لازم نیست کد بدهی.")
    await client.disconnect()


async def status():
    client = get_client()
    await client.connect()
    if await client.is_user_authorized():
        me = await client.get_me()
        print(f"LOGGED_IN: {me.first_name} ({me.phone})")
    else:
        print("NOT_LOGGED_IN")
    await client.disconnect()


async def qr_login():
    """
    ورود با QR: کد QR در ترمینال نمایش داده می‌شود،
    تو در تلگرام گوشی: Settings → Devices → Link Desktop Device
    """
    client = get_client()
    await client.connect()

    if await client.is_user_authorized():
        me = await client.get_me()
        print(f"ALREADY_LOGGED_IN: {me.first_name} ({me.phone})")
        await client.disconnect()
        return

    def _show_qr(url: str):
        qr = qrcode.QRCode(border=1)
        qr.add_data(url)
        qr.print_ascii(invert=True)

    # نمایش QR به‌صورت زنده (فایل PNG برای پنل Preview + متن ترمینال)
    def _save_qr_png(url: str):
        try:
            img = qrcode.make(url)
            img.save("login_qr.png")
            # باز کردن خودکار QR در تصویربردار ویندوز برای اسکن راحت
            os.startfile(os.path.abspath("login_qr.png"))
        except Exception:
            pass

    user = await client.qr_login()
    _show_qr(user.url)
    _save_qr_png(user.url)
    print("→ گوشی را بردار و در تلگرام برو:")
    print("   تنظیمات ← دستگاه‌ها ← اتصال دستگاه دسکتاپ")
    print("   (Settings → Devices → Link Desktop Device)")
    print("→ کد QR (فایل login_qr.png یا همین ترمینال) را با تلگرام گوشی اسکن کن")

    timeout = 120  # ثانیه
    start = time.time()
    while user is not None and time.time() - start < timeout:
        try:
            done = await asyncio.wait_for(user.wait(), timeout=5)
            if done:
                me = await client.get_me()
                print(f"\nQR_LOGIN_OK: {me.first_name} ({me.phone})")
                print("→ لاگین کامل شد! دیگر هیچ‌وقت لازم نیست کد یا QR بدهی.")
                await client.disconnect()
                return
        except asyncio.TimeoutError:
            pass
        # به‌روزرسانی توکن QR (تلگرام هر ~۳۰ ثانیه توکن را عوض می‌کند)
        try:
            user = await user.recreate()
            print("\n→ QR تازه شد، دوباره اسکن کن:")
            _show_qr(user.url)
            _save_qr_png(user.url)
        except Exception:
            break

    if user is not None and time.time() - start >= timeout:
        print("\nQR_TIMEOUT: زمان اسکن تمام شد - دوباره دستور را اجرا کن")
    await client.disconnect()


def _check_reachable() -> bool:
    """تست دسترسی به تلگرام — مستقیم یا از طریق پراکسی سیستم"""
    return check_telegram_through_proxy(get_windows_proxy())


async def main():
    if not _check_reachable():
        print("ERROR: اتصال به سرور تلگرام ممکن نیست!")
        print("→ هات‌اسپات/فیلترشکن موبایل یا ExpressVPN را وصل کن و دوباره تلاش کن")
        sys.exit(2)

    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"

    if cmd == "send_code":
        await send_code()
    elif cmd == "verify":
        if len(sys.argv) < 3:
            print("ERROR: کد را بنویس. مثال: python login.py verify 12345")
            sys.exit(1)
        await verify(sys.argv[2])
    elif cmd == "qr":
        await qr_login()
    elif cmd == "status":
        await status()
    else:
        print("دستورها: send_code | verify <code> | qr | status")


if __name__ == "__main__":
    asyncio.run(main())
