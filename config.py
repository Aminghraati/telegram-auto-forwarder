"""
تنظیمات ربات تلگرام
"""

# توکن ربات (از BotFather بگیر)
BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"

# لیست گروه‌های هدف (چت‌آیدی یا یوزرنیم)
# برای پیدا کردن چت‌آیدی گروه:
# 1. ربات رو به گروه اضافه کن
# 2. یه پیام بفرست
# 3. به https://api.telegram.org/bot<TOKEN>/getUpdates بریم
TARGET_GROUPS = [
    # -1001234567890,  # چت‌آیدی گروه ۱
    # "@group_username",  # یوزرنیم گروه ۲
]

# تنظیمات زمان‌بندی
SCHEDULE = {
    "min_delay": 30,        # حداقل تاخیر بین پیام‌ها (ثانیه)
    "max_delay": 90,        # حداکثر تاخیر بین پیام‌ها (ثانیه)
    "start_hour": 8,        # ساعت شروع ارسال
    "end_hour": 23,         # ساعت پایان ارسال
    "max_messages_per_hour": 10,  # حداکثر پیام در ساعت
    "max_messages_per_day": 50,   # حداکثر پیام در روز
}

# تنظیمات ضد شناسایی
ANTI_DETECT = {
    "randomize_content": True,    # تغییر تصادفی محتوا
    "add_emoji_variation": True,  # تنوع ایموجی
    "typing_simulation": True,    # شبیه‌سازی تایپ
    "variable_delays": True,      # تاخیرهای متغیر
    "shuffle_order": True,        # ترتیب تصادفی گروه‌ها
}

# تنظیمات لاگ
LOGGING = {
    "enabled": True,
    "log_file": "bot.log",
    "log_level": "INFO",
}
