"""
الگوهای پیام ربات تلگرام
قالب‌های متنوع برای جلوگیری از شناسایی
"""
import random
from typing import List, Optional


class MessageTemplates:
    """
    مدیریت الگوهای پیام
    ایجاد پیام‌های متنوع و طبیعی
    """

    def __init__(self):
        self.templates = self._load_templates()

    def _load_templates(self) -> dict:
        """بارگذاری الگوها"""
        return {
            # الگوهای تبلیغاتی
            "promo": [
                "🔥 {text}\n\n👆 حتماً ببینید!",
                "⭐ {text}\n\n💡 پیشنهاد ویژه!",
                "🎯 {text}\n\n✅ کاملاً رایگان!",
                "🚀 {text}\n\n⏰ محدود!",
                "💎 {text}\n\n🌟 ارزش دیدن داره!",
            ],

            # الگوهای اطلاع‌رسانی
            "info": [
                "📢 {text}",
                "ℹ️ {text}",
                "📝 {text}",
                "📰 {text}",
                "🔔 {text}",
            ],

            # الگوهای تعاملی
            "engagement": [
                "🤔 {text}\n\nنظر شما چیه؟",
                "💬 {text}\n\nکامنت بذارید!",
                "🎯 {text}\n\nشما هم امتحان کنید!",
                "👆 {text}\n\nلایک فراموش نشه!",
            ],

            # الگوهای ساده
            "simple": [
                "{text}",
                "{text} ✨",
                "👉 {text}",
                "{text} 👇",
            ],

            # الگوهای فارسی
            "persian": [
                "🇮🇷 {text}",
                "🌙 {text}",
                "☀️ {text}",
                "🌸 {text}",
                "🎭 {text}",
            ],
        }

    def get_message(
        self,
        text: str,
        template_type: Optional[str] = None,
        custom_emoji: Optional[str] = None,
    ) -> str:
        """
        تولید پیام با الگو

        Args:
            text: متن اصلی پیام
            template_type: نوع الگو (promo, info, engagement, simple, persian)
            custom_emoji: ایموجی سفارشی

        Returns:
            پیام نهایی
        """
        # انتخاب نوع الگو
        if template_type is None:
            template_type = random.choice(list(self.templates.keys()))

        # انتخاب الگو تصادفی
        template = random.choice(self.templates[template_type])

        # جایگزینی متن
        message = template.format(text=text)

        # اضافه کردن ایموجی سفارشی
        if custom_emoji:
            message = f"{custom_emoji} {message}"

        return message

    def add_template(self, template_type: str, template: str):
        """افزودن الگوی جدید"""
        if template_type not in self.templates:
            self.templates[template_type] = []
        self.templates[template_type].append(template)

    def get_random_emoji(self) -> str:
        """دریافت ایموجی تصادفی"""
        emojis = [
            "✨", "💫", "⭐", "🌟", "🔥", "💥", "⚡", "💫",
            "😊", "😄", "😁", "🙂", "👍", "👌", "🙌", "👏",
            "❤️", "💕", "💖", "💗", "🎯", "🎪", "🎨", "🎭",
            "🚀", "💎", "🌟", "🎉", "🎊", "🎈", "🎁", "🎀",
        ]
        return random.choice(emojis)

    def split_long_message(
        self,
        message: str,
        max_length: int = 4096,
        separator: str = "\n\n"
    ) -> List[str]:
        """
        تقسیم پیام‌های طولانی
        تلگرام حداکثر 4096 کاراکتر مجازه
        """
        if len(message) <= max_length:
            return [message]

        parts = []
        current_part = ""

        paragraphs = message.split(separator)

        for paragraph in paragraphs:
            if len(current_part) + len(paragraph) + len(separator) <= max_length:
                current_part += paragraph + separator
            else:
                if current_part:
                    parts.append(current_part.strip())
                current_part = paragraph + separator

        if current_part:
            parts.append(current_part.strip())

        return parts

    def get_welcome_message(self, group_name: Optional[str] = None) -> str:
        """پیام خوشامدگویی"""
        if group_name:
            return f"سلام! 👋\nمن ربات این گروه هستم.\nخوش اومدید {group_name}! 🌟"
        return "سلام! 👋\nمن ربات این گروه هستم.\nخوش اومدید! 🌟"

    def get_help_message(self) -> str:
        """پیام راهنما"""
        return """
🤖 راهنمای ربات:

📌 دستورات:
/start - شروع ربات
/help - نمایش راهنما
/info - اطلاعات ربات

💡 نکته:
این ربات پیام‌های خودکار ارسال می‌کنه.
برای توقف، از دستور /stop استفاده کنید.
"""
