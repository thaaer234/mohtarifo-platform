# دليل تشغيل وتجميع تطبيقات منصة محترفو التعليم (Pro Academy)
**الرابط الرسمي المعتمد للـ WebView:** `https://pro-academy.pro/`

---

## 🍏 1. كيفية بناء نسخة الآيفون (iOS & iPad):
1. افتح تطبيق **Xcode** على جهاز الماك.
2. اختر **Create New Project** -> **iOS** -> **App**.
3. اجعل لغة المشروع **Swift** والواجهة **SwiftUI**.
4. انسخ محتوى الملف التالي وضعه في `ContentView.swift` أو `App.swift`:
   - المسار: [`apps_package/ios/MohtarifoApp.swift`](file:///Users/thaaer/Desktop/لابتوب%20قديم/pro/apps_package/ios/MohtarifoApp.swift)
5. في إعدادات المشروع (Signing & Capabilities):
   - اختر حساب المطور الخاص بك (Apple Developer Team).
6. من القائمة العلوية اختر جهازك أو المحاكي واضغط **Run (⌘ + R)** أو **Product -> Archive** لرفعها إلى App Store / TestFlight.

---

## 🤖 2. كيفية استخراج APK الأندرويد (Android Release APK):
1. افتح تطبيق **Android Studio**.
2. اختر **Open** وافتح مجلد: [`apps_package/android`](file:///Users/thaaer/Desktop/لابتوب%20قديم/pro/apps_package/android).
3. من القائمة العلوية اختر **Build** -> **Build Bundle(s) / APK(s)** -> **Build APK(s)**.
4. سيتم إنشاء ملف `app-debug.apk` أو `app-release.apk` جاهز للتثبيت الفوري على أي هاتف أندرويد.

---

## 💻 3. نسخة الماك والويندوز (macOS & Windows):
* **تطبيق الماك:**
  يتم بناؤه وتصديره مباشرة عبر:
  ```bash
  cd apps_package/desktop
  npm run build-mac
  ```
  تجد الحزمة الناتجة في مجلد: `apps_package/desktop/dist/` بصيغة `.dmg` أو `.app`.

* **تطبيق الويندوز:**
  يتم تصديره عبر الأمر:
  ```bash
  cd apps_package/desktop
  npm run build-win
  ```
  تجد الحزمة الناتجة في مجلد: `apps_package/desktop/dist/` بصيغة `.exe`.
