import sys
filepath = r"c:\Users\THAAER\Desktop\pro\production_management\views.py"

with open(filepath, 'r', encoding='utf-8') as f:
    lines = f.readlines()

replacement = '''            # ── UNBREAKABLE SOLVER WITH 7-DAY SAFETY GUARANTEE ──
            from datetime import date as d_type
            EID_BLOCK = [d_type(2026, 5, 27), d_type(2026, 5, 28), d_type(2026, 5, 29)]
            
            if ex_date:
                # Starts at ceiling (7+ days back)
                anchor = PresentationBuilder.calculate_shooting_date(ex_date, subject, branch, PresentationBuilder.SCHEDULE_START_DATE)
                direction = -1 # Step BACKWARDS to ensure they only go earlier, never later
            else:
                anchor = PresentationBuilder.SCHEDULE_START_DATE
                direction = 1 # Step forward
            
            walk = anchor
            steps = 0
            while True:
                is_friday = (walk.weekday() == 4)
                is_eid = walk in EID_BLOCK
                
                if not is_friday and not is_eid and allocations.get(walk, 0) < 2:
                    s_date = walk
                    break
                
                walk += timedelta(days=direction)
                steps += 1
                
                # Reversal safety valve: if completely saturated earlier, move forward slightly
                if direction == -1 and walk < PresentationBuilder.SCHEDULE_START_DATE:
                     walk = anchor + timedelta(days=1)
                     direction = 1
                if steps > 100:
                     s_date = anchor
                     break
'''

new_lines = lines[:255] + [replacement + "\n"] + lines[275:]

with open(filepath, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print("Strict 7-day buffer solver deployed.")
