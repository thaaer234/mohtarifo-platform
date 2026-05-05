# محترفو التعليم

منصة تعليمية عربية متخصصة في المكثفات والامتحانيات لطلاب المرحلة الثانوية، تجمع بين المحتوى المركز، الاختبارات، تحليل الأداء، وخطة دراسة ذكية.

## ما الموجود الآن

- Prototype واجهة عربية RTL يعمل مباشرة من المتصفح داخل `app/index.html`.
- تطبيق Next.js أولي داخل `apps/web` يحتوي صفحات الطالب والمدرس والإدارة.
- NestJS API أولي داخل `apps/api` يحتوي وحدات Auth, Courses, Exams, Analytics, Study Plan, Billing, Notifications.
- Django Backend داخل `apps/backend` لإدارة المحتوى ولوحات الإدارة والمدرس باستخدام Django Templates و Django Admin.
- Django REST API مفعّل للربط مع Next.js:
  - `/api/v1/courses/`
  - `/api/v1/exams/`
  - `/api/v1/student/dashboard/`
  - `/api/v1/analytics/me/`
  - `/api/v1/study-plan/me/`
  - `/api/v1/online-sessions/`
  - `/api/v1/attendance/me/`
  - `/api/v1/access/redeem/`
  - `/api/v1/access/me/`
- Prisma schema تفصيلي داخل `packages/database/prisma/schema.prisma`.
- Package مشترك للأنواع داخل `packages/shared`.
- تجربة طالب تشمل: لوحة أداء، دورات، مشغل درس، اختبار قصير، تحليل أداء، خطة دراسة، Gamification، ولوحات إدارية أولية.
- وثائق Product, UX, Database, API, Security, AI, Roadmap داخل مجلد `docs`.

## التشغيل

افتح الملف التالي في المتصفح:

```text
app/index.html
```

النموذج القديم لا يحتاج إلى Node.js. التطبيق الجديد يحتاج Node.js و npm.

بعد تثبيت Node.js:

```bash
npm install
npm run dev:web
npm run dev:api
```

ثم افتح:

```text
http://localhost:3000
http://localhost:4000/api/v1/courses
```

## تشغيل Django Dashboard

الداشبورد الخلفي يعمل الآن بدون Node.js، ويستخدم SQLite محليًا للتجربة.

```bash
cd apps/backend
python manage.py migrate
python manage.py seed_demo
python manage.py runserver 8000
```

افتح:

```text
http://127.0.0.1:8000/
http://127.0.0.1:8000/login/
http://127.0.0.1:8000/register/
http://127.0.0.1:8000/student/
http://127.0.0.1:8000/admin/
http://127.0.0.1:8000/api/v1/courses/
```

صفحة الهبوط العامة:

```text
http://127.0.0.1:8000/landing/
```

بيانات الدخول التجريبية:

```text
admin / admin12345
teacher / teacher12345
student / student12345
```

## المسار التقني المقترح

- Frontend: Next.js + Tailwind CSS
- Backend: NestJS
- Database: PostgreSQL
- Cache: Redis
- Queue: BullMQ
- Payments: Stripe ثم PayPal
- Auth: JWT + Refresh Tokens + Rate Limiting

## هدف MVP

إطلاق نسخة مدفوعة أولية خلال 60-90 يوم تتضمن مادة واحدة، 20-30 درسًا، 200-300 سؤال، امتحانات مؤتمتة، تحليل أداء أساسي، وخطة دراسة ذكية.

## فهرس الوثائق

- `docs/product-plan.md`: تعريف المنتج، نطاق MVP، ومؤشرات النجاح.
- `docs/sitemap-and-ux.md`: Sitemap كامل وتصميم تجربة الطالب والمدرس والإدارة.
- `docs/user-journeys.md`: رحلات المستخدم الأساسية.
- `docs/database-design.md`: قاعدة بيانات تفصيلية مناسبة لـ PostgreSQL.
- `docs/api-design.md`: API endpoints ونماذج طلبات وردود.
- `docs/architecture.md`: المعمارية التقنية العامة.
- `docs/performance-security-ai.md`: الأداء، الأمان، الفيديو، والميزات الذكية.
- `docs/design-system.md`: الهوية البصرية والمكونات.
- `docs/roadmap-90-days.md`: خطة تنفيذ 60-90 يوم.
- `docs/future-roadmap.md`: التوسع المستقبلي والتسويق والموبايل.

## مسار التحويل إلى تطبيق كامل

1. تثبيت Node.js و PostgreSQL و Redis.
2. تشغيل `npm install`.
3. ضبط `.env` من `.env.example`.
4. تشغيل `npm run db:generate`.
5. تشغيل `npm run db:migrate` بعد تجهيز PostgreSQL.
6. استبدال mock services في `apps/api` باستعلامات Prisma.
7. ربط `apps/web` مع API بدل بيانات `apps/web/lib/mock-data.ts`.
8. إضافة الدفع والإشعارات قبل الإطلاق التجريبي.

## المسار الأسرع للـ MVP باستخدام Django

إذا قررنا اعتماد Django كباك إند رئيسي بدل NestJS:

1. نقل قاعدة البيانات الإنتاجية إلى PostgreSQL في `apps/backend/config/settings.py`.
2. استخدام Django Admin لإدارة المستخدمين، الدورات، الدروس، بنك الأسئلة، الامتحانات، الاشتراكات.
3. إبقاء Next.js لواجهة الطالب فقط.
4. إضافة Django REST Framework لاحقًا لتغذية Next.js وتطبيق الموبايل.
5. استخدام Celery + Redis للإيميلات، الإشعارات، وتحليلات الأداء الثقيلة.

## الربط الحالي بين Django و Next.js

- الرسم المعماري موجود في `docs/system-map.md`.
- Django هو مصدر البيانات الحالي.
- Next.js يستخدم `apps/web/lib/api.ts`.
- عند تشغيل Django على `http://127.0.0.1:8000`، صفحات Next.js التالية تقرأ من Django API:
  - الصفحة الرئيسية.
  - لوحة الطالب.
  - المواد.
  - الامتحانات.
  - التحليلات.
  - خطة الدراسة.
- إذا لم يكن Django شغالًا، تستخدم الواجهة بيانات mock مؤقتة حتى لا تتعطل تجربة التطوير.

لتغيير رابط API في Next.js:

```bash
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000/api/v1
```

## حالة الجاهزية للنشر

الحالة الحالية: غير جاهز للنشر العام بعد، لكنه جاهز كـ internal prototype أو demo محلي.

أسباب عدم جاهزية الإنتاج:

- Node.js غير مثبت على الجهاز، لذلك لم يتم اختبار build واجهة Next.js.
- Django يعمل حاليًا على SQLite للتجربة، وليس PostgreSQL إنتاجي.
- المصادقة في API لم تتحول بعد إلى JWT/session API لواجهة الطالب.
- أزرار بدء الامتحان في Next.js تعرض الامتحانات لكنها لا تبدأ Attempt حقيقي من الواجهة بعد.
- الدفع، رفع الفيديو، الإشعارات، وحماية المحتوى ما زالت هيكلية وليست production.
- إعدادات الإنتاج مثل `SECRET_KEY`, `DEBUG=False`, static files, logging, backups غير مضبوطة بعد.

ما هو جاهز الآن:

- Django Admin لإدارة المحتوى.
- Dashboard خلفي بالقوالب.
- Models و migrations.
- بيانات تجريبية.
- REST API أساسي.
- ربط Next.js بعدة صفحات مع Django API.
- فحوصات Django الأساسية تمر بنجاح.

## إعدادات Production الأولية

تمت إضافة:

- `apps/backend/requirements.txt`
- `apps/backend/.env.example`
- `apps/backend/Procfile`
- `apps/backend/runtime.txt`
- إعدادات Django تقرأ من environment variables.
- صفحة هبوط عامة `/landing/`.
- إعدادات أمان أساسية تعمل عند `DJANGO_DEBUG=False`.

فحص الإنتاج المحلي:

```bash
$env:DJANGO_DEBUG='False'
$env:DJANGO_SECRET_KEY='prod-secret-key-change-me-with-a-long-random-value'
$env:DJANGO_ALLOWED_HOSTS='your-domain.com,www.your-domain.com'
python manage.py check --deploy
```

النتيجة الحالية عند ضبط env صحيحة:

```text
System check identified no issues
```

قبل النشر العام ما زال مطلوبًا:

- PostgreSQL فعلي.
- استضافة static/media أو S3.
- دومين و HTTPS.
- قيمة سرية قوية لـ `DJANGO_SECRET_KEY`.
- تعطيل `DEBUG`.
- Backups ومراقبة أخطاء.

## قسم الشراء بالكود والحضور

تم إنهاء القسم الأول الخاص بشراء/تفعيل الدروس بالكود وحضور الدروس الأونلاين.

### أكواد الوصول

من Django Admin:

```text
/admin/billing/accesscode/
```

يمكن إنشاء كود يفعّل:

- مادة كاملة.
- درسًا محددًا.
- اشتراكًا مرتبطًا بخطة.

API تفعيل الكود:

```text
POST /api/v1/access/redeem/
```

مثال:

```json
{
  "code": "MATH-2026-DEMO",
  "username": "student"
}
```

عرض صلاحيات الطالب:

```text
GET /api/v1/access/me/
```

### الدروس الأونلاين والحضور

من Django Admin:

```text
/admin/learning/onlinelessonsession/
/admin/learning/lessonattendance/
```

API الجلسات:

```text
GET /api/v1/online-sessions/
GET /api/v1/attendance/me/
```

الكود التجريبي بعد `seed_demo`:

```text
MATH-2026-DEMO
PHYS-2026-DEMO
CHEM-2026-DEMO
```

## بوابة الطالب

الطالب يعمل حساب جديد من:

```text
http://127.0.0.1:8000/register/
```

ثم يسجل دخول من:

```text
http://127.0.0.1:8000/login/
```

بعد الدخول يفتح لوحة الطالب:

```text
http://127.0.0.1:8000/student/
```

من لوحة الطالب يستطيع:

- إدخال كود مادة أو درس.
- رؤية مواده ودروسه المفعّلة.
- فتح تفاصيل المادة من لوحة الطالب.
- فتح الدروس المفعّلة ومشاهدة رابط الفيديو أو ملف PDF.
- تسجيل الدرس كمكتمل وتحديث تقدم المادة.
- رؤية الجلسات الأونلاين القادمة.
- تسجيل الحضور في جلسة أونلاين.
- رؤية حضوره.
- رؤية إشعاراته الداخلية.
- رؤية آخر محاولاته.

مسارات الطالب المهمة:

```text
/student/
/student/courses/<course_id>/
/student/lessons/<lesson_id>/
/student/lessons/<lesson_id>/complete/
/student/sessions/<session_id>/join/
```

## لوحة المدرس

لوحة المدرس:

```text
http://127.0.0.1:8000/instructor/
```

تعرض:

- دورات المدرس.
- عدد الدروس.
- الجلسات الأونلاين.
- حضور الطلاب.
- عدد الطلاب المفعّلين عبر الأكواد.
- روابط سريعة لإضافة دورة، وحدة، درس، جلسة، أو كود.

## لوحة الإدارة المخصصة

لوحة الإدارة المخصصة:

```text
http://127.0.0.1:8000/admin-dashboard/
```

تعرض:

- كل الطلاب.
- المواد والدورات.
- حضور الدروس الأونلاين.
- أكواد الدورات.
- من استخدم كل كود.
- روابط سريعة لإضافة طالب، دورة، درس، كود، وجلسة أونلاين.
