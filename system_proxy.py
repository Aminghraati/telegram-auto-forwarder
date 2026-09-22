"""
شناسایی خودکار پراکسی ویندوز (system proxy)

اگر لپ‌تاپ از هات‌اسپات موبایل / فیلترشکن با پراکسی سیستم استفاده کند،
این ماژول آن را از رجیستری ویندوز می‌خواند و به Telethon می‌دهد.
اگر پراکسی‌ای نباشد، اتصال مستقیم استفاده می‌شود.
"""
import socket
import urllib.request
import urllib.error


def get_windows_proxy():
    """
    خواندن پراکسی از تنظیمات ویندوز (Internet Settings)
    Returns: (host, port) یا None
    """
    try:
        import winreg
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Internet Settings",
        )
        enabled, _ = winreg.QueryValueEx(key, "ProxyEnable")
        if not enabled:
            return None
        server, _ = winreg.QueryValueEx(key, "ProxyServer")
        winreg.CloseKey(key)
    except Exception:
        return None

    if not server:
        return None

    # ProxyServer می‌تواند "host:port" یا "http=host:port;https=host:port" باشد
    proxy = None
    for part in server.split(";"):
        if "=" in part:
            scheme, addr = part.split("=", 1)
            if scheme.lower() in ("http", "https", "socks"):
                proxy = addr
                break
        else:
            proxy = part
            break

    if not proxy:
        return None

    host, _, port = proxy.rpartition(":")
    if not host or not port.isdigit():
        return None

    return (host, int(port))


def check_telegram_through_proxy(proxy=None, timeout=5.0):
    """
    تست دسترسی به سرور تلگرام — مستقیم یا از طریق پراکسی HTTP CONNECT
    proxy: (host, port) یا None
    """
    telegram_ip = "149.154.167.51"
    telegram_port = 443

    try:
        if proxy:
            # از طریق پراکسی سیستم: اول به پراکسی وصل شو، بعد CONNECT بزن
            import base64
            sock = socket.create_connection(proxy, timeout=timeout)
            connect_line = (
                f"CONNECT {telegram_ip}:{telegram_port} HTTP/1.1\r\n"
                f"Host: {telegram_ip}:{telegram_port}\r\n\r\n"
            )
            sock.sendall(connect_line.encode())
            response = b""
            sock.settimeout(timeout)
            try:
                while b"\r\n\r\n" not in response:
                    chunk = sock.recv(1024)
                    if not chunk:
                        break
                    response += chunk
            except socket.timeout:
                pass
            ok = b" 200 " in response.split(b"\r\n", 1)[0]
            sock.close()
            return ok
        else:
            # اتصال مستقیم
            sock = socket.create_connection((telegram_ip, telegram_port), timeout=timeout)
            sock.close()
            return True
    except Exception:
        return False


def get_telethon_proxy_args():
    """
    برگرداندن آرگومان‌های proxy برای TelegramClient.
    پراکسی سیستم (HTTP) به‌صورت HTTP proxy به Telethon داده می‌شود.
    اگر پراکسی نباشد: dict خالی (اتصال مستقیم).
    """
    win_proxy = get_windows_proxy()
    if win_proxy:
        host, port = win_proxy
        import socks
        return {"proxy": (socks.HTTP, host, port)}
    return {}
