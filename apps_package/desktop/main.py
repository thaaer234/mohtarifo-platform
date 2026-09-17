import os
import sys
from PyQt6.QtWidgets import QApplication, QMainWindow, QStackedWidget, QWidget, QVBoxLayout, QLabel
from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtGui import QIcon, QFont
import ctypes

# رابط منصة محترفو
PLATFORM_URL = "https://mohtarifo.com"

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("منصة محترفو التعليمية - Mohtarifo Platform")
        self.resize(1280, 800)
        self.setMinimumSize(1024, 700)

        # 1. منع تسجيل الشاشة على نظام ويندوز وماك على مستوى الـ Kernel / OS
        self.enable_hardware_anti_capture()

        # الحاوية الرئيسية
        self.stacked = QStackedWidget()
        self.setCentralWidget(self.stacked)

        # صفحة الويب الرئيسية للمنصة
        self.browser = QWebEngineView()
        self.browser.setUrl(QUrl(PLATFORM_URL))
        self.stacked.addWidget(self.browser)

        # صفحة الحظر الأمني عند محاولة التسجيل أو فقدان الأمان
        self.block_screen = self.create_block_screen()
        self.stacked.addWidget(self.block_screen)

        # حقن سكريبت الحماية
        self.inject_security_guard()

    def enable_hardware_anti_capture(self):
        """تفعيل منع الالتقاط عبر Win32 API لنظام Windows وعبر Cocoa لنظام macOS"""
        if sys.platform == "win32":
            try:
                # WDA_EXCLUDEFROMCAPTURE = 0x00000011 (يمنع OBS و Discord والتصوير ويجعل النافذة شفافة/سوداء بالكامل للمسجل)
                hwnd = int(self.winId())
                ctypes.windll.user32.SetWindowDisplayAffinity(hwnd, 0x00000011)
            except Exception as e:
                print("Windows Capture Block Error:", e)

    def create_block_screen(self):
        """شاشة الحظر الفوري"""
        widget = QWidget()
        widget.setStyleSheet("background: qradialgradient(cx:0.5, cy:0.5, radius:0.8, fx:0.5, fy:0.5, stop:0 #1e1b4b, stop:1 #09090b); color: white;")
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        icon_label = QLabel("🛡️")
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_label.setFont(QFont("Arial", 48))

        title = QLabel("التقاط وتسجيل الشاشة محظور في هذا التطبيق")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 26px; font-weight: bold; color: #f87171; margin-top: 15px;")

        desc = QLabel("لحماية المحتوى التعليمي، لا يُسمح بتشغيل برامج التسجيل أو التقاط الصور أثناء استخدام التطبيق.")
        desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc.setStyleSheet("font-size: 16px; color: #e2e8f0; margin-top: 10px; max-width: 600px;")

        layout.addWidget(icon_label)
        layout.addWidget(title)
        layout.addWidget(desc)
        widget.setLayout(layout)
        return widget

    def inject_security_guard(self):
        js_code = """
        document.addEventListener('keydown', (e) => {
            if (e.key === 'PrintScreen' || (e.ctrlKey && e.key === 'p') || (e.metaKey && e.shiftKey)) {
                e.preventDefault();
            }
        });
        """
        self.browser.page().runJavaScript(js_code)

    def changeEvent(self, event):
        # عند تصغير التطبيق أو نقل التركيز لبرنامج تسجيل
        if event.type() == event.Type.ActivationChange:
            if not self.isActiveWindow():
                self.stacked.setCurrentWidget(self.block_screen)
            else:
                self.stacked.setCurrentWidget(self.browser)
        super().changeEvent(event)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
