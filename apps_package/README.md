# حزمة تطبيقات منصة محترفو التعليمية (Mohtarifo Apps Package)

يحتوي هذا المجلد على كافة نسخ التطبيقات لمنصة محترفو مع منظومة الأمان المتقدمة **(Anti-Screen Capture & Recording Blocker)**.

---

## 📁 محتويات المجلد:

### 1. `download_landing/` (صفحة تحميل التطبيقات)
- صفحة هبوط ذات تصميم فاخر، تقوم بالتعرف التلقائي على نظام الزائر (Auto-detect OS) وتوفير روابط التنزيل المباشرة لكافة المنصات.

### 2. `android/` (نسخة أندرويد - Android App)
- كود Java/Android الأصلي مع تفعيل `FLAG_SECURE` على مستوى النافذة لمنع التقاط لقطات الشاشة أو تسجيل الشاشة وتحويلها إلى شاشة سوداء تماماً.

### 3. `ios/` (نسخة الآيفون والآيباد - iOS App)
- كود Swift مع طبقة `isSecureTextEntry` المتقدمة والاستماع لـ `UIScreen.capturedDidChangeNotification` لإخفاء المحتوى فوراً وإظهار شاشة الحظر التحذيرية عند محاولة التسجيل.

### 4. `desktop/` (نسخة ويندوز وماك بوك - Windows & macOS)
- **Electron Shell**: مدعوم بخاصية `setContentProtection(true)` التي تطبق `SetWindowDisplayAffinity(WDA_EXCLUDEFROMCAPTURE)` في ويندوز وحظر تسجيل النوافذ في macOS ضد برامج OBS، Snagit، وغيرها.
- **Python / PyQt6 Shell**: حل بديل سريع لتشغيل المنصة مع حماية الهاردوير المباشرة.

### 5. `web_security_layer/` (طبقة حماية الويب الموحدة)
- سكريبت `anti_capture_guard.js` الجاهز للحقن في أي متصفح أو WebView لحظر مفاتيح التقاط الشاشة (PrintScreen، Win+Shift+S، Cmd+Shift+3/4/5) وإظهار شاشة الحظر الأمنية الفورية.

---

## 🚀 كيفية بناء وتشغيل حزم التطبيقات:

### تشغيل وبناء تطبيق الديسكتوب (Windows / Mac):
```bash
cd apps_package/desktop
npm install
npm start # للتشغيل التجريبي
npm run build-win # لإنتاج ملف Setup (.exe) للويندوز
npm run build-mac # لإنتاج ملف DMG للماك
```

### تشغيل تطبيق أندرويد (Android Studio):
افتح مجلد `apps_package/android` في Android Studio واضغط على Build APK / Bundle.

### تشغيل تطبيق آيفون (Xcode):
افتح المشروع في Xcode على جهاز Mac مع تحديد `ViewController.swift` وتشغيل المحاكي أو الجهاز الحقيقي.
