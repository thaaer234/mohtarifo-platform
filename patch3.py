import sys
filepath = r"c:\Users\THAAER\Desktop\pro\production_management\views.py"

with open(filepath, 'r', encoding='utf-8') as f:
    lines = f.readlines()

replacement = '''            # ── THE UNBREAKABLE SOLVER WITH HOLIDAY SUPPORT ──
            # Eid Dates for blockout: May 27, 28, 29 of 2026
            from datetime import date as d_type
            EID_BLOCK = [d_type(2026, 5, 27), d_type(2026, 5, 28), d_type(2026, 5, 29)]
            
            walk = s_date
            while True:
                is_friday = (walk.weekday() == 4)
                is_eid = walk in EID_BLOCK
                
                if not is_friday and not is_eid and allocations.get(walk, 0) < 2:
                    s_date = walk
                    break
                walk += timedelta(days=1)
'''

# In views.py previously:
# Line 262 was: # ── THE UNBREAKABLE SOLVER ──
# Walk = s_date starts at 265.
# Replace from 262 to 272 (where walk += timedelta is)
# Zero indexed: 261 up to 272
new_lines = lines[:261] + [replacement + "\n"] + lines[272:]

with open(filepath, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print("Eid holiday blocking implemented successfully!")
