import sys
filepath = r"c:\Users\THAAER\Desktop\pro\production_management\views.py"

with open(filepath, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Define the replacement method
replacement = '''    def _auto_generate_sessions(self, clear_existing=True):
        """Auto-generate production sessions with strict collision solver."""
        exam_entries = ExamScheduleEntry.objects.filter(is_active=True)
        if not exam_entries.exists():
            return

        if clear_existing:
            TeacherProductionSession.objects.filter(status='scheduled').delete()

        TRACK_MAP = {'scientific': 'science', 'literary': 'literal', 'ninth': 'ninth', 'general': 'literal'}
        courses = Course.objects.filter(
            status__in=['published', 'review', 'draft']
        ).select_related('subject', 'instructor')

        schedule_date = PresentationBuilder.SCHEDULE_START_DATE
        allocations = {} 
        items = []
        for c in courses:
            br = TRACK_MAP.get(c.academic_track, 'ninth')
            match = self._find_exam(c.subject.name, br, exam_entries)
            items.append({'c': c, 'e': match, 'd': match.exam_date if match else None, 'b': br})
            
        items.sort(key=lambda x: (x['d'] is None, x['d']))

        for it in items:
            course = it['c']
            exam = it['e']
            ex_date = it['d']
            branch = it['b']
            subject = course.subject.name
            
            if TeacherProductionSession.objects.filter(course=course, exam_date=ex_date).exists():
                continue

            if ex_date:
                s_date = PresentationBuilder.calculate_shooting_date(ex_date, subject, branch, schedule_date)
            else:
                s_date = schedule_date

            # Conflict Solver: Max 2 per day
            while allocations.get(s_date, 0) >= 2:
                s_date -= timedelta(days=1)
                if s_date < PresentationBuilder.SCHEDULE_START_DATE:
                     s_date = schedule_date
                     while allocations.get(s_date, 0) >= 2:
                         s_date += timedelta(days=1)
                     break
            
            if s_date.weekday() == 4: 
                s_date -= timedelta(days=1)

            allocations[s_date] = allocations.get(s_date, 0) + 1
            if allocations.get(schedule_date, 0) >= 2:
                schedule_date += timedelta(days=1)

            price = course.price_cents / 100 if course.price_cents else PresentationBuilder.get_platform_price(subject, branch)

            session = TeacherProductionSession.objects.create(
                course=course,
                teacher_name=course.instructor.get_full_name() or course.instructor.username,
                subject=subject,
                branch=branch,
                exam_date=ex_date,
                exam_time=exam.exam_time if exam else None,
                shooting_date=s_date,
                shooting_time=dt_time(20, 0), # 8 PM
                status='scheduled',
            )
            ProductionCost.objects.create(session=session, platform_price=price)
'''

# We want to replace EXACTLY from line 222 up to line 281.
# In zero-indexed array, that is index 221 up to 281.
new_lines = lines[:221] + [replacement + "\n"] + lines[281:]

with open(filepath, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print("Successfully overwritten method block!")
