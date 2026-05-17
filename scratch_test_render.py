import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.template.loader import render_to_string
from django.contrib.auth.models import User
from dashboard.views import _get_instructor_context

try:
    u = User.objects.filter(instructor_profile__status='active').first()
    print("Found active instructor user:", u)
    if u:
        class FakeRequest:
            user = u
            GET = {}
            session = {}
        req = FakeRequest()
        ctx = _get_instructor_context(req)
        ctx["request"] = req
        ctx["active_page"] = "courses"
        
        print("Rendering instructor_courses.html...")
        html = render_to_string("dashboard/instructor_courses.html", ctx)
        print("SUCCESS! Rendered length:", len(html))
    else:
        print("No active instructor found in DB!")
except Exception as e:
    import traceback
    print("CRASH DETECTED DURING RENDER:")
    traceback.print_exc()
