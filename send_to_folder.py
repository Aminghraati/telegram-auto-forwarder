"""
اسکریپت فوروارد خودکار پیام‌های سیو مسیج به پوشه تلگرام
با استفاده از Telethon (اکانت شخصی - نه بات)

کارکرد:
- دقیقاً ۵ پیام آخر «سیو مسیج» رو بدون هیچ تغییری می‌خونه
- هر پیام رو **موازی** به همه گروه‌های پوشه «گپ» فوروارد می‌کنه
  (ارسال‌ها همزمان شروع می‌شن؛ حداکثر زمان ارسال ≈ max_broadcast_seconds)
- بین هر پیام، تاخیر تصادفی (min_delay تا max_delay ثانیه)
- حلقه بی‌وقفه تا Ctrl+C یا پیام /stop در سیو مسیج
"""
import asyncio
import random
import signal
import sys
import logging
import time

# ⚠️ ویندوز: کنسول cp1256 است، برای چاپ فارسی/ایموجی حتماً UTF-8 کن
# و برای redirect/لاگ، بافر را line-buffered می‌کنیم تا خروجی فوراً نوشته شود
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)
else:
    try:
        sys.stdout.reconfigure(line_buffering=True)
    except Exception:
        pass
if sys.stderr and sys.stderr.encoding and sys.stderr.encoding.lower() not in ("utf-8", "utf8"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)

from telethon import TelegramClient, functions, connection as tg_connection
from telethon.errors import FloodWaitError

from telethon_config import (
    API_ID,
    API_HASH,
    SESSION_NAME,
    FOLDER_NAME,
    SAVED_MESSAGES_SOURCE,
    FORWARD_CONFIG,
    PROXY,
)
from system_proxy import get_telethon_proxy_args, get_windows_proxy, check_telegram_through_proxy

# تنظیم لاگ — فقط خطاهای جدی؛ لاگ‌های INFO خود Telethon خاموش تا خروجی تمیز بماند
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.WARNING,
)
logging.getLogger("telethon").setLevel(logging.ERROR)
logger = logging.getLogger(__name__)

# متغیر برای کنترل حلقه اصلی
running = True


def signal_handler(sig, frame):
    """مدیریت سیگنال Ctrl+C"""
    global running
    print("\n🛑 درخواست توقف دریافت شد... (برای توقف فوری دوباره Ctrl+C)")
    running = False


# ثبت handler برای سیگنال SIGINT (Ctrl+C)
signal.signal(signal.SIGINT, signal_handler)
try:
    # در ویندوز سیگنال SIGBREAK با Ctrl+Break یا بستن پنجره ارسال می‌شه
    signal.signal(signal.SIGBREAK, signal_handler)
except (AttributeError, ValueError):
    pass


def _build_proxy_args() -> dict:
    """
    ساخت آرگومان‌های پراکسی دستی برای TelegramClient
    اگه پراکسی دستی فعال نباشه، خالی برمی‌گرده
    """
    if not PROXY.get("enabled", False):
        return {}

    ptype = str(PROXY.get("type", "socks5")).lower()
    host = str(PROXY.get("host", "127.0.0.1"))
    port = int(PROXY.get("port", 10808))

    print(f"🛰️ اتصال از طریق پراکسی دستی {ptype} روی {host}:{port}")

    if ptype == "mtproto":
        secret = str(PROXY.get("secret", "")).strip()
        if not secret:
            raise SystemExit(
                "❌ برای پراکسی MTProto باید مقدار secret را هم در telethon_config.py بگذاری"
            )
        return {
            "connection": tg_connection.ConnectionTcpMTProxyRandomizedIntermediate,
            "proxy": (host, port, secret),
        }

    # socks5 / socks4 / http — نیاز به python-socks دارد
    return {"proxy": (ptype, host, port)}


def _check_telegram_reachable(timeout: float = 6.0) -> bool:
    """
    تست دسترسی به سرور تلگرام — مستقیم یا از طریق پراکسی سیستم
    """
    win_proxy = get_windows_proxy()
    return check_telegram_through_proxy(win_proxy)


# کش پیام‌های سیو مسیج
cached = {"messages": [], "index": 0}


class TelegramForwarder:
    """
    فورواردکننده پیام‌های سیو مسیج به پوشه‌های تلگرام
    """

    def __init__(self):
        # اولویت: پراکسی دستی کانفیگ → بعد پراکسی خودکار ویندوز → بعد مستقیم
        if PROXY.get("enabled", False):
            client_args = _build_proxy_args()
        else:
            client_args = get_telethon_proxy_args()
        self.client = TelegramClient(
            SESSION_NAME,
            API_ID,
            API_HASH,
            **client_args,
            connection_retries=3,
            timeout=15,
            request_retries=3,
        )

    async def connect(self):
        """اتصال به تلگرام (اولین بار: شماره + کد تایید)"""
        print("🔗 در حال اتصال به تلگرام...")
        await self.client.start()
        me = await self.client.get_me()
        print(f"✅ با اکانت {me.first_name} متصل شد!")

    async def get_folders(self) -> dict:
        """دریافت لیست پوشه‌ها با TL خام (سازگار با Telethon 1.45)"""
        print("\n📁 در حال دریافت لیست پوشه‌ها...")
        folders = {}
        try:
            result = await self.client(functions.messages.GetDialogFiltersRequest())
            for f in result.filters:
                raw_title = getattr(f, "title", None)
                f_id = getattr(f, "id", None)
                if raw_title is None or f_id is None:
                    continue
                title = getattr(raw_title, "text", None) or str(raw_title)
                folders[title] = f_id
                print(f"  📂 {title} (ID: {f_id})")
        except Exception as e:
            print(f"❌ خطا در دریافت پوشه‌ها: {e}")
        return folders

    async def resolve_folder_id(self, folder_name: str) -> int:
        """
        پیدا کردن ID پوشه بر اساس نام.
        اگه نام پیدا نشه، کاربر رو راهنمایی می‌کنه.
        """
        folders = await self.get_folders()
        if folder_name in folders:
            return folders[folder_name]

        print(f"\n❌ پوشه «{folder_name}» یافت نشد!")
        print("پوشه‌های موجود:")
        for name in folders.keys():
            print(f"  - {name}")
        print("\n💡 نام پوشه رو در telethon_config.py درست کن و دوباره اجرا کن.")
        return None

    async def get_folder_chats(self, folder_id: int):
        """
        دریافت چت‌های عضو یک پوشه — از لیست اعضای خود فیلتر
        (folder_id روی dialogها با تلگرام دسکتاپ همخوان نیست،
         پس مستقیم pinned_peers و include_peers پوشه را می‌خوانیم)
        """
        chats = []
        seen_ids = set()
        result = await self.client(functions.messages.GetDialogFiltersRequest())
        for f in result.filters:
            if getattr(f, "id", None) != folder_id:
                continue
            for peer in (list(getattr(f, "pinned_peers", []) or [])
                         + list(getattr(f, "include_peers", []) or [])):
                try:
                    ent = await self.client.get_entity(peer)
                except Exception as e:
                    print(f"  ⚠️ نتوانستم این عضو پوشه را باز کنم: {e}")
                    continue
                if ent.id in seen_ids:
                    continue
                seen_ids.add(ent.id)
                # فقط گروه/سوپرگروه/کانال — پیام خصوصی به افراد نمی‌زنیم
                is_group = getattr(ent, "megagroup", False) or getattr(ent, "broadcast", False) \
                    or ent.__class__.__name__ in ("Chat", "Channel")
                if not is_group:
                    continue
                chats.append(ent)
            break

        return chats

    async def refresh_saved_messages(self):
        """
        خواندن مجدد پیام‌های سیو مسیج (وقتی دور جدید شروع می‌شه)
        اگر پیام «/stop» در سیو مسیج باشد، اتوماسیون متوقف می‌شود
        """
        if not SAVED_MESSAGES_SOURCE.get("refresh_each_round", True):
            return cached["messages"]
        count = SAVED_MESSAGES_SOURCE.get("message_count", 5)
        print(f"\n📥 خواندن {count} پیام آخر سیو مسیج...")
        msgs = await self.client.get_messages("me", limit=count)

        # ⛔ کنترل از راه دور: پیام /stop در سیو مسیج = توقف
        for m in msgs[:3]:
            if m and getattr(m, "text", None) and m.text.strip().lower() == "/stop":
                print("\n⛔ دستور /stop در سیو مسیج دیده شد — توقف اتوماسیون!")
                print("   (برای شروع دوباره، پیام /stop را از سیو مسیج پاک کن و اسکریپت را اجرا کن)")
                global running
                running = False
                return []

        cached["messages"] = [m for m in msgs if m and not m.action]
        cached["index"] = 0
        print(f"✅ {len(cached['messages'])} پیام آماده فوروارد شد")
        return cached["messages"]

    @staticmethod
    def _chat_display_name(chat) -> str:
        """نام نمایشی چت — برای Channel/Chat از title، برای User از first_name"""
        name = getattr(chat, "title", None) or getattr(chat, "name", None) \
            or getattr(chat, "first_name", None) or str(getattr(chat, "id", "?"))
        return str(name)

    async def forward_one(self, msg, chat) -> bool:
        """
        فوروارد یک پیام به یک چت (قابل فراخوانی موازی)
        Returns: موفق یا نه
        """
        chat_name = self._chat_display_name(chat)
        try:
            await self.client.forward_messages(chat, msg, "me")
            return True
        except FloodWaitError as e:
            # تلگرام گفته چقدر صبر کنیم — احترام می‌ذاریم و منتظر می‌مونیم
            wait = min(e.seconds, 60)
            print(f"  ⏳ {chat_name}: تلگرام درخواست صبر کرد ({e.seconds}s) — این گروه از این دور افتاد")
            if wait < e.seconds:
                await asyncio.sleep(wait)
            return False
        except Exception as e:
            print(f"  ❌ خطا در فوروارد به {chat_name}: {e}")
            return False

    async def broadcast_one(self, msg, order) -> tuple:
        """
        ⚡ فوروارد موازی یک پیام به همه گروه‌ها (همه همزمان شروع می‌شوند)
        Returns: (تعداد موفق، مدت زمان)
        """
        tasks = [self.forward_one(msg, chat) for chat in order]
        results = await asyncio.gather(*tasks)
        sent = sum(1 for r in results if r)
        return sent

    async def run(self):
        """اجرای اصلی اسکریپت"""
        round_num = 0
        total_sent = 0

        # ⚠️ پیش‌چک: فقط هشدار — اگر پاس نشد هم تلاش واقعی را امتحان می‌کنیم
        print("🔎 بررسی اتصال به سرور تلگرام (مستقیم یا پراکسی سیستم)...")
        win_proxy = get_windows_proxy()
        if not _check_telegram_reachable():
            print("⚠️ تست اولیه ناموفق بود — ولی تلاش واقعی اتصال ادامه دارد...")
        elif win_proxy:
            print(f"✅ دسترسی تأیید شد (از طریق پراکسی سیستم {win_proxy[0]}:{win_proxy[1]})")
        else:
            print("✅ دسترسی مستقیم به تلگرام تأیید شد")

        try:
            await self.connect()

            # پیدا کردن پوشه هدف
            folder_id = await self.resolve_folder_id(FOLDER_NAME)
            if folder_id is None:
                return

            max_broadcast = float(FORWARD_CONFIG.get("max_broadcast_seconds", 20))
            print("\n" + "=" * 50)
            print("🚀 اتوماسیون فوروارد شروع به کار کرد!")
            print(f"📂 پوشه هدف: {FOLDER_NAME}")
            print(f"⚡ ارسال موازی: حداکثر {max_broadcast:.0f} ثانیه برای هر پیام (هر تعداد گروه)")
            print(
                f"⏱️ تاخیر تصادفی بین پیام‌ها: {FORWARD_CONFIG['min_delay']}-"
                f"{FORWARD_CONFIG['max_delay']} ثانیه"
            )
            print("🛑 برای توقف: Ctrl+C یا پیام /stop در سیو مسیج")
            print("=" * 50 + "\n")

            # حلقه اصلی - تا وقتی که کاربر Ctrl+C بزنه یا /stop بفرسته
            while running:
                round_num += 1
                print(f"\n{'=' * 20} دور {round_num} {'=' * 20}")

                # لیست تازه چت‌های پوشه (تا تغییرات پوشه لحاظ بشه)
                try:
                    chats = await self.get_folder_chats(folder_id)
                except Exception as e:
                    print(f"❌ خطا در دریافت چت‌های پوشه: {e}")
                    if running:
                        print("⏳ تلاش مجدد تا ۳۰ ثانیه دیگر...")
                        await self._sleep_interruptible(30)
                    continue

                if not chats:
                    print(f"⚠️ هیچ چتی در پوشه «{FOLDER_NAME}» یافت نشد!")
                    print("💡 گروه‌ها رو به پوشه اضافه کن و اسکریپت رو دوباره اجرا کن.")
                    return

                # خواندن (تازه‌سازی) پیام‌های سیو مسیج در شروع هر دور
                messages = await self.refresh_saved_messages()
                if not messages and SAVED_MESSAGES_SOURCE.get(
                    "use_latest_message_fallback", True
                ):
                    msgs = await self.client.get_messages("me", limit=1)
                    messages = [m for m in msgs if m and not m.action]
                if not messages:
                    print("❌ هیچ پیامی در سیو مسیج برای فوروارد نیست!")
                    return

                # ترتیب تصادفی گروه‌ها در هر دور
                order = chats.copy()
                if FORWARD_CONFIG.get("shuffle_groups", True):
                    random.shuffle(order)
                    print("🔀 ترتیب گروه‌ها تصادفی شد")

                sent_this_round = 0

                for msg in messages:
                    if not running:
                        break

                    msg_summary = (getattr(msg, "text", None) or "<media>")[:40]
                    print(f"\n📨 فوروارد موازی پیام «{msg_summary}...» به {len(order)} گروه:")

                    t0 = time.monotonic()
                    sent_this_msg = await self.broadcast_one(msg, order)
                    elapsed = time.monotonic() - t0

                    sent_this_round += sent_this_msg
                    total_sent += sent_this_msg
                    print(
                        f"  ↳ این پیام به {sent_this_msg}/{len(order)} گروه رسید "
                        f"در {elapsed:.1f} ثانیه"
                    )

                    # ⏱️ تاخیر تصادفی اصلی بین هر پیام
                    if running:
                        delay = random.uniform(
                            FORWARD_CONFIG["min_delay"],
                            FORWARD_CONFIG["max_delay"],
                        )
                        print(f"  ⏱️ {delay:.0f} ثانیه صبر برای پیام بعدی...")
                        await self._sleep_interruptible(delay)

                print(f"\n📊 دور {round_num} تمام شد: {sent_this_round} فوروارد موفق")
                print(f"📊 کل فورواردها از شروع: {total_sent}")

                # استراحت کوتاه بین دورها (تا حلقه فشرده نشود)
                if running:
                    await self._sleep_interruptible(5)

        except asyncio.CancelledError:
            pass
        except Exception as e:
            print(f"❌ خطای غیرمنتظره: {e}")
        finally:
            print("\n🛑 اتوماسیون متوقف شد.")
            print(f"📊 مجموع کل فورواردها: {total_sent}")
            await self.disconnect()

    async def _sleep_interruptible(self, seconds: float):
        """
        خوابیدن با قابلیت قطع سریع توسط Ctrl+C
        """
        try:
            await asyncio.sleep(seconds)
        except asyncio.CancelledError:
            pass

    async def disconnect(self):
        """قطع اتصال"""
        try:
            await self.client.disconnect()
        except Exception:
            pass


async def main():
    """تابع اصلی"""
    forwarder = TelegramForwarder()
    await forwarder.run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 اسکریپت کامل متوقف شد. خداحافظ! 👋")
        sys.exit(0)
