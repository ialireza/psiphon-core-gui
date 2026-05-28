#!/usr/bin/env python3
import subprocess
import sys
import os
import signal
import time

class PsiphonTunnel:
    def __init__(self, binary_path="./psiphon-tunnel-core-x86_64", config_path="./psiphon_temp.config"):
        self.binary_path = binary_path
        self.config_path = config_path
        self.process = None
        self.running = False

    def start(self):
        """باینری سایفون را با کانفیگ مشخص شده اجرا می‌کند"""
        if self.running:
            print("تونل از قبل در حال اجراست.")
            return False

        # بررسی وجود فایل‌ها
        if not os.path.exists(self.binary_path):
            print(f"خطا: فایل باینری در مسیر {self.binary_path} پیدا نشد.")
            return False
        if not os.path.exists(self.config_path):
            print(f"خطا: فایل کانفیگ در مسیر {self.config_path} پیدا نشد.")
            return False
        if not os.access(self.binary_path, os.X_OK):
            print(f"خطا: فایل باینری قابل اجرا نیست. دستور chmod +x {self.binary_path} را بزنید.")
            return False

        try:
            # ایجاد پوشه دیتای سایفون در صورت عدم وجود جهت کش کردن سرورها
            os.makedirs("./psiphon_data", exist_ok=True)

            # اجرای باینری با سوئیچ‌های استاندارد تایید شده در ترمینال
            self.process = subprocess.Popen(
                [self.binary_path, "-config", self.config_path, "-formatNotices", "-dataRootDirectory", "./psiphon_data"],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,  # ادغام استریم خطا با خروجی اصلی
                text=True,
                bufsize=1,
                preexec_fn=os.setsid if sys.platform != 'win32' else None
            )
            self.running = True
            return True
        except Exception as e:
            print(f"خطا در اجرای فرآیند سایفون: {e}")
            self.running = False
            return False

    def stop(self):
        """فرآیند سایفون را به صورت امن متوقف می‌کند"""
        if not self.running or self.process is None:
            print("فرآیندی برای توقف وجود ندارد.")
            return False

        try:
            print("در حال توقف فرآیند سایفون...")
            if sys.platform == 'win32':
                self.process.terminate()
            else:
                # ارسال سیگنال سیستمی به کل گروه فرآیند
                os.killpg(os.getpgid(self.process.pid), signal.SIGTERM)

            try:
                self.process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                print("فرآیند با TERM بسته نشد، از KILL استفاده می‌کنم.")
                if sys.platform == 'win32':
                    self.process.kill()
                else:
                    os.killpg(os.getpgid(self.process.pid), signal.SIGKILL)
                self.process.wait()

            self.running = False
            print("فرآیند متوقف شد.")
            return True
        except Exception as e:
            print(f"خطا در توقف فرآیند: {e}")
            return False

    def read_output(self, callback=None):
        """خروجی فرآیند را خط به خط می‌خواند و با callback پردازش می‌کند"""
        if not self.running or self.process is None or self.process.stdout is None:
            print("فرآیند در حال اجرا نیست یا خروجی ندارد.")
            return

        try:
            for line in self.process.stdout:
                line = line.strip()
                if line:
                    if callback:
                        callback(line)
                    else:
                        print(f"[سایفون] {line}")
        except Exception as e:
            print(f"خطا در خواندن خروجی: {e}")
        finally:
            self.running = False
            print("فرآیند سایفون به پایان رسید.")
