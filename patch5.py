import sys
filepath = r"c:\Users\THAAER\Desktop\pro\production_management\views.py"

with open(filepath, 'r', encoding='utf-8') as f:
    lines = f.readlines()

replacement = '''            # ── DYNAMIC MULTI-DAY SPLIT & 7-DAY SAFETY SOLVER ──
            num_days = 1
            norm_sub = subject.strip()
            if 'الرياضيات' in norm_sub:
                num_days = 2 if branch == 'ninth' else 3
            elif any(kw in norm_sub for kw in ['الفيزياء', 'الكيمياء', 'العلوم', 'فيزياء']):
                num_days = 2

            from datetime import date as d_type
            EID_BLOCK = [d_type(2026, 5, 27), d_type(2026, 5, 28), d_type(2026, 5, 29)]
            
            if ex_date:
                anchor = PresentationBuilder.calculate_shooting_date(ex_date, subject, branch, PresentationBuilder.SCHEDULE_START_DATE)
                direction = -1 
            else:
                anchor = PresentationBuilder.SCHEDULE_START_DATE
                direction = 1
            
            current_walk = anchor
            price = course.price_cents / 100 if course.price_cents else PresentationBuilder.get_platform_price(subject, branch)
            
            # Automatically spawn multiple discrete operational sessions for large subjects
            for part in range(num_days):
                s_date = None
                steps = 0
                walk = current_walk 
                
                while True:
                    is_fri = (walk.weekday() == 4)
                    is_eid = walk in EID_BLOCK
                    
                    if not is_fri and not is_eid and allocations.get(walk, 0) < 2:
                        s_date = walk
                        # Important: Advance walk for next sub-session immediately to avoid stacking on same day
                        current_walk = walk + timedelta(days=direction) 
                        break
                    
                    walk += timedelta(days=direction)
                    steps += 1
                    
                    if direction == -1 and walk < PresentationBuilder.SCHEDULE_START_DATE:
                         walk = anchor + timedelta(days=1)
                         direction = 1
                    if steps > 100:
                         s_date = walk
                         break
                
                allocations[s_date] = allocations.get(s_date, 0) + 1

                # Construct split metadata
                part_label = f" ({part+1}/{num_days})" if num_days > 1 else ""
                
                session = TeacherProductionSession.objects.create(
                    course=course,
                    teacher_name=course.instructor.get_full_name() or course.instructor.username,
                    subject=f"{subject}{part_label}",
                    branch=branch,
                    exam_date=ex_date,
                    exam_time=exam.exam_time if exam else None,
                    shooting_date=s_date,
                    shooting_time=dt_time(20, 0),
                    status='scheduled',
                )
                # Split total cost estimate evenly among the operational session days
                ProductionCost.objects.create(session=session, platform_price=(price / float(num_days)))
'''

# Replace from lines 256 to 307
new_lines = lines[:255] + [replacement + "\n"] + lines[307:]

with open(filepath, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print("Sub-session multiplexer injected successfully!")
