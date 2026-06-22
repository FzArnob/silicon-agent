from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

import requests

LLM_API_URL = os.getenv("LLM_API_URL", "http://localhost:2000")
SCRIPT_MODEL = os.getenv("SCRIPT_MODEL", "qwen/qwen3-14b")
LM_API_TOKEN = os.getenv("LM_API_TOKEN", "")

SYSTEM_PROMPT = """You are an esports script planner.
You convert frame-by-frame structured gameplay analysis into a continuous timing script.
Return JSON only. Do not use markdown.
"""


def _extract_text(output_field: Any) -> str | None:
    if isinstance(output_field, str):
        return output_field.strip()

    if isinstance(output_field, list):
        for item in output_field:
            if isinstance(item, dict) and item.get("type") == "message":
                content = item.get("content", "")
                if isinstance(content, str) and content.strip():
                    return content.strip()
        for item in output_field:
            if isinstance(item, dict):
                content = item.get("content", "")
                if isinstance(content, str) and content.strip():
                    return content.strip()

    return None


def _build_headers(api_token: str) -> dict[str, str]:
    headers = {"Content-Type": "application/json"}
    if api_token.strip():
        headers["Authorization"] = f"Bearer {api_token.strip()}"
    return headers


def load_frame_files(frame_json_dir: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    files = sorted(frame_json_dir.glob("frame_*.json"))

    for path in files:
        obj = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(obj, dict):
            rows.append(obj)

    rows.sort(key=lambda r: (float(r.get("timestamp", 0.0)), int(r.get("frame_number", 0))))
    return rows


def build_timeline(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    timeline: list[dict[str, Any]] = []
    for row in rows:
        vlm = row.get("vlm") if isinstance(row.get("vlm"), dict) else {}
        state = vlm.get("state") if isinstance(vlm.get("state"), dict) else {}
        events = vlm.get("events") if isinstance(vlm.get("events"), list) else []

        timeline.append(
            {
                "frame_number": row.get("frame_number"),
                "timestamp": row.get("timestamp"),
                "state": {
                    "agent": state.get("agent"),
                    "weapon": state.get("weapon"),
                    "health": state.get("health"),
                    "shield": state.get("shield"),
                    "spike_state": state.get("spike_state"),
                    "location": state.get("location"),
                },
                "events": events,
            }
        )

    return timeline


def build_prompt(timeline: list[dict[str, Any]]) -> str:
    return (
        "You are given sequential 2 FPS gameplay JSON.\n"
        "Produce a final narration script with continuous timing windows.\n"
        "Use only timeline facts; no fabrication.\n"
        "Constraints:\n"
        "1) Output JSON array only.\n"
        "2) Each item must be: {start, end, text}.\n"
        "3) Timing must be continuous and non-overlapping.\n"
        "4) Keep pacing suitable for TTS (<= 12 words per 3 seconds).\n"
        "5) Mention important event transitions naturally.\n"
        "\nTimeline JSON:\n"
        + json.dumps(timeline, ensure_ascii=True)
    )


def call_llm(prompt: str, model: str, api_url: str, api_token: str, timeout: int) -> str:
    payload = {
        "model": model,
        "system_prompt": SYSTEM_PROMPT,
        "input": prompt,
    }

    response = requests.post(
        f"{api_url.rstrip('/')}/api/v1/chat",
        headers=_build_headers(api_token),
        json=payload,
        timeout=timeout,
    )
    response.raise_for_status()

    result = response.json()
    text = _extract_text(result.get("output"))
    if not text:
        raise RuntimeError("LLM returned empty output")

    return text


def parse_segments(raw_text: str) -> list[dict[str, Any]] | None:
    cleaned = raw_text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        if len(lines) >= 3:
            cleaned = "\n".join(lines[1:-1]).strip()

    first = cleaned.find("[")
    last = cleaned.rfind("]")
    if first == -1 or last == -1 or last <= first:
        return None

    try:
        parsed = json.loads(cleaned[first : last + 1])
    except json.JSONDecodeError:
        return None

    if isinstance(parsed, list):
        return parsed

    return None


def main() -> None:
    parser = argparse.ArgumentParser(
        description="PoC: Convert sequential frame JSON files into final continuous-timing script."
    )
    parser.add_argument("--frame-json-dir", required=True, help="Directory containing frame_*.json files")
    parser.add_argument("--output", default="final_script.json", help="Output JSON path")
    parser.add_argument("--api-url", default=LLM_API_URL, help="LLM API base URL")
    parser.add_argument("--api-token", default=LM_API_TOKEN, help="Optional bearer token")
    parser.add_argument("--model", default=SCRIPT_MODEL, help="LLM model id")
    parser.add_argument("--timeout", type=int, default=180, help="Request timeout seconds")
    args = parser.parse_args()

    frame_json_dir = Path(args.frame_json_dir).resolve()
    output_path = Path(args.output).resolve()

    rows = load_frame_files(frame_json_dir)
    if not rows:
        raise RuntimeError(f"No frame JSON files found in {frame_json_dir}")

    timeline = build_timeline(rows)
    prompt = build_prompt(timeline)
    llm_text = call_llm(prompt, args.model, args.api_url, args.api_token, args.timeout)

    payload: dict[str, Any] = {
        "source_frame_json_dir": str(frame_json_dir),
        "raw_response": llm_text,
    }

    segments = parse_segments(llm_text)
    if segments is not None:
        payload["segments"] = segments

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")
    print(f"Wrote {output_path}")


if __name__ == "__main__":
    main()
