import csv
from collections import Counter

CSV_FILE = "..\scene.csv"

with open(CSV_FILE, newline="", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    categories = [row["category"].strip() for row in reader]

counts = Counter(categories)
total_categories = len(counts)
total_scenes = sum(counts.values())

print(f"{'Category':<25} {'Count':>5}  {'%':>6}")
print("-" * 42)
for category, count in sorted(counts.items()):
    pct = count / total_scenes * 100
    print(f"{category:<25} {count:>5}  {pct:>5.1f}%")
print("-" * 42)
print(f"{'Total Categories:':<25} {total_categories:>5}")
print(f"{'Total Scenes:':<25} {total_scenes:>5}  100.0%")
