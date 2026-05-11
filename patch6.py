import sys
filepath = r"c:\Users\THAAER\Desktop\pro\production_management\views.py"

with open(filepath, 'r', encoding='utf-8') as f:
    lines = f.readlines()

replacement = '''                # ── TWO-PASS ELASTIC SOLVER (MAXIMIZE SPACING) ──
                # Pass 1: Seek an absolute empty day (count < 1) to avoid stacking
                # Pass 2: Only if failed, relax constraint to partial days (count < 2)
                
                solved = False
                for max_cap in [1, 2]:
                    walk = current_walk
                    local_dir = direction
                    steps = 0
                    
                    while True:
                        is_fri = (walk.weekday() == 4)
                        is_eid = walk in EID_BLOCK
                        
                        if not is_fri and not is_eid and allocations.get(walk, 0) < max_cap:
                            s_date = walk
                            # Advance starting point for immediate next iteration to sustain spreading
                            current_walk = walk + timedelta(days=direction) 
                            solved = True
                            break
                        
                        walk += timedelta(days=local_dir)
                        steps += 1
                        
                        if local_dir == -1 and walk < PresentationBuilder.SCHEDULE_START_DATE:
                             walk = anchor + timedelta(days=1)
                             local_dir = 1
                             
                        if steps > 100:
                             break # Try next capacity phase
                             
                    if solved: break
'''

# Replacing Line 280 down to 302
# Zero-indexed: 279 up to 302
new_lines = lines[:279] + [replacement + "\n"] + lines[302:]

with open(filepath, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print("Uncompressed Elastic Solver deployed.")
