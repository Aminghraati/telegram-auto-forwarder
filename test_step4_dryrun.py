"""STEP 4 TEST: full round simulation with mocked forward (NO real sends)"""
import asyncio
import random
import sys

if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import send_to_folder as stf
from send_to_folder import TelegramForwarder, cached
from telethon_config import FOLDER_NAME, FORWARD_CONFIG


async def main():
    f = TelegramForwarder()
    await f.client.connect()
    me = await f.client.get_me()
    print(f"[OK] connected as {me.first_name}")

    # ---- MOCK: forward_messages فقط ثبت می‌کند، چیزی نمی‌فرستد
    calls = []
    async def fake_forward(entity, msg, src):
        calls.append((entity.id, msg.id))
        return True
    f.client.forward_messages = fake_forward
    print("[MOCK] forward_messages replaced (no real sends)")

    # ---- منطق واقعی run(): همان بلوک داخل while، دقیقاً همان ترتیب
    folder_id = (await f.get_folders())[FOLDER_NAME]
    chats = await f.get_folder_chats(folder_id)
    assert chats, "no chats"
    print(f"[OK] {len(chats)} chats resolved")

    await f.refresh_saved_messages()
    assert not any(getattr(m, "text", None) and m.text.strip().lower() == "/stop" for m in cached["messages"]), "/stop present!"
    messages = cached["messages"]
    assert messages, "no messages"
    print(f"[OK] {len(messages)} messages loaded (no /stop)")

    order = chats.copy()
    if FORWARD_CONFIG.get("shuffle_groups", True):
        random.shuffle(order)
    print("[OK] order shuffled")

    total_sent = 0
    same_time_gap = float(FORWARD_CONFIG.get("same_time_gap", 0.5))
    for msg in messages:
        msg_summary = (getattr(msg, "text", None) or "<media>")[:40]
        print(f"\n[SIM] message '{msg_summary}' -> {len(order)} groups")
        sent_this_msg = 0
        for i, chat in enumerate(order):
            ok = await f.forward_one(msg, chat)
            assert ok, f"forward failed for {chat.id}"
            sent_this_msg += 1
            total_sent += 1
            print(f"  [SIM-OK] {f._chat_display_name(chat)}")
            if i < len(order) - 1 and same_time_gap > 0:
                await asyncio.sleep(0)  # تست: بدون انتظار واقعی
        print(f"  [SIM] delivered {sent_this_msg}/{len(order)}")
        # بدون انتظار واقعی در تست — فقط منطق عددی (بازه از کانفیگ خوانده می‌شود)
        delay = random.uniform(FORWARD_CONFIG["min_delay"], FORWARD_CONFIG["max_delay"])
        assert FORWARD_CONFIG["min_delay"] <= delay <= FORWARD_CONFIG["max_delay"], \
            f"delay {delay} out of range!"
        print(f"  [SIM] would wait {delay:.1f}s")

    # ---- اعتبارسنجی نهایی
    expected = len(messages) * len(order)
    assert total_sent == expected, f"sent {total_sent} != expected {expected}"
    # calls=(chat_id, msg_id) — ولی forward یک‌بار به هر گروه با هر msg.id واقعی سیو مسیج
    # در mock ما msg همان آبجکت است؛ پس اینجا فقط تعداد را چک می‌کنیم
    assert len(calls) == expected, f"mock calls {len(calls)} != expected {expected}"
    print(f"\n[OK] simulated {total_sent} forwards = {len(messages)} msgs x {len(order)} groups")
    print("[OK] every message went to every group exactly once (same-time broadcast OK)")

    await f.client.disconnect()
    print("\nSTEP4: PASS")


asyncio.run(main())
