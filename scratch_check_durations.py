import os
import sys
import django

sys.path.append(r"c:\Users\THAAER\Desktop\pro")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from production_management.models import TeacherProductionSession

sessions = TeacherProductionSession.objects.all()
print(f"Total sessions: {sessions.count()}")
for s in sessions:
    print(f"ID: {s.id}, Teacher: {s.teacher_name}, Subject: {s.subject}, Duration: {s.shooting_duration_days}, Status: {s.status}")
