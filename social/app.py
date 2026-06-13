import csv
import json
import os
import re
import subprocess
from datetime import date
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse


BASE_DIR = Path(__file__).resolve().parent
WEB_DIR = BASE_DIR / "webui"
PLANSHEET_DIR = BASE_DIR / "plansheet" / "monthly_sheets"
PLANSHEET_SCRIPT = BASE_DIR / "plansheet" / "generate_monthly_sheet.py"
INPUT_JSON_FILE = BASE_DIR / "plansheet" / "input_monthly.json"

DEFAULT_COLUMNS = [
    "post_id", "upload_date", "upload_time",
    "title", "description", "hashtags", "keywords",
    "category", "sub_category_name", "series_name", "episode_number",
    "landscape_video_path", "landscape_thumbnail_path",
    "portrait_video_path", "portrait_thumbnail_path",
    "ai_flag", "kids_flag", "status"
]


def _json_response(handler: SimpleHTTPRequestHandler, status: int, payload: dict) -> None:
    raw = json.dumps(payload).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(raw)))
    handler.end_headers()
    handler.wfile.write(raw)


def _month_from_query(handler: SimpleHTTPRequestHandler) -> str | None:
    parsed = urlparse(handler.path)
    params = parse_qs(parsed.query)
    month = params.get("month", [""])[0]
    if not re.fullmatch(r"\d{4}-\d{2}", month):
        return None
    return month


def _csv_path_for_month(month: str) -> Path:
    PLANSHEET_DIR.mkdir(parents=True, exist_ok=True)
    return PLANSHEET_DIR / f"{month}.csv"


def _read_csv(csv_path: Path) -> tuple[list[str], list[dict]]:
    with csv_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        columns = list(reader.fieldnames or DEFAULT_COLUMNS)
        rows = [dict(row) for row in reader]
    return columns, rows


def _write_csv(csv_path: Path, columns: list[str], rows: list[dict]) -> None:
    with csv_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns, quoting=csv.QUOTE_ALL)
        writer.writeheader()
        for row in rows:
            clean = {col: str(row.get(col, "")) for col in columns}
            writer.writerow(clean)


def _read_body(handler: SimpleHTTPRequestHandler) -> dict:
    length = int(handler.headers.get("Content-Length", "0"))
    raw = handler.rfile.read(length)
    if not raw:
        return {}
    return json.loads(raw.decode("utf-8"))


def _run_generator(month: str) -> tuple[bool, str]:
    try:
        with INPUT_JSON_FILE.open("r", encoding="utf-8") as f:
            cfg = json.load(f)
        cfg["month"] = month
        with INPUT_JSON_FILE.open("w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2)

        result = subprocess.run(
            ["python", str(PLANSHEET_SCRIPT)],
            cwd=str(PLANSHEET_SCRIPT.parent),
            capture_output=True,
            text=True,
            timeout=900,
            check=False,
        )
        if result.returncode != 0:
            return False, result.stderr or result.stdout or "Unknown generation error"
        return True, result.stdout
    except Exception as exc:
        return False, str(exc)


class PlansheetHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(WEB_DIR), **kwargs)

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/plansheet":
            month = _month_from_query(self)
            if not month:
                _json_response(self, 400, {"error": "Invalid month format. Use YYYY-MM."})
                return

            csv_path = _csv_path_for_month(month)
            exists = csv_path.is_file()
            if not exists:
                _json_response(self, 200, {
                    "exists": False,
                    "month": month,
                    "columns": DEFAULT_COLUMNS,
                    "rows": [],
                    "current_month": date.today().strftime("%Y-%m"),
                })
                return

            try:
                columns, rows = _read_csv(csv_path)
                _json_response(self, 200, {
                    "exists": True,
                    "month": month,
                    "columns": columns,
                    "rows": rows,
                    "current_month": date.today().strftime("%Y-%m"),
                })
            except Exception as exc:
                _json_response(self, 500, {"error": f"Failed reading CSV: {exc}"})
            return

        super().do_GET()

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/plansheet/save":
            try:
                payload = _read_body(self)
                month = payload.get("month", "")
                columns = payload.get("columns", [])
                rows = payload.get("rows", [])

                if not re.fullmatch(r"\d{4}-\d{2}", month):
                    _json_response(self, 400, {"error": "Invalid month format. Use YYYY-MM."})
                    return
                if not isinstance(columns, list) or not all(isinstance(c, str) for c in columns):
                    _json_response(self, 400, {"error": "Invalid columns payload."})
                    return
                if not isinstance(rows, list):
                    _json_response(self, 400, {"error": "Invalid rows payload."})
                    return

                csv_path = _csv_path_for_month(month)
                _write_csv(csv_path, columns, rows)
                _json_response(self, 200, {"ok": True})
            except Exception as exc:
                _json_response(self, 500, {"error": f"Failed saving CSV: {exc}"})
            return

        if parsed.path == "/api/plansheet/generate":
            try:
                payload = _read_body(self)
                month = payload.get("month", "")
                if not re.fullmatch(r"\d{4}-\d{2}", month):
                    _json_response(self, 400, {"error": "Invalid month format. Use YYYY-MM."})
                    return
                ok, output = _run_generator(month)
                if not ok:
                    _json_response(self, 500, {"error": output})
                    return
                _json_response(self, 200, {"ok": True, "output": output})
            except Exception as exc:
                _json_response(self, 500, {"error": f"Generation failed: {exc}"})
            return

        _json_response(self, 404, {"error": "Not found"})

    def do_DELETE(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/plansheet":
            month = _month_from_query(self)
            if not month:
                _json_response(self, 400, {"error": "Invalid month format. Use YYYY-MM."})
                return

            try:
                csv_path = _csv_path_for_month(month)
                if csv_path.exists():
                    csv_path.unlink()
                _json_response(self, 200, {"ok": True})
            except Exception as exc:
                _json_response(self, 500, {"error": f"Failed removing CSV: {exc}"})
            return

        _json_response(self, 404, {"error": "Not found"})


def run_server(host: str = "127.0.0.1", port: int = 8088) -> None:
    if not WEB_DIR.exists():
        raise FileNotFoundError(f"Web UI directory not found: {WEB_DIR}")

    httpd = ThreadingHTTPServer((host, port), PlansheetHandler)
    print(f"Plansheet UI running at http://{host}:{port}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping server...")
    finally:
        httpd.server_close()


if __name__ == "__main__":
    run_server()
