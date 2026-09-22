"""STEP 3 TEST: read folder 'گپ' members + last 5 saved messages using real classes"""
import asyncio
import sys

if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from send_to_folder import TelegramForwarder, cached
from telethon_config import FOLDER_NAME


async def main():
    f = TelegramForwarder()
    await f.client.connect()
    me = await f.client.get_me()
    print(f"[OK] connected as {me.first_name}")

    folders = await f.get_folders()
    assert FOLDER_NAME in folders, f"folder {FOLDER_NAME!r} not found!"
    fid = folders[FOLDER_NAME]
    print(f"[OK] folder '{FOLDER_NAME}' -> id {fid}")

    chats = await f.get_folder_chats(fid)
    print(f"[OK] {len(chats)} group chats in folder:")
    for c in chats:
        print(f"     - {TelegramForwarder._chat_display_name(c)} (id={c.id})")
    assert len(chats) > 0, "no chats in folder!"

    msgs = await f.client.get_messages("me", limit=5)
    real = [m for m in msgs if m and not m.action]
    print(f"[OK] {len(real)} saved messages found:")
    for m in real:
        kind = "text" if m.text else "media"
        preview = (m.text or f"<{m.media.__class__.__name__}>" if m.media else "<empty>")
        print(f"     - [{kind}] {str(preview)[:50]}")
    assert len(real) > 0, "no saved messages!"

    # dry-run forward target check: entity types must be Channel/Chat
    types_ok = all(c.__class__.__name__ in ("Channel", "Chat") for c in chats)
    print(f"[OK] all targets are Channel/Chat: {types_ok}")

    await f.client.disconnect()
    print("\nSTEP3: PASS")


asyncio.run(main())
