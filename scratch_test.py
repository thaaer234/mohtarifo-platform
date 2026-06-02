import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.db import connection
with connection.cursor() as cursor:
    cursor.execute("SELECT datname FROM pg_database WHERE datistemplate = false;")
    dbs = cursor.fetchall()
    print("--- POSTGRES DATABASES ---")
    for db in dbs:
        print(db[0])
