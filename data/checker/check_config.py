import csv
from collections import Counter

csv_file = "..\config.csv"
with open(csv_file, 'r', encoding='utf-8', newline='') as f:
    reader = csv.DictReader(f)
    all_rows = list(reader)

new_rows = all_rows[1:]  # skip original "Professional White"
total = len(new_rows)

wide = sum(1 for r in new_rows if 'ultrawide' in r['Monitors'].lower() or '49' in r['Monitors'] or '45' in r['Monitors'] or '40' in r['Monitors'] or '34' in r['Monitors'] or '57' in r['Monitors'])
figs = sum(1 for r in new_rows if r['Action Figures'].strip() and r['Action Figures'].strip().lower() != 'none')
lcd = sum(1 for r in new_rows if 'lcd' in r['CPU Cooler'].lower())

names = [r['Setup Name'] for r in all_rows]
dupes = [(k,v) for k,v in Counter(names).items() if v > 1]

print(f"Total data rows: {len(all_rows)}")
print(f"New rows added: {total}")
print(f"Wide displays: {wide} ({wide*100//total}%)")
print(f"Action figures: {figs} ({figs*100//total}%)")
print(f"LCD coolers: {lcd} ({lcd*100//total}%)")
print(f"Unique names: {len(set(names))}")
print(f"Duplicates: {len(dupes)}")
if dupes:
    fieldnames = list(all_rows[0].keys())
    for name, count in dupes:
        print(f"\n  {name}: {count}x")
        matching_rows = [r for r in all_rows if r['Setup Name'] == name]
        # Compare each pair
        for i in range(len(matching_rows)):
            for j in range(i + 1, len(matching_rows)):
                total_fields = len(fieldnames)
                same_fields = sum(1 for f in fieldnames if matching_rows[i][f] == matching_rows[j][f])
                similarity = same_fields * 100 // total_fields
                print(f"    Row pair ({i+1} vs {j+1}): {same_fields}/{total_fields} fields match = {similarity}% similarity")
                if similarity < 100:
                    for f in fieldnames:
                        if matching_rows[i][f] != matching_rows[j][f]:
                            print(f"      [{f}] \"{matching_rows[i][f][:50]}\" vs \"{matching_rows[j][f][:50]}\"")
