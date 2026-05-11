import sys
filepath = r"c:\Users\THAAER\Desktop\pro\production_management\views.py"

with open(filepath, 'r', encoding='utf-8') as f:
    lines = f.readlines()

replacement = '''            # ── DYNAMIC BLOCK ALLOCATION SCHEDULER ──
            num_days = 1
            norm_sub = subject.strip()
            if 'الرياضيات' in norm_sub:
                num_days = 2 if branch == 'ninth' else 3
            elif any(kw in norm_sub for kw in ['الفيزياء', 'الكيمياء', 'العلوم', 'فيزياء']):
                num_days = 2

            from datetime import date as d_t
            EID_BLOCK = [d_t(2026, 5, 27), d_t(2026, 5, 28), d_t(2026, 5, 29)]
            HARD_END = d_t(2026, 6, 22)
            
            if ex_date:
                anchor = PresentationBuilder.calculate_shooting_date(ex_date, subject, branch, PresentationBuilder.SCHEDULE_START_DATE)
                direction = -1 
            else:
                anchor = PresentationBuilder.SCHEDULE_START_DATE
                direction = 1
            
            final_span = []
            s_date = None
            solved = False
            
            # ATOMIC BLOCK VALIDATOR
            for max_cap in [1, 2, 3]:
                walk = current_walk
                local_dir = direction
                steps = 0
                while True:
                    if walk > HARD_END: break
                    
                    candidate_span = []
                    b_walk = walk
                    is_valid_start = True
                    
                    while len(candidate_span) < num_days:
                        if b_walk > HARD_END:
                             is_valid_start = False
                             break
                        
                        if b_walk.weekday() != 4 and b_walk not in EID_BLOCK:
                             if allocations.get(b_walk, 0) < max_cap:
                                  candidate_span.append(b_walk)
                             else:
                                  is_valid_start = False 
                                  break
                        b_walk += timedelta(days=1)
                    
                    if is_valid_start and len(candidate_span) == num_days:
                        s_date = walk 
                        final_span = candidate_span
                        current_walk = walk + timedelta(days=direction)
                        solved = True
                        break
                    
                    walk += timedelta(days=local_dir)
                    steps += 1
                    if local_dir == -1 and walk < PresentationBuilder.SCHEDULE_START_DATE:
                         walk = anchor + timedelta(days=1)
                         local_dir = 1
                    if steps > 60: break
                    
                if solved: break

            if not s_date:
                s_date = PresentationBuilder.SCHEDULE_START_DATE
                final_span = [s_date]
                
            for locked_day in final_span:
                 allocations[locked_day] = allocations.get(locked_day, 0) + 1

            price = course.price_cents / 100 if course.price_cents else PresentationBuilder.get_platform_price(subject, branch)
            
            session = TeacherProductionSession.objects.create(
                course=course,
                teacher_name=course.instructor.get_full_name() or course.instructor.username,
                subject=subject,
                branch=branch,
                exam_date=ex_date,
                exam_time=exam.exam_time if exam else None,
                shooting_date=s_date,
                shooting_time=dt_time(20, 0),
                shooting_duration_days=num_days, 
                status='scheduled',
            )
            ProductionCost.objects.create(session=session, platform_price=price)
'''

# Perform replacement from index 255 to 342
new_lines = lines[:255] + [replacement + "\n"] + lines[342:]

with open(filepath, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print("Supersonic Atomic Block Scheduler has replaced iterative generator perfectly!")
