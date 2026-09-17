# مشروع منصة محترفو التعليم الموحد (Single Codebase Multiplatform)
**الرابط الموجه للـ WebView:** `https://pro-academy.pro/`

هذا المشروع مبني باستخدام **CapacitorJS** ليسمح لك بإدارة وتعديل كود واحد فقط وبناء تطبيقات لكافة المنصات بضغطة زر واحدة.

---

## 🔒 نظام الحماية المشترك المدمج:
تم تضمين وتفعيل إضافة `@capacitor-community/privacy-screen` رسمياً:
- تقوم بتفعيل `FLAG_SECURE` تلقائياً في الأندرويد.
- تقوم بتفعيل طبقة `Secure View Controller` وإخفاء الشاشة عند التسجيل في الـ iOS.

---

## 🛠️ أوامر العمل المباشرة:

### 1. مزامنة أي تعديل على كل المنصات دفعة واحدة:
```bash
cd apps_package/unified_app
npx cap sync
```

### 2. فتح وبناء تطبيق الأندرويد (Android Studio):
```bash
npx cap open android
```
ثم اضغط **Build -> Build APK** داخل Android Studio.

### 3. فتح وبناء تطبيق الآيفون (Xcode):
```bash
npx cap open ios
```
ثم اضغط **Run** أو **Archive** داخل Xcode.

### 4. تشغيل وبناء تطبيق الديسكتوب (Windows & macOS):
من مجلد `apps_package/desktop`:
```bash
npm start           # تشغيل تجريبي
npm run build-mac   # تصدير DMG للماك
npm run build-win   # تصدير EXE للويندوز
```
