"""
سیستم ضد شناسایی ربات تلگرام
جلوگیری از شناسایی توسط تلگرام
"""
import random
import time
from datetime import datetime, timedelta
from typing import List, Optional
import json
from pathlib import Path


class AntiDetect:
    """
    سیستم ضد شناسایی هوشمند
    رعایت محدودیت‌های تلگرام و جلوگیری از بن شدن
    """

    def __init__(self):
        self.message_log = []
        self.daily_count = 0
        self.hourly_count = 0
        self.last_hour_reset = datetime.now()
        self.last_day_reset = datetime.now()
        self._load_stats()

    def _load_stats(self):
        """بارگذاری آمار ارسال"""
        stats_file = Path("send_stats.json")
        if stats_file.exists():
            try:
                with open(stats_file, "r", encoding="utf-8") as f:
                    stats = json.load(f)
                    self.daily_count = stats.get("daily_count", 0)
                    last_reset = stats.get("last_day_reset")
                    if last_reset:
                        self.last_day_reset = datetime.fromisoformat(last_reset)
            except (json.JSONDecodeError, IOError):
                pass

    def _save_stats(self):
        """ذخیره آمار ارسال"""
        stats = {
            "daily_count": self.daily_count,
            "last_day_reset": self.last_day_reset.isoformat(),
            "total_sent": len(self.message_log),
        }
        try:
            with open("send_stats.json", "w", encoding="utf-8") as f:
                json.dump(stats, f, ensure_ascii=False, indent=2)
        except IOError:
            pass

    def _reset_counters(self):
        """بازنشانی شمارنده‌ها"""
        now = datetime.now()

        # بازنشانی روزانه
        if now.date() > self.last_day_reset.date():
            self.daily_count = 0
            self.last_day_reset = now

        # بازنشانی ساعتی
        if now - self.last_hour_reset >= timedelta(hours=1):
            self.hourly_count = 0
            self.last_hour_reset = now

    def can_send(self, config: dict) -> tuple[bool, str]:
        """
        بررسی امکان ارسال
        Returns: (می‌تونه بفرسته, دلیل)
        """
        self._reset_counters()

        schedule = config.get("SCHEDULE", {})

        # بررسی ساعت
        current_hour = datetime.now().hour
        start_hour = schedule.get("start_hour", 8)
        end_hour = schedule.get("end_hour", 23)

        if not (start_hour <= current_hour < end_hour):
            return False, f"خارج از ساعت ارسال ({start_hour}:00 تا {end_hour}:00)"

        # بررسی محدودیت ساعتی
        max_per_hour = schedule.get("max_messages_per_hour", 10)
        if self.hourly_count >= max_per_hour:
            return False, f"حد ساعتی رسید ({max_per_hour} پیام/ساعت)"

        # بررسی محدودیت روزانه
        max_per_day = schedule.get("max_messages_per_day", 50)
        if self.daily_count >= max_per_day:
            return False, f"حد روزانه رسید ({max_per_day} پیام/روز)"

        return True, "آماده ارسال"

    def get_random_delay(self, config: dict) -> float:
        """
        محاسبه تاخیر تصادفی
        ایجاد تاخیر انسان‌گونه
        """
        schedule = config.get("SCHEDULE", {})
        min_delay = schedule.get("min_delay", 30)
        max_delay = schedule.get("max_delay", 90)

        # تاخیر پایه تصادفی
        base_delay = random.uniform(min_delay, max_delay)

        # اضافه کردن نویز تصادفی (±20%)
        noise = base_delay * random.uniform(-0.2, 0.2)
        delay = base_delay + noise

        # اطمینان از حداقل تاخیر
        return max(5, delay)

    def get_typing_delay(self, message_length: int) -> float:
        """
        محاسبه تاخیر تایپ
        شبیه‌سازی سرعت تایپ انسان
        """
        # سرعت تایپ متوسط: 40-80 کاراکتر در ثانیه
        chars_per_second = random.uniform(40, 80)
        typing_time = message_length / chars_per_second

        # اضافه کردن مکث‌های تصادفی
        pause_probability = 0.3  # 30% احتمال مکث
        if random.random() < pause_probability:
            pause_time = random.uniform(0.5, 2.0)
            typing_time += pause_time

        return max(1, typing_time)

    def randomize_message(self, message: str, config: dict) -> str:
        """
        تغییر تصادفی پیام
        ایجاد تنوع برای جلوگیری از شناسایی
        """
        anti_config = config.get("ANTI_DETECT", {})

        if not anti_config.get("randomize_content", True):
            return message

        result = message

        # اضافه/حذف ایموجی تصادفی
        if anti_config.get("add_emoji_variation", True):
            result = self._vary_emojis(result)

        # تغییر فاصله‌گذاری
        result = self._vary_spacing(result)

        # اضافه کردن کاراکترهای غیرقابل تشخیص
        if random.random() < 0.1:  # 10% احتمال
            result = self._add_invisible_chars(result)

        return result

    def _vary_emojis(self, message: str) -> str:
        """تغییر ایموجی‌ها"""
        emoji_sets = [
            ["✨", "💫", "⭐", "🌟"],
            ["😊", "😄", "😁", "🙂"],
            ["🔥", "💥", "⚡", "💫"],
            ["👍", "👌", "🙌", "👏"],
            ["❤️", "💕", "💖", "💗"],
            ["🎯", "🎪", "🎨", "🎭"],
        ]

        result = message
        for emoji_set in emoji_sets:
            for emoji in emoji_set:
                if emoji in result:
                    # با احتمال 30% ایموجی رو عوض کن
                    if random.random() < 0.3:
                        new_emoji = random.choice(emoji_set)
                        result = result.replace(emoji, new_emoji, 1)
                    break

        return result

    def _vary_spacing(self, message: str) -> str:
        """تغییر فاصله‌گذاری"""
        # اضافه/حذف فاصله‌های اضافی
        if random.random() < 0.2:
            # اضافه کردن فاصله اضافی
            words = message.split()
            if len(words) > 3:
                idx = random.randint(1, len(words) - 2)
                words.insert(idx, "  ")
                message = " ".join(words)

        return message

    def _add_invisible_chars(self, message: str) -> str:
        """اضافه کردن کاراکترهای نامرئی"""
        invisible_chars = ["\u200b", "\u200c", "\u200d", "\ufeff"]
        char = random.choice(invisible_chars)

        # اضافه کردن در یک موقعیت تصادفی
        if len(message) > 10:
            pos = random.randint(5, len(message) - 5)
            message = message[:pos] + char + message[pos:]

        return message

    def shuffle_targets(self, targets: list) -> list:
        """ترتیب تصادفی گروه‌ها"""
        shuffled = targets.copy()
        random.shuffle(shuffled)
        return shuffled

    def record_send(self, group_id: str, message: str):
        """ثبت ارسال"""
        self._reset_counters()
        self.hourly_count += 1
        self.daily_count += 1

        self.message_log.append({
            "timestamp": datetime.now().isoformat(),
            "group_id": str(group_id),
            "message_preview": message[:50],
        })

        self._save_stats()

    def get_stats(self) -> dict:
        """دریافت آمار"""
        return {
            "daily_count": self.daily_count,
            "hourly_count": self.hourly_count,
            "total_sent": len(self.message_log),
            "last_send": self.message_log[-1] if self.message_log else None,
        }
