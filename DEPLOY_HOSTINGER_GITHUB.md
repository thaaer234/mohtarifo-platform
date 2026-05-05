# رفع مشروع Django على Hostinger VPS عبر GitHub

هذا الدليل يشرح الرفع من الصفر: GitHub للكود، PostgreSQL لقاعدة البيانات، Gunicorn لتشغيل Django، و Nginx لاستقبال الزوار.

## 1. ما هي قاعدة البيانات؟

محليا المشروع يستخدم غالبا:

```text
db.sqlite3
```

هذا مناسب للتجربة على جهازك، لكنه غير مناسب للإنتاج. على Hostinger VPS سنستخدم:

```text
PostgreSQL
```

الترتيب سيكون هكذا:

```text
GitHub
  يحتوي الكود فقط

Hostinger VPS
  يشغل Django
  يشغل PostgreSQL
  يحتوي ملف .env الحقيقي
  يحتوي ملفات media الخاصة بالمستخدمين
```

قاعدة الإنتاج المقترحة:

```text
Database name: mohtarifo
Database user: mohtarifo
Database host: localhost
Database port: 5432
```

البيانات الحالية من SQLite تنتقل إلى PostgreSQL عبر ملف مؤقت:

```text
data_dump_production.json
```

مهم جدا: هذا الملف يحتوي مستخدمين وبيانات، لذلك لا ترفعه على GitHub.

## 2. ماذا نرفع على GitHub؟

نرفع الكود فقط:

```text
accounts/
analytics/
billing/
config/
dashboard/
exams/
learning/
static/
templates/
manage.py
requirements.txt
Procfile
runtime.txt
.env.example
.gitignore
README.md
DEPLOY_HOSTINGER_GITHUB.md
```

ولا نرفع:

```text
.env
db.sqlite3
data_dump_production.json
hostinger-django-deploy.zip
media/
staticfiles/
*.log
__pycache__/
```

## 3. تجهيز GitHub من جهازك

افتح Terminal داخل مجلد المشروع:

```bash
cd "C:\Users\THAAER\Desktop\pro"
```

إن لم يكن المشروع Git repository بعد:

```bash
git init
git add .
git commit -m "Initial Django project"
```

أنشئ repository جديد على GitHub باسم مثل:

```text
mohtarifo-platform
```

لا تضف README من GitHub إذا كان عندك README محلي.

بعد الإنشاء سيعطيك GitHub رابط مثل:

```text
https://github.com/YOUR_USERNAME/mohtarifo-platform.git
```

اربط المشروع المحلي:

```bash
git branch -M main
git remote add origin https://github.com/thaaer234/mohtarifo-platform.git
git push -u origin main
```

إذا طلب تسجيل دخول، استخدم GitHub account أو Personal Access Token حسب إعدادات جهازك.

## 4. نقل البيانات من SQLite إلى PostgreSQL، اختياري

هذه الخطوة مطلوبة فقط إذا تريد نقل البيانات الموجودة حاليا داخل `db.sqlite3` إلى قاعدة PostgreSQL على السيرفر.

إذا كانت البيانات الحالية وهمية أو تجريبية، لا تنقلها. الأفضل أن تبدأ PostgreSQL نظيفة على Hostinger، ثم تنشئ مدير جديد وتضيف البيانات الحقيقية من لوحة الإدارة.

إذا قررت نقل البيانات الحالية، جهز dump من قاعدة SQLite المحلية:

```bash
python manage.py dumpdata --exclude contenttypes --exclude auth.permission --exclude sessions --exclude admin.logentry --indent 2 -o data_dump_production.json
```

هذا الملف ننقله للسيرفر يدويا عبر SFTP أو SCP، ولا نضعه في GitHub.

مثال باستخدام SCP من جهازك:

```bash
scp data_dump_production.json root@SERVER_IP:/var/www/mohtarifo/
```

إذا لم تستخدم SCP، ارفعه من File Manager أو SFTP في Hostinger.

أما إذا لا تريد نقل البيانات، تجاهل أوامر `dumpdata` و `loaddata` بالكامل. على السيرفر بعد `migrate` أنشئ حساب مدير جديد:

```bash
python manage.py createsuperuser
```

ثم افتح لوحة الإدارة وأدخل البيانات الحقيقية مباشرة في PostgreSQL.

## 5. اختيار السيرفر في Hostinger

في شاشة Hostinger اختر أقرب موقع لك ولطلابك. إذا أعطاك:

```text
Germany - Best latency
```
thaaer7426thsh@SH
thaaer7426thsh@SH
اختيار Germany جيد.

يفضل اختيار Ubuntu Server، مثلا:

```text
Ubuntu 24.04 LTS
```

بعد إنشاء VPS خذ:

```text
SERVER_IP
root password
```

ثم ادخل SSH:

```bash
ssh root@SERVER_IP
```

## 6. تجهيز السيرفر

على السيرفر نفذ:

```bash
apt update && apt upgrade -y
apt install -y python3 python3-venv python3-pip nginx postgresql postgresql-contrib redis-server git
```

تأكد أن الخدمات تعمل:

```bash
systemctl status postgresql
systemctl status nginx
systemctl status redis-server
```

## 7. إنشاء قاعدة PostgreSQL

ادخل إلى PostgreSQL:

```bash
sudo -u postgres psql
```

نفذ الأوامر التالية، وغير كلمة السر:

```sql
CREATE DATABASE mohtarifo;
CREATE USER mohtarifo WITH PASSWORD 'PUT_STRONG_PASSWORD_HERE';
ALTER ROLE mohtarifo SET client_encoding TO 'utf8';
ALTER ROLE mohtarifo SET default_transaction_isolation TO 'read committed';
ALTER ROLE mohtarifo SET timezone TO 'Asia/Damascus';
GRANT ALL PRIVILEGES ON DATABASE mohtarifo TO mohtarifo;
\q
```

مع PostgreSQL 15 وما بعده، نفذ أيضا:

```bash
sudo -u postgres psql -d mohtarifo
```

ثم:

```sql
GRANT ALL ON SCHEMA public TO mohtarifo;
ALTER SCHEMA public OWNER TO mohtarifo;
\q
```

## 8. سحب المشروع من GitHub

أنشئ مجلد المشروع:

```bash
mkdir -p /var/www
cd /var/www
```

اسحب المشروع:

```bash
git clone https://github.com/YOUR_USERNAME/mohtarifo-platform.git mohtarifo
cd /var/www/mohtarifo
```

## 9. إنشاء بيئة Python

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

## 10. إنشاء ملف البيئة .env على السيرفر

لا ترفع `.env` إلى GitHub. أنشئه فقط على السيرفر:

```bash
nano /var/www/mohtarifo/.env
```

إذا لم تربط الدومين بعد وتريد التجربة على IP فقط:

```env
DJANGO_SECRET_KEY=PUT_LONG_RANDOM_SECRET_HERE
DJANGO_DEBUG=False
DJANGO_SITE_URL=http://SERVER_IP
DJANGO_ALLOWED_HOSTS=SERVER_IP
DJANGO_CORS_ALLOWED_ORIGINS=http://SERVER_IP
DJANGO_CSRF_TRUSTED_ORIGINS=http://SERVER_IP
DJANGO_DB_ENGINE=django.db.backends.postgresql
DJANGO_DB_NAME=mohtarifo
DJANGO_DB_USER=mohtarifo
DJANGO_DB_PASSWORD=PUT_STRONG_PASSWORD_HERE
DJANGO_DB_HOST=localhost
DJANGO_DB_PORT=5432
DJANGO_SECURE_SSL_REDIRECT=False
DJANGO_SECURE_HSTS_SECONDS=0
DJANGO_SESSION_COOKIE_SAMESITE=Lax
DJANGO_CSRF_COOKIE_SAMESITE=Lax
DJANGO_LOG_LEVEL=INFO
DJANGO_ENABLE_ADMIN_BACKUP_EXPORT=False
DJANGO_LOGIN_RATE_LIMIT_ATTEMPTS=10
DJANGO_LOGIN_RATE_LIMIT_TIMEOUT_SECONDS=900
REDIS_URL=redis://127.0.0.1:6379/1
DRF_THROTTLE_AUTH_LOGIN=20/hour
DRF_THROTTLE_BILLING_REDEEM=10/hour
DRF_THROTTLE_EXAM_START=30/hour
DRF_THROTTLE_EXAM_SUBMIT=60/hour
```

إذا صار عندك دومين، استخدم:

```env
DJANGO_ALLOWED_HOSTS=your-domain.com,www.your-domain.com
DJANGO_SITE_URL=https://your-domain.com
DJANGO_CORS_ALLOWED_ORIGINS=https://your-domain.com
DJANGO_CSRF_TRUSTED_ORIGINS=https://your-domain.com
DJANGO_SECURE_SSL_REDIRECT=True
DJANGO_SECURE_HSTS_SECONDS=31536000
```

لتوليد secret key قوي:

```bash
python - <<'PY'
from django.core.management.utils import get_random_secret_key
print(get_random_secret_key())
PY
```

## 11. تجهيز Django على السيرفر

داخل المشروع:

```bash
cd /var/www/mohtarifo
source .venv/bin/activate
python manage.py check
python manage.py migrate
python manage.py collectstatic --noinput
```

إذا تريد نقل بياناتك الحالية من SQLite:

```bash
python manage.py loaddata data_dump_production.json
```

إذا لم تنقل البيانات لأن البيانات المحلية وهمية أو تجريبية، أنشئ مدير جديد:

```bash
python manage.py createsuperuser
```

## 12. تجهيز مجلد media

إذا لديك صور أو ملفات مرفوعة محليا داخل `media/`، انقلها للسيرفر:

```bash
scp -r media root@SERVER_IP:/var/www/mohtarifo/
```

ثم على السيرفر:

```bash
chown -R www-data:www-data /var/www/mohtarifo/media
chmod -R 775 /var/www/mohtarifo/media
```

إذا لا توجد ملفات مهمة داخل media، أنشئ المجلد فقط:

```bash
mkdir -p /var/www/mohtarifo/media
chown -R www-data:www-data /var/www/mohtarifo/media
chmod -R 775 /var/www/mohtarifo/media
```

## 13. اختبار Gunicorn يدويا

```bash
cd /var/www/mohtarifo
source .venv/bin/activate
gunicorn config.wsgi:application --bind 0.0.0.0:8000
```

افتح:

```text
http://SERVER_IP:8000
```

إذا اشتغل، أوقفه بـ Ctrl+C.

## 14. تشغيل Gunicorn كخدمة systemd

أنشئ ملف الخدمة:

```bash
nano /etc/systemd/system/mohtarifo.service
```

ضع:

```ini
[Unit]
Description=Mohtarifo Django App
After=network.target postgresql.service redis-server.service

[Service]
User=www-data
Group=www-data
WorkingDirectory=/var/www/mohtarifo
EnvironmentFile=/var/www/mohtarifo/.env
ExecStart=/var/www/mohtarifo/.venv/bin/gunicorn config.wsgi:application --workers 3 --bind unix:/run/mohtarifo.sock
Restart=always

[Install]
WantedBy=multi-user.target
```

أعط الصلاحيات:

```bash
chown -R www-data:www-data /var/www/mohtarifo
```

شغل الخدمة:

```bash
systemctl daemon-reload
systemctl enable mohtarifo
systemctl start mohtarifo
systemctl status mohtarifo
```

لمشاهدة الأخطاء:

```bash
journalctl -u mohtarifo -n 100 --no-pager
```

## 15. إعداد Nginx

أنشئ ملف Nginx:

```bash
nano /etc/nginx/sites-available/mohtarifo
```

إذا تستخدم IP فقط:

```nginx
server {
    listen 80;
    server_name SERVER_IP;

    client_max_body_size 100M;

    location /static/ {
        alias /var/www/mohtarifo/staticfiles/;
    }

    location /media/ {
        alias /var/www/mohtarifo/media/;
    }

    location / {
        proxy_pass http://unix:/run/mohtarifo.sock;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

إذا تستخدم دومين:

```nginx
server {
    listen 80;
    server_name your-domain.com www.your-domain.com;

    client_max_body_size 100M;

    location /static/ {
        alias /var/www/mohtarifo/staticfiles/;
    }

    location /media/ {
        alias /var/www/mohtarifo/media/;
    }

    location / {
        proxy_pass http://unix:/run/mohtarifo.sock;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

فعل الموقع:

```bash
ln -s /etc/nginx/sites-available/mohtarifo /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
nginx -t
systemctl restart nginx
```

افتح:

```text
http://SERVER_IP
```

أو:

```text
http://your-domain.com
```

## 16. ربط الدومين

من لوحة الدومين أضف DNS record:

```text
Type: A
Name: @
Value: SERVER_IP
TTL: Auto
```

ولـ www:

```text
Type: CNAME
Name: www
Value: your-domain.com
TTL: Auto
```

أو:

```text
Type: A
Name: www
Value: SERVER_IP
TTL: Auto
```

انتظر انتشار DNS، ثم جرب:

```bash
ping your-domain.com
```

## 17. تركيب SSL

بعد أن يعمل الدومين على HTTP:

```bash
apt install -y certbot python3-certbot-nginx
certbot --nginx -d your-domain.com -d www.your-domain.com
```

بعد SSL عدل `.env`:

```bash
nano /var/www/mohtarifo/.env
```

واجعل:

```env
DJANGO_CORS_ALLOWED_ORIGINS=https://your-domain.com
DJANGO_CSRF_TRUSTED_ORIGINS=https://your-domain.com
DJANGO_SITE_URL=https://your-domain.com
DJANGO_SECURE_SSL_REDIRECT=True
DJANGO_SECURE_HSTS_SECONDS=31536000
```

ثم:

```bash
systemctl restart mohtarifo
systemctl restart nginx
```

اختبر تجديد الشهادة:

```bash
certbot renew --dry-run
```

بعد تشغيل الدومين والـ SSL، افتح Google Search Console وأضف الدومين، ثم أرسل sitemap:

```text
https://your-domain.com/sitemap.xml
```

وتأكد أن الملفات التالية تعمل:

```text
https://your-domain.com/robots.txt
https://your-domain.com/sitemap.xml
```

## 18. طريقة تحديث الموقع بعد أي تعديل

على جهازك:

```bash
git add .
git commit -m "Describe your change"
git push
```

على السيرفر:

```bash
cd /var/www/mohtarifo
git pull
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --noinput
systemctl restart mohtarifo
```

إذا تغيرت static أو CSS:

```bash
python manage.py collectstatic --noinput
systemctl restart nginx
```

## 19. أوامر فحص مهمة

حالة Django service:

```bash
systemctl status mohtarifo
```

آخر أخطاء Django:

```bash
journalctl -u mohtarifo -n 100 --no-pager
```

فحص Nginx:

```bash
nginx -t
systemctl status nginx
```

آخر أخطاء Nginx:

```bash
tail -n 100 /var/log/nginx/error.log
```

فحص اتصال PostgreSQL:

```bash
sudo -u postgres psql -d mohtarifo -c "\dt"
```

فحص Django:

```bash
cd /var/www/mohtarifo
source .venv/bin/activate
python manage.py check
```

## 20. نسخ احتياطي

نسخة احتياطية من PostgreSQL:

```bash
mkdir -p /var/backups/mohtarifo
pg_dump -U mohtarifo -h localhost mohtarifo > /var/backups/mohtarifo/mohtarifo_$(date +%F).sql
```

نسخة media:

```bash
tar -czf /var/backups/mohtarifo/media_$(date +%F).tar.gz /var/www/mohtarifo/media
```

استعادة قاعدة البيانات:

```bash
psql -U mohtarifo -h localhost mohtarifo < backup.sql
```

## 21. مشاكل شائعة وحلها

### DisallowedHost

المشكلة أن الدومين أو IP غير موجود في:

```env
DJANGO_ALLOWED_HOSTS
```

أضفه ثم:

```bash
systemctl restart mohtarifo
```

### CSRF verification failed

أضف رابط الموقع إلى:

```env
DJANGO_CSRF_TRUSTED_ORIGINS
```

مثال:

```env
DJANGO_CSRF_TRUSTED_ORIGINS=https://your-domain.com
```

ثم:

```bash
systemctl restart mohtarifo
```

### static لا تظهر

نفذ:

```bash
cd /var/www/mohtarifo
source .venv/bin/activate
python manage.py collectstatic --noinput
nginx -t
systemctl restart nginx
```

### 502 Bad Gateway

افحص خدمة Django:

```bash
systemctl status mohtarifo
journalctl -u mohtarifo -n 100 --no-pager
```

غالبا السبب خطأ في `.env` أو قاعدة البيانات أو requirements.

### خطأ PostgreSQL permission denied for schema public

نفذ:

```bash
sudo -u postgres psql -d mohtarifo
```

ثم:

```sql
GRANT ALL ON SCHEMA public TO mohtarifo;
ALTER SCHEMA public OWNER TO mohtarifo;
\q
```

ثم:

```bash
python manage.py migrate
```

## 22. الخلاصة

الخطة النهائية:

```text
1. نرفع الكود إلى GitHub.
2. لا نرفع .env ولا db.sqlite3 ولا data_dump_production.json.
3. على Hostinger VPS ننزل الكود بـ git clone.
4. ننشئ PostgreSQL database.
5. ننشئ .env على السيرفر.
6. نشغل migrate و collectstatic.
7. ننقل البيانات بـ loaddata إذا بدنا بيانات SQLite الحالية.
8. نشغل Gunicorn عبر systemd.
9. نربط Nginx.
10. نركب SSL بعد ربط الدومين.
```
