with open('dashboard/views.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if 'def _filter_financial_rows' in line:
        print(f"Line {i+1}: {line}")
        # print the next 100 lines
        for j in range(i, min(i+100, len(lines))):
            print(f"{j+1}: {lines[j]}", end='')
        break
