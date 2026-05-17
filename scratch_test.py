import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from learning.models import Course

print("Auditing course subjects...")
for course in Course.objects.all():
    try:
        subject_name = course.subject.name if course.subject else "None"
        print(f"Course ID: {course.id}, Subject: {subject_name}")
    except Exception as e:
        print(f"Course ID: {course.id} crashed on subject: {e}")
