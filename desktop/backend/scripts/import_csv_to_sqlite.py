from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.app.db import init_db
from backend.app.services.plansheet_service import save_plansheet

SOURCE_DIR = ROOT_DIR.parent / "social" / "plansheet" / "monthly_sheets"
SOURCE_INPUT = ROOT_DIR.parent / "social" / "plansheet" / "input_monthly.json"


def load_input_template(month: str) -> dict:
    if SOURCE_INPUT.is_file():
        with SOURCE_INPUT.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        data["month"] = month
        return data
    return {"month": month}


def import_month(csv_path: Path) -> None:
    month = csv_path.stem
    rows: list[dict[str, str]] = []
    with csv_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            rows.append(dict(row))

    save_plansheet(month, load_input_template(month), rows)
    print(f"Imported {month}: {len(rows)} rows")


def main() -> None:
    init_db()
    if not SOURCE_DIR.is_dir():
        raise FileNotFoundError(f"Source folder not found: {SOURCE_DIR}")

    files = sorted(SOURCE_DIR.glob("*.csv"))
    if not files:
        print(f"No CSV files found in {SOURCE_DIR}")
        return

    for csv_path in files:
        import_month(csv_path)


if __name__ == "__main__":
    main()
