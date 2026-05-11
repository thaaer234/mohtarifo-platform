import sys
filepath = r"c:\Users\THAAER\Desktop\pro\production_management\views.py"

with open(filepath, 'r', encoding='utf-8') as f:
    lines = f.readlines()

replacement = '''            if ex_date:
                # Get default anchor (usually few days before exam)
                s_date = PresentationBuilder.calculate_shooting_date(ex_date, subject, branch, PresentationBuilder.SCHEDULE_START_DATE)
            else:
                s_date = PresentationBuilder.SCHEDULE_START_DATE

            # ── THE UNBREAKABLE SOLVER ──
            # Start from candidate, step FORWARD until we hit a Non-Friday Day with < 2 items.
            # This yields a PERFECT, collision-free allocation matrix.
            walk = s_date
            while True:
                is_friday = (walk.weekday() == 4)
                if not is_friday and allocations.get(walk, 0) < 2:
                    s_date = walk
                    break
                walk += timedelta(days=1)

            # ── LOCK ALLOCATION ──
            allocations[s_date] = allocations.get(s_date, 0) + 1

            price = course.price_cents / 100 if course.price_cents else PresentationBuilder.get_platform_price(subject, branch)
'''

# We replace from line 256 "if ex_date:" down to line 275 "schedule_date += timedelta(days=1)"
# Zero indexed: 255 up to 275
new_lines = lines[:255] + [replacement + "\n"] + lines[275:]

with open(filepath, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print("Fixed the overlapping overflow bug successfully!")
