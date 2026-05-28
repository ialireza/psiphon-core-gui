#!/usr/bin/env python3
import sys
import threading
import json
import os
import re
from datetime import datetime
from PySide6.QtWidgets import (QApplication, QMainWindow, QVBoxLayout,
                               QHBoxLayout, QPushButton, QLabel,
                               QWidget, QTextEdit, QMessageBox, QComboBox,
                               QCheckBox, QSpinBox, QGroupBox, QGridLayout)
from PySide6.QtCore import Signal, QObject, Slot, Qt, QSettings, QUrl
from PySide6.QtGui import QFont, QTextCursor, QColor, QDesktopServices, QPalette, QIcon

from psiphon_core import PsiphonTunnel

class LogProcessor:
    @staticmethod
    def parse_timestamp(ts_str):
        try:
            ts_str = ts_str.split('.')[0]
            ts_str = ts_str.replace('Z', '').replace('T', ' ')
            dt = datetime.fromisoformat(ts_str)
            return dt.strftime('%H:%M:%S')
        except:
            return datetime.now().strftime('%H:%M:%S')

    @staticmethod
    def extract_json(line):
        match = re.search(r'(\{.*\})', line)
        if match:
            return match.group(1)
        return None

    @classmethod
    def process_line(cls, line, dark_mode=False):
        line_clean = line.strip()
        time_str = datetime.now().strftime('%H:%M:%S')

        ts_match = re.match(r'^\[?(\d{2}:\d{2}:\d{2})\]?', line_clean)
        if ts_match:
            time_str = ts_match.group(1)
        else:
            ts_match_iso = re.match(r'^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})', line_clean)
            if ts_match_iso:
                time_str = cls.parse_timestamp(ts_match_iso.group(1))

        line_content = re.sub(r'^\[\d{2}:\d{2}:\d{2}\]\s+', '', line_clean)
        line_content = re.sub(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}.*?Z\s+', '', line_content)

        if "Tunnels" in line_clean and '"count"' in line_clean:
            json_str = cls.extract_json(line_clean)
            if json_str:
                try:
                    data = json.loads(json_str)
                    if data.get('count', 0) > 0:
                        return "CONNECTED", f'<span style="color: #4CAF50; font-weight: bold;">[{time_str}] 🚀 اتصال با موفقیت برقرار شد. تعداد تونل‌های فعال: {data.get("count")}</span>'
                except:
                    pass

        if "error" in line_clean.lower() or "failed" in line_clean.lower():
            return "LOG", f'<span style="color: #E91E63; font-weight: bold;">[{time_str}] ❌ {line_content}</span>'

        if "⚠️" in line_clean or "هشدار" in line_clean or "Warning" in line_clean:
            return "LOG", f'<span style="color: #FF9800;">[{time_str}] {line_content}</span>'

        if "ConnectingServer" in line_clean:
            return "LOG", f'<span style="color: #03A9F4;">[{time_str}] 🔍 در حال بررسی و تست سرور جدید...</span>'

        if "start establishing" in line_clean.lower():
            return "LOG", f'<span style="color: #FF9800; font-weight: bold;">[{time_str}] 🔄 فرآیند دست‌تکانی و تونل‌زنی آغاز شد...</span>'

        if "ListeningSocksProxyPort" in line_clean or "SocksProxyListening" in line_clean:
            return "LOG", f'<span style="color: #2196F3; font-weight: bold;">[{time_str}] 🔌 پورت ساکس مپ شد (SOCKS Listening)</span>'
        if "ListeningHttpProxyPort" in line_clean or "HttpProxyListening" in line_clean:
            return "LOG", f'<span style="color: #00BCD4; font-weight: bold;">[{time_str}] 🌐 پورت اچ‌تی‌تی‌پي مپ شد (HTTP Listening)</span>'

        return "LOG", f'<span style="color: #9E9E9E;">[{time_str}] {line_content}</span>'


class TunnelWorker(QObject):
    log_received = Signal(str)
    finished = Signal()
    error_occurred = Signal(str)

    def __init__(self, tunnel):
        super().__init__()
        self.tunnel = tunnel

    def run(self):
        try:
            if self.tunnel.start():
                self.tunnel.read_output(self.handle_log)
            else:
                self.error_occurred.emit("باینری هسته سایفون استارت نشد.")
        except Exception as e:
            self.error_occurred.emit(str(e))
        finally:
            self.finished.emit()

    def handle_log(self, line):
        self.log_received.emit(line)


class PsiphonGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.tunnel = None
        self.worker_thread = None
        self.is_connected = False  # وضعیت اتصال واقعی کلاینت
        self.settings = QSettings("PsiphonManager", "Config")
        self.load_settings()
        self.init_ui()

    def load_settings(self):
        self.app_settings = {
            'socks_port': int(self.settings.value('socks_port', 8087)),
            'http_port': int(self.settings.value('http_port', 8086)),
            'region': self.settings.value('region', ''),
            'dark_mode': self.settings.value('dark_mode', 'false') == 'true',
            'enable_log': self.settings.value('enable_log', 'true') == 'true',
            'show_colors': self.settings.value('show_colors', 'true') == 'true',
            'auto_scroll': self.settings.value('auto_scroll', 'true') == 'true'
        }

    def save_settings(self):
        for key, val in self.app_settings.items():
            if isinstance(val, bool):
                self.settings.setValue(key, 'true' if val else 'false')
            else:
                self.settings.setValue(key, val)

    def init_ui(self):
        self.setWindowTitle("کلاینت سایفون | http://github.com/ialireza")
        self.setMinimumSize(850, 600)
        self.apply_theme()

        icon_path = os.path.join(os.path.dirname(__file__), "icon.png")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        elif os.path.exists("./icon.png"):
            self.setWindowIcon(QIcon("./icon.png"))

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)

        left_panel = QVBoxLayout()
        main_layout.addLayout(left_panel, 1)

        status_group = QGroupBox("وضعیت و اتصال")
        status_layout = QVBoxLayout(status_group)
        self.status_label = QLabel("🔴 متوقف شده")
        self.status_label.setFont(QFont("Arial", 12, QFont.Bold))
        self.status_label.setAlignment(Qt.AlignCenter)
        status_layout.addWidget(self.status_label)

        self.btn_toggle = QPushButton("🚀 اتصال به شبکه")
        self.btn_toggle.setMinimumHeight(45)
        self.btn_toggle.clicked.connect(self.toggle_tunnel)
        status_layout.addWidget(self.btn_toggle)
        left_panel.addWidget(status_group)

        config_group = QGroupBox("تنظیمات کلاینت هسته")
        config_layout = QGridLayout(config_group)

        config_layout.addWidget(QLabel("پورت SOCKS:"), 0, 0)
        self.spin_socks = QSpinBox()
        self.spin_socks.setRange(1, 65535)
        self.spin_socks.setValue(self.app_settings['socks_port'])
        config_layout.addWidget(self.spin_socks, 0, 1)

        config_layout.addWidget(QLabel("پورت HTTP:"), 1, 0)
        self.spin_http = QSpinBox()
        self.spin_http.setRange(1, 65535)
        self.spin_http.setValue(self.app_settings['http_port'])
        config_layout.addWidget(self.spin_http, 1, 1)

        config_layout.addWidget(QLabel("لوکیشن خروجی:"), 2, 0)
        self.combo_region = QComboBox()
        regions = {"": "اتوماتیک", "US": "آمریکا", "DE": "آلمان", "FR": "فرانسه", "IN": "هند"}
        for code, name in regions.items():
            self.combo_region.addItem(name, code)

        index = self.combo_region.findData(self.app_settings['region'])
        if index >= 0:
            self.combo_region.setCurrentIndex(index)
        config_layout.addWidget(self.combo_region, 2, 1)
        left_panel.addWidget(config_group)

        shortcuts_group = QGroupBox("لینک‌های سریع تلگرام")
        shortcuts_layout = QVBoxLayout(shortcuts_group)
        self.btn_tg_link = QPushButton("💡 تولید و باز کردن لینک پروکسی تلگرام")
        self.btn_tg_link.clicked.connect(self.open_telegram_proxy)
        shortcuts_layout.addWidget(self.btn_tg_link)
        left_panel.addWidget(shortcuts_group)

        view_group = QGroupBox("تنظیمات رابط گرافیکی")
        view_layout = QVBoxLayout(view_group)

        self.chk_dark = QCheckBox("حالت تاریک (Dark Mode)")
        self.chk_dark.setChecked(self.app_settings['dark_mode'])
        self.chk_dark.toggled.connect(self.toggle_dark_mode)
        view_layout.addWidget(self.chk_dark)

        self.chk_log = QCheckBox("فعال بودن نمایش زنده لاگ‌ها")
        self.chk_log.setChecked(self.app_settings['enable_log'])
        self.chk_log.toggled.connect(self.toggle_log)
        view_layout.addWidget(self.chk_log)

        self.chk_color = QCheckBox("رنگی‌سازی پیشرفته لاگ کلاینت")
        self.chk_color.setChecked(self.app_settings['show_colors'])
        self.chk_color.toggled.connect(lambda c: self.update_setting('show_colors', c))
        view_layout.addWidget(self.chk_color)

        self.chk_scroll = QCheckBox("اسکرول خودکار")
        self.chk_scroll.setChecked(self.app_settings['auto_scroll'])
        self.chk_scroll.toggled.connect(lambda c: self.update_setting('auto_scroll', c))
        view_layout.addWidget(self.chk_scroll)

        left_panel.addWidget(view_group)
        left_panel.addStretch()

        right_panel = QVBoxLayout()
        main_layout.addLayout(right_panel, 2)

        log_header = QHBoxLayout()
        log_header.addWidget(QLabel("📋 مانیتورینگ خروجی هسته سایفون:"))
        log_header.addStretch()
        btn_clear = QPushButton("🗑️ پاک کردن صفحه")
        btn_clear.clicked.connect(self.clear_log)
        log_header.addWidget(btn_clear)
        right_panel.addLayout(log_header)

        self.output_text = QTextEdit()
        self.output_text.setReadOnly(True)
        self.output_text.setFont(QFont("Monospace", 10))
        right_panel.addWidget(self.output_text)

    def apply_theme(self):
        palette = QPalette()
        if self.app_settings['dark_mode']:
            palette.setColor(QPalette.Window, QColor(40, 44, 52))
            palette.setColor(QPalette.WindowText, Qt.white)
            palette.setColor(QPalette.Base, QColor(28, 30, 34))
            palette.setColor(QPalette.Text, Qt.white)
            palette.setColor(QPalette.Button, QColor(58, 64, 74))
            palette.setColor(QPalette.ButtonText, Qt.white)
        else:
            palette = QApplication.style().standardPalette()
        self.setPalette(palette)

    def toggle_dark_mode(self, checked):
        self.app_settings['dark_mode'] = checked
        self.save_settings()
        self.apply_theme()

    def update_setting(self, key, value):
        self.app_settings[key] = value
        self.save_settings()

    def generate_temp_config(self):
        base_config_path = "./psiphon.config"
        config_data = {}

        if os.path.exists(base_config_path):
            try:
                with open(base_config_path, "r", encoding="utf-8") as f:
                    config_data = json.load(f)
            except:
                pass

        config_data["LocalSocksProxyPort"] = self.spin_socks.value()
        config_data["LocalHttpProxyPort"] = self.spin_http.value()
        config_data["EgressRegion"] = self.combo_region.currentData()
        config_data["EmitDiagnosticNotices"] = True
        config_data["EmitDiagnosticNetworkParameters"] = True

        with open("./psiphon_temp.config", "w", encoding="utf-8") as f:
            json.dump(config_data, f, indent=2, ensure_ascii=False)

    def toggle_tunnel(self):
        if self.tunnel and self.tunnel.running:
            self.btn_toggle.setEnabled(False)
            self.output_text.append('<b><span style="color: #FF5722;">⏳ در حال توقف امن سایفون...</span></b>')
            self.tunnel.stop()
        else:
            self.is_connected = False
            self.app_settings['socks_port'] = self.spin_socks.value()
            self.app_settings['http_port'] = self.spin_http.value()
            self.app_settings['region'] = self.combo_region.currentData()
            self.save_settings()

            self.generate_temp_config()
            self.tunnel = PsiphonTunnel(config_path="./psiphon_temp.config")

            self.worker_thread = threading.Thread(target=self.run_tunnel_worker, daemon=True)
            self.worker_thread.start()

            self.btn_toggle.setText("🛑 قطع اتصال")
            self.status_label.setText("🟡 در حال جستجوی سرور...")
            self.status_label.setStyleSheet("color: #FF9800; font-weight: bold;")
            self.spin_socks.setEnabled(False)
            self.spin_http.setEnabled(False)
            self.combo_region.setEnabled(False)

    def run_tunnel_worker(self):
        worker = TunnelWorker(self.tunnel)
        worker.log_received.connect(self.append_output)
        worker.error_occurred.connect(self.on_core_error)
        worker.finished.connect(self.on_tunnel_stopped)
        worker.run()

    def open_telegram_proxy(self):
        socks_port = self.spin_socks.value()
        tg_url = f"https://t.me/socks?server=127.0.0.1&port={socks_port}"
        self.output_text.append(f'<br><b>💡 لینک پروکسی تلگرام صادر شد:</b>')
        self.output_text.append(f'<a href="{tg_url}">{tg_url}</a><br>')
        QDesktopServices.openUrl(QUrl(tg_url))

    @Slot(str)
    def on_core_error(self, error_msg):
        self.output_text.append(f'<span style="color: #E91E63; font-weight: bold;">❌ خطا در کارکرد هسته: {error_msg}</span>')

    @Slot()
    def on_tunnel_stopped(self):
        self.is_connected = False
        self.btn_toggle.setText("🚀 اتصال به شبکه")
        self.btn_toggle.setEnabled(True)
        self.status_label.setText("🔴 متوقف شده")
        self.status_label.setStyleSheet("color: #F44336; font-weight: bold;")
        self.spin_socks.setEnabled(True)
        self.spin_http.setEnabled(True)
        self.combo_region.setEnabled(True)
        self.output_text.append('<span style="color: #9E9E9E;">⏹️ سایفون متوقف شد.</span>')

        if os.path.exists("./psiphon_temp.config"):
            try: os.remove("./psiphon_temp.config")
            except: pass

    @Slot(str)
    def append_output(self, text):
        if not self.app_settings['enable_log'] or "updated server" in text:
            return

        status_type, processed_text = LogProcessor.process_line(text, self.app_settings['dark_mode'])

        if status_type == "CONNECTED":
            self.is_connected = True
            self.status_label.setText("🟢 متصل شد")
            self.status_label.setStyleSheet("color: #4CAF50; font-weight: bold;")
        elif not self.is_connected and "ConnectingServer" in text:
            self.status_label.setText("🟡 در حال جستجوی سرور...")
            self.status_label.setStyleSheet("color: #FF9800; font-weight: bold;")

        self.output_text.append(processed_text)

        if self.app_settings['auto_scroll']:
            self.output_text.moveCursor(QTextCursor.End)

    def toggle_log(self, checked):
        self.app_settings['enable_log'] = checked
        self.save_settings()

    def clear_log(self):
        self.output_text.clear()

def main():
    if sys.platform.startswith('linux'):
        try:
            os.environ["QT_QPA_PLATFORM"] = "xcb"
        except:
            pass

    app = QApplication(sys.argv)
    gui = PsiphonGUI()
    gui.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
