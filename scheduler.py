"""
زمان‌بند ارسال پیام
مدیریت زمان ارسال و محدودیت‌ها
"""
import random
import time
from datetime import datetime, timedelta
from typing import List, Callable, Optional
import threading
import json
from pathlib import Path


class Scheduler:
    """
    زمان‌بند هوشمند ارسال پیام
    مدیریت زمان‌بندی و محدودیت‌ها
    """

    def __init__(self, anti_detect):
        self.anti_detect = anti_detect
        self.is_running = False
        self.scheduled_tasks = []
        self.send_history = []
        self._load_history()

    def _load_history(self):
        """بارگذاری تاریخچه ارسال"""
        history_file = Path("send_history.json")
        if history_file.exists():
            try:
                with open(history_file, "r", encoding="utf-8") as f:
                    self.send_history = json.load(f)
            except (json.JSONDecodeError, IOError):
                self.send_history = []

    def _save_history(self):
        """ذخیره تاریخچه ارسال"""
        try:
            with open("send_history.json", "w", encoding="utf-8") as f:
                json.dump(self.send_history[-1000:], f, ensure_ascii=False, indent=2)
        except IOError:
            pass

    def schedule_message(
        self,
        message: str,
        targets: List[str],
        delay: Optional[float] = None,
        callback: Optional[Callable] = None,
    ):
        """
        زمان‌بندی ارسال پیام

        Args:
            message: متن پیام
            targets: لیست گروه‌های هدف
            delay: تاخیر قبل از ارسال (ثانیه)
            callback: تابع callback بعد از ارسال
        """
        if delay is None:
            delay = self.anti_detect.get_random_delay({})

        task = {
            "message": message,
            "targets": targets,
            "delay": delay,
            "callback": callback,
            "created_at": datetime.now().isoformat(),
            "scheduled_for": (datetime.now() + timedelta(seconds=delay)).isoformat(),
        }

        self.scheduled_tasks.append(task)

        # شروع تایمر
        timer = threading.Timer(delay, self._execute_task, args=[task])
        timer.daemon = True
        timer.start()

        return task

    def _execute_task(self, task: dict):
        """اجرای وظیفه زمان‌بندی شده"""
        if not self.is_running:
            return

        message = task["message"]
        targets = task["targets"]
        callback = task["callback"]

        # ارسال به هر هدف
        for target in targets:
            # بررسی امکان ارسال
            can_send, reason = self.anti_detect.can_send({})

            if not can_send:
                print(f"⚠️ امکان ارسال نیست: {reason}")
                continue

            # تغییر تصادفی پیام
            randomized_message = self.anti_detect.randomize_message(message, {})

            # اجرای callback
            if callback:
                try:
                    callback(target, randomized_message)
                except Exception as e:
                    print(f"❌ خطا در ارسال: {e}")

            # ثبت ارسال
            self.anti_detect.record_send(target, randomized_message)

            # ذخیره در تاریخچه
            self.send_history.append({
                "timestamp": datetime.now().isoformat(),
                "target": target,
                "message_preview": randomized_message[:50],
            })

            # تاخیر بین ارسال‌ها
            if len(targets) > 1:
                inter_delay = random.uniform(5, 15)
                time.sleep(inter_delay)

        self._save_history()

    def start(self):
        """شروع زمان‌بند"""
        self.is_running = True
        print("✅ زمان‌بند شروع شد")

    def stop(self):
        """توقف زمان‌بند"""
        self.is_running = False
        print("🛑 زمان‌بند متوقف شد")

    def get_pending_tasks(self) -> List[dict]:
        """دریافت وظایف منتظر"""
        now = datetime.now()
        pending = []

        for task in self.scheduled_tasks:
            scheduled_for = datetime.fromisoformat(task["scheduled_for"])
            if scheduled_for > now:
                pending.append(task)

        return pending

    def clear_pending(self):
        """پاک کردن وظایف منتظر"""
        self.scheduled_tasks.clear()
        print("🧹 وظایف منتظر پاک شد")

    def get_stats(self) -> dict:
        """دریافت آمار"""
        return {
            "total_sent": len(self.send_history),
            "pending_tasks": len(self.get_pending_tasks()),
            "is_running": self.is_running,
        }
