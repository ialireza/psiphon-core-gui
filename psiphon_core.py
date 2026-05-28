#!/usr/bin/env python3
import sys
import os
import subprocess
import threading

# 📌 پیدا کردن مسیر دقیق دایرکتوری جاری برنامه
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 📌 تشخیص خودکار مسیر باینری هسته سایفون بر اساس سیستم‌عامل
if sys.platform.startswith('win'):
    # اگر کاربر ویندوز بود، دنبال فایل اجرایی باینری ویندوز می‌گردد
    CORE_BINARY = os.path.join(BASE_DIR, "psiphon-tunnel-core-i686.exe")
else:
    # اگر لینوکس یا سیستم‌عامل دیگری بود، از نسخه لینوکسی استفاده می‌کند
    CORE_BINARY = os.path.join(BASE_DIR, "psiphon-tunnel-core-x86_64")


class PsiphonTunnel:
    """کلاس مدیریت و کنترل فرآیندها و اجرای کلاینت هسته سایفون"""

    def __init__(self, config_path="./psiphon_temp.config", data_dir="./psiphon_data"):
        self.config_path = os.path.abspath(config_path)
        self.data_dir = os.path.abspath(data_dir)
        self.process = None
        self.running = False
        self._read_thread = None

    def start(self):
        """راه‌اندازی و اجرای امن فرآیند کلاینت هسته"""
        if self.running:
            return True

        # بررسی وجود فایل باینری هسته قبل از اجرا
        if not os.path.exists(CORE_BINARY):
            raise FileNotFoundError(f"باینری هسته سایفون در مسیر مشخص شده یافت نشد:\n{CORE_BINARY}")

        # در لینوکس، مطمئن می‌شویم فایل باینری اجازه اجرا (Execution Permission) دارد
        if not sys.platform.startswith('win'):
            try:
                os.chmod(CORE_BINARY, 0o755)
            except Exception as e:
                print(f"⚠️ خطای دسترسی تمیز به باینری: {e}")

        # آماده‌سازی آرگومان‌های خط فرمان برای اجرای هسته سایفون
        cmd = [
            CORE_BINARY,
            "-config", self.config_path,
            "-dataDir", self.data_dir
        ]

        try:
            # ایجاد پروسس جدید و هدایت استاندارد خروجی‌ها (stdout/stderr)
            # استفاده از creationflags در ویندوز برای جلوگیری از باز شدن پاپ‌آپ‌های CMD مزاحم
            creation_flags = 0
            if sys.platform.startswith('win'):
                creation_flags = subprocess.CREATE_NO_WINDOW

            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                encoding='utf-8',
                errors='ignore',
                creationflags=creation_flags
            )
            self.running = True
            return True
        except Exception as e:
            self.running = False
            raise RuntimeError(f"خطا در زمان استارت پروسس باینری سایفون: {e}")

    def read_output(self, callback_func):
        """خواندن لاگ‌های خروجی باینری به صورت زنده بدون فریز کردن برنامه"""
        def reader():
            while self.running and self.process:
                line = self.process.stdout.readline()
                if not line:
                    break
                # فرستادن لاگ خام دریافتی به متد بک‌تراک رابط گرافیکی
                callback_func(line)

            # وقتی حلقه تمام شود یعنی پروسس متوقف شده است
            self.running = False

        self._read_thread = threading.Thread(target=reader, daemon=True)
        self._read_thread.start()

    def stop(self):
        """توقف امن و کامل پروسس باینری سایفون و آزادسازی پورت‌ها"""
        self.running = False
        if self.process:
            try:
                # تلاش برای بستن پروسس به صورت استاندارد
                self.process.terminate()
                self.process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                # اگر پروسس در زمان معین بسته نشد، آن را فُورس کیل (Kill) می‌کنیم
                try:
                    self.process.kill()
                except:
                    pass
            except:
                pass
            finally:
                self.process = None
