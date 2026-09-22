"""
ربات تلگرام هوشمند با سیستم ضد شناسایی
"""
import asyncio
import logging
from datetime import datetime
from typing import Optional

from telegram import Update, Bot
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
from telegram.constants import ParseMode

from config import BOT_TOKEN, TARGET_GROUPS, SCHEDULE, ANTI_DETECT, LOGGING
from anti_detect import AntiDetect
from message_templates import MessageTemplates
from scheduler import Scheduler


# تنظیم لاگ
if LOGGING.get("enabled"):
    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=getattr(logging, LOGGING.get("log_level", "INFO")),
        handlers=[
            logging.FileHandler(LOGGING.get("log_file", "bot.log"), encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )
logger = logging.getLogger(__name__)


class TelegramBot:
    """
    ربات تلگرام هوشمند
    """

    def __init__(self):
        self.anti_detect = AntiDetect()
        self.templates = MessageTemplates()
        self.scheduler = Scheduler(self.anti_detect)
        self.bot: Optional[Bot] = None

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """دستور شروع"""
        user = update.effective_user
        welcome = self.templates.get_welcome_message()

        await update.message.reply_text(welcome)
        logger.info(f"User {user.username} started the bot")

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """دستور راهنما"""
        help_text = self.templates.get_help_message()
        await update.message.reply_text(help_text)

    async def send_message_command(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """دستور ارسال پیام"""
        if not context.args:
            await update.message.reply_text(
                " usage: /send <message>\nExample: /send Hello everyone!"
            )
            return

        message = " ".join(context.args)

        # ارسال به گروه‌های هدف
        success_count = 0
        for group_id in TARGET_GROUPS:
            try:
                # تغییر تصادفی پیام
                randomized = self.anti_detect.randomize_message(message, {})

                # ارسال
                await context.bot.send_message(
                    chat_id=group_id,
                    text=randomized,
                )

                # ثبت ارسال
                self.anti_detect.record_send(group_id, randomized)
                success_count += 1

                logger.info(f"Message sent to {group_id}")

                # تاخیر بین ارسال‌ها
                if len(TARGET_GROUPS) > 1:
                    import random
                    delay = random.uniform(5, 15)
                    await asyncio.sleep(delay)

            except Exception as e:
                logger.error(f"Failed to send to {group_id}: {e}")

        await update.message.reply_text(
            f"✅ پیام به {success_count} گروه ارسال شد"
        )

    async def schedule_command(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """دستور زمان‌بندی ارسال"""
        if not context.args:
            await update.message.reply_text(
                " usage: /schedule <message>\nExample: /schedule Hello!"
            )
            return

        message = " ".join(context.args)

        # زمان‌بندی ارسال
        def send_callback(target, msg):
            asyncio.create_task(
                context.bot.send_message(chat_id=target, text=msg)
            )

        self.scheduler.schedule_message(
            message=message,
            targets=TARGET_GROUPS,
            callback=send_callback,
        )

        await update.message.reply_text(
            "⏰ پیام زمان‌بندی شد!\nارسال با تاخیر تصادفی انجام می‌شه."
        )

    async def stats_command(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """دستور نمایش آمار"""
        stats = self.anti_detect.get_stats()
        scheduler_stats = self.scheduler.get_stats()

        text = f"""
📊 آمار ربات:

📨 ارسال شده امروز: {stats['daily_count']}
📨 ارسال شده این ساعت: {stats['hourly_count']}
📨 کل ارسال شده: {stats['total_sent']}

⏰ وظایف منتظر: {scheduler_stats['pending_tasks']}
▶️ وضعیت: {'فعال' if scheduler_stats['is_running'] else 'غیرفعال'}
"""
        await update.message.reply_text(text)

    async def handle_message(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """پردازش پیام‌های دریافتی"""
        message = update.message.text
        user = update.effective_user

        # لاگ کردن پیام
        logger.info(f"Message from {user.username}: {message[:50]}")

    def run(self):
        """اجرای ربات"""
        print("\n" + "=" * 50)
        print("🤖 ربات تلگرام هوشمند")
        print("=" * 50)
        print(f"📌 توکن: {BOT_TOKEN[:20]}...")
        print(f"👥 گروه‌ها: {len(TARGET_GROUPS)}")
        print(f"⏰ ساعت فعال: {SCHEDULE['start_hour']}:00 تا {SCHEDULE['end_hour']}:00")
        print("=" * 50 + "\n")

        # ساخت Application
        application = Application.builder().token(BOT_TOKEN).build()

        # اضافه کردن Handlerها
        application.add_handler(CommandHandler("start", self.start))
        application.add_handler(CommandHandler("help", self.help_command))
        application.add_handler(CommandHandler("send", self.send_message_command))
        application.add_handler(CommandHandler("schedule", self.schedule_command))
        application.add_handler(CommandHandler("stats", self.stats_command))
        application.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message)
        )

        # شروع زمان‌بند
        self.scheduler.start()

        # اجرای ربات
        print("✅ ربات شروع به کار کرد!")
        print("🛑 برای توقف: Ctrl+C\n")

        application.run_polling(allowed_updates=Update.ALL_TYPES)


def main():
    """تابع اصلی"""
    try:
        bot = TelegramBot()
        bot.run()
    except KeyboardInterrupt:
        print("\n🛑 ربات متوقف شد")
    except Exception as e:
        print(f"❌ خطا: {e}")


if __name__ == "__main__":
    main()
