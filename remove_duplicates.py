import csv

csv_file = r"c:\xampp\htdocs\silicon-agent\config.csv"

with open(csv_file, 'r', encoding='utf-8', newline='') as f:
    reader = csv.DictReader(f)
    fieldnames = reader.fieldnames
    all_rows = list(reader)

print(f"Before: {len(all_rows)} rows")

seen = set()
unique_rows = []
removed = 0
for row in all_rows:
    key = tuple(row[f] for f in fieldnames)
    if key in seen:
        removed += 1
        print(f"  Removed duplicate: {row['Setup Name']}")
    else:
        seen.add(key)
        unique_rows.append(row)

print(f"Removed: {removed} exact duplicates")
print(f"After: {len(unique_rows)} rows")

with open(csv_file, 'w', encoding='utf-8', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames, quoting=csv.QUOTE_MINIMAL)
    writer.writeheader()
    for row in unique_rows:
        writer.writerow(row)

print("Done. CSV rewritten.")
