from django.core.management.base import BaseCommand
from learning.models import Lesson, fetch_bunny_video_duration

class Command(BaseCommand):
    help = "Syncs empty video lesson durations from Bunny.net API"

    def handle(self, *args, **options):
        lessons = Lesson.objects.filter(lesson_type="video", duration_seconds__isnull=True)
        self.stdout.write(self.style.NOTICE(f"Found {lessons.count()} video lessons with missing durations."))

        success_count = 0
        for lesson in lessons:
            if lesson.video_url:
                self.stdout.write(f"Fetching duration for: {lesson.title} ({lesson.video_url})...")
                duration = fetch_bunny_video_duration(lesson.video_url)
                if duration:
                    lesson.duration_seconds = duration
                    lesson.save(update_fields=["duration_seconds"])
                    self.stdout.write(self.style.SUCCESS(f"Updated duration to {duration} seconds."))
                    success_count += 1
                else:
                    self.stdout.write(self.style.WARNING(f"Could not retrieve duration for: {lesson.title}"))

        self.stdout.write(self.style.SUCCESS(f"Successfully synced {success_count} lessons."))
