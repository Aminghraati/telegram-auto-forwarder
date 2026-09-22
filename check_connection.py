"""
تست سریع اتصال به تلگرام (مستقیم یا از طریق پراکسی سیستم)
اگر خروجی [OK] بود، اسکریپت اصلی آماده اجراست.
"""
from system_proxy import get_windows_proxy, check_telegram_through_proxy


def main():
    print("Checking connection to Telegram servers...")
    proxy = get_windows_proxy()
    if check_telegram_through_proxy(proxy):
        if proxy:
            print(f"[OK] TELEGRAM REACHABLE via system proxy {proxy[0]}:{proxy[1]}")
        else:
            print("[OK] TELEGRAM REACHABLE (direct connection)")
    else:
        print("[BLOCKED] TELEGRAM NOT REACHABLE")
        print("-> Connect your VPN / mobile hotspot proxy and try again")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
