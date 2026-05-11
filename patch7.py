import sys
filepath = r"c:\Users\THAAER\Desktop\pro\production_management\views.py"

with open(filepath, 'r', encoding='utf-8') as f:
    lines = f.readlines()

replacement = '''                # ── HARD-BOUNDED SPATIAL SCHEDULER (17/5 - 15/6) ──
                from datetime import date as d_t
                HARD_END = d_t(2026, 6, 15)
                
                solved = False
                # We iterate capacities: First try 1 per day. If box fills up, allow 2 per day.
                # This dynamically squeezes everything into the 17/5 -> 15/6 box without leaking past June 15.
                for max_cap in [1, 2, 3]: 
                    walk = current_walk
                    local_dir = direction
                    steps = 0
                    
                    while True:
                        # 1. CHECK BOUNDARIES (Crucial constraint)
                        if walk > HARD_END:
                             break # Exceeded Hard Deadline, restart this loop with HIGHER density/cap
                        
                        is_fri = (walk.weekday() == 4)
                        is_eid = walk in EID_BLOCK
                        
                        if not is_fri and not is_eid and allocations.get(walk, 0) < max_cap:
                            s_date = walk
                            current_walk = walk + timedelta(days=direction) 
                            solved = True
                            break
                        
                        # 2. TAKE NEXT STEP
                        walk += timedelta(days=local_dir)
                        steps += 1
                        
                        # 3. REVERSAL LOGIC (Historical Wall)
                        if local_dir == -1 and walk < PresentationBuilder.SCHEDULE_START_DATE:
                             # We backed up to May 17 and found no empty slots. Let's now scan forward towards June 15!
                             walk = anchor + timedelta(days=1)
                             local_dir = 1
                             
                        if steps > 60: 
                             break 
                             
                    if solved: break

                # Total Safe Fallback (just in case mathematical anomaly, keep it on May 17)
                if not s_date:
                    s_date = PresentationBuilder.SCHEDULE_START_DATE
'''

# Replace from line 280 to line 312 (lines[279] to lines[312])
new_lines = lines[:279] + [replacement + "\n"] + lines[312:]

with open(filepath, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print("Hard Boundary Scheduler Lockdown deployed!")
