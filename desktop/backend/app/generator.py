from __future__ import annotations

import calendar
import json
import os
import re
import uuid
from datetime import date, datetime, timedelta
from typing import Any

import requests

LLM_API_URL = os.getenv("LLM_API_URL", "http://localhost:2000")
LLM_MODEL = os.getenv("LLM_MODEL", "google/gemma-4-e2b")

POST_KEYS = ["date_time", "title", "description", "hashtags", "keywords"]


def build_response_schema(total_posts: int) -> dict[str, Any]:
    """JSON Schema the model is forced to decode into.

    The server compiles this into a decoding grammar, so the response cannot be
    malformed JSON, cannot miss or invent a key, and cannot return the wrong
    number of posts.
    """
    return {
        "type": "array",
        "minItems": total_posts,
        "maxItems": total_posts,
        "items": {
            "type": "object",
            "properties": {key: {"type": "string"} for key in POST_KEYS},
            "required": list(POST_KEYS),
            "additionalProperties": False,
        },
    }


def _log_llm_response(raw_response: str) -> None:
    logs_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "logs"))
    os.makedirs(logs_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = os.path.join(logs_dir, f"execution_{timestamp}.log")

    with open(log_path, "w", encoding="utf-8") as log_file:
        log_file.write(raw_response)


def compute_post_slots(month_str: str, posts_per_week: int, first_day: date | None = None, last_day: date | None = None) -> list[str]:
    if first_day is None or last_day is None:
        year, month = map(int, month_str.split("-"))
        days_in_month = calendar.monthrange(year, month)[1]
        first_day = date(year, month, 1)
        last_day = date(year, month, days_in_month)

    all_dates: list[date] = []
    current = first_day

    while current <= last_day:
        week_start = current - timedelta(days=current.weekday())
        week_end = week_start + timedelta(days=6)
        effective_start = max(week_start, first_day)
        effective_end = min(week_end, last_day)

        available_days: list[date] = []
        day = effective_start
        while day <= effective_end:
            available_days.append(day)
            day += timedelta(days=1)

        count = posts_per_week
        if count <= len(available_days):
            if count == len(available_days):
                chosen = available_days
            else:
                step = len(available_days) / count
                chosen = [available_days[int(index * step)] for index in range(count)]
        else:
            # When requested posts exceed days in a week slice, distribute multiple
            # posts per day by assigning slots across available days.
            step = len(available_days) / count
            chosen = [available_days[int(index * step)] for index in range(count)]

        all_dates.extend(chosen)
        current = week_start + timedelta(days=7)

    return [day.isoformat() for day in all_dates]


def build_llm_prompt(plan_input: dict[str, Any], total_posts: int, first_day: date, last_day: date) -> str:
    posts_per_week = int(plan_input.get("posts_per_week") or 7)
    month_window = f"{first_day.isoformat()} to {last_day.isoformat()}"

    channel = str(plan_input.get("channel_name", ""))
    channel_lower = channel.lower().replace(" ", "")
    words = channel.lower().split()
    name_tags = {f"#{channel_lower}"} if channel_lower else set()
    for word in words:
        if word:
            name_tags.add(f"#{word}")
    for start in range(len(words)):
        for end in range(start + 1, len(words)):
            name_tags.add(f"#{''.join(words[start:end + 1])}")
    channel_tag_hint = " ".join(sorted(name_tags))

    prompt = f"""You are a Social Media Content Planner.

CONTEXT:
- Channel: {plan_input.get('channel_name')}
- Category: {plan_input.get('category')} > {plan_input.get('sub_category_name')}
- Series: {plan_input.get('series_name')}
- Content type: {plan_input.get('content_type')}
- Tone: {plan_input.get('tone')}
- Language: {plan_input.get('language')}
- Target audience regions: {plan_input.get('target_audience')}
- Timezone for upload times: {plan_input.get('timezone')}
- Duration: {plan_input.get('duration_range_seconds')} seconds
- Goal: {plan_input.get('goal')}
- Special instructions: {plan_input.get('special_instructions')}

TASK:
Generate content metadata for exactly {total_posts} posts.

POSTING CADENCE:
- Required posts per week: {posts_per_week}
- Allowed upload date window: {month_window}
- You decide date_time.
- When posts_per_week is greater than 7, multiple posts on the same date are expected.
- If multiple posts are placed on the same date, use different time values for each post on that date.

For EACH post, provide:
1. date_time - YYYY-MM-DD HH:mm format in {plan_input.get('timezone')} timezone, optimized for peak activity across target regions
2. title - catchy, engaging, under 80 characters, include song/music references for variety
3. description - 2-3 sentences, engaging, include call-to-action, under 300 characters
4. hashtags - 8-15 space-separated hashtags starting with #. MUST include these channel tags: {channel_tag_hint}. Also include relevant gaming/content hashtags.
5. keywords - 5-10 space-separated keywords WITHOUT #. Related to content for SEO.

OUTPUT FORMAT:
Return ONLY a valid JSON array with exactly {total_posts} objects. No markdown, no code fences, no explanation.
Each object must have exactly these keys: "date_time", "title", "description", "hashtags", "keywords"
Every date_time value must be inside the allowed upload date window.

Example of ONE object:
{{"date_time":"2026-07-01 18:30","title":"Neon Goes Crazy on Ascent | Montage","description":"Watch Neon dominate with insane plays. Drop a like if you enjoy! #valorant","hashtags":"#runfzrun #runfz #fzrun #fz #valorant #neon #montage #gaming","keywords":"valorant neon montage gaming highlights gameplay"}}

Return the full JSON array now. Ensure valid JSON. Double-check every quote and comma."""
    return prompt


def call_llm(prompt: str, total_posts: int) -> str:
    """Ask the model for the posts, with the response schema enforced by the server.

    Uses the OpenAI-compatible endpoint because that is the one that accepts
    `response_format`; the prompt text itself is sent unchanged.
    """
    payload = {
        "model": LLM_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": "plansheet_posts",
                "strict": True,
                "schema": build_response_schema(total_posts),
            },
        },
    }

    try:
        response = requests.post(
            f"{LLM_API_URL}/v1/chat/completions",
            headers={"Content-Type": "application/json"},
            json=payload,
            timeout=300,
        )
    except requests.RequestException as exc:
        raise RuntimeError(f"Could not reach the LLM at {LLM_API_URL}: {exc}") from exc

    if response.status_code != 200:
        raise RuntimeError(f"LLM returned HTTP {response.status_code}: {response.text[:300]}")

    try:
        content = response.json()["choices"][0]["message"]["content"]
    except (ValueError, KeyError, IndexError) as exc:
        raise RuntimeError(f"Unexpected LLM response shape: {response.text[:300]}") from exc

    return (content or "").strip()


def _repair_json(text: str) -> str:
    """Fix the malformations models produce most often around valid content."""
    text = re.sub(r",\s*}", "}", text)
    text = re.sub(r",\s*]", "]", text)
    # Adjacent objects with the separating comma dropped.
    text = re.sub(r"}\s*{", "},{", text)
    # A key that lost its opening quote:  ...","hashtags":...  ->  ...,"hashtags":...
    text = re.sub(r'([,{])(\s*)([A-Za-z_][A-Za-z0-9_]*)"(\s*):', r'\1\2"\3"\4:', text)
    return text


def _iter_object_chunks(text: str):
    """Yield each top-level {...} span, ignoring braces inside strings."""
    depth = 0
    start = None
    in_string = False
    escaped = False

    for index, char in enumerate(text):
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue

        if char == '"':
            in_string = True
        elif char == "{":
            if depth == 0:
                start = index
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0 and start is not None:
                yield text[start:index + 1]
                start = None


def _salvage_objects(text: str) -> list[dict[str, Any]]:
    salvaged: list[dict[str, Any]] = []
    for chunk in _iter_object_chunks(text):
        try:
            item = json.loads(_repair_json(chunk))
        except json.JSONDecodeError:
            continue
        if isinstance(item, dict):
            salvaged.append(item)
    return salvaged


def parse_llm_response(raw_text: str, expected_count: int) -> list[dict[str, Any]] | None:
    if not raw_text:
        return None

    text = raw_text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        start = 1
        end = len(lines)
        for index in range(len(lines) - 1, -1, -1):
            if lines[index].strip().startswith("```"):
                end = index
                break
        text = "\n".join(lines[start:end]).strip()

    first_bracket = text.find("[")
    last_bracket = text.rfind("]")
    if first_bracket == -1 or last_bracket == -1:
        return None

    json_str = _repair_json(text[first_bracket:last_bracket + 1])

    try:
        data = json.loads(json_str)
    except json.JSONDecodeError:
        # One malformed object must not cost the whole batch: recover the objects
        # that are still readable and drop only the ones that are not.
        data = _salvage_objects(json_str)
        if not data:
            return None

    if not isinstance(data, list):
        return None

    # Keep exactly what the LLM returned; do not pad or synthesize missing items.

    required_keys = {"date_time", "title", "description", "hashtags", "keywords"}
    validated: list[dict[str, Any]] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        # Backward compatibility if model returns split date/time keys.
        if not str(item.get("date_time", "")).strip():
            upload_date = str(item.get("upload_date", "")).strip()
            upload_time = str(item.get("upload_time", "")).strip()
            if upload_date:
                item["date_time"] = f"{upload_date} {upload_time or '18:00'}"

        if isinstance(item.get("date_time"), str):
            item["date_time"] = item["date_time"].strip().replace("T", " ")

        missing = required_keys - set(item.keys())
        for key in missing:
            item[key] = ""
        validated.append(item)

    return validated


def build_rows(plan_input: dict[str, Any], llm_items: list[dict[str, Any]], start_episode: int = 1) -> list[dict[str, Any]]:
    storage_path = str(plan_input.get("storage_path", ""))
    category = str(plan_input.get("category", ""))
    sub_category = str(plan_input.get("sub_category_name", ""))
    series_name = str(plan_input.get("series_name", "")) if plan_input.get("is_series") else ""

    rows: list[dict[str, Any]] = []
    for index, llm_row in enumerate(llm_items):
        episode_number = start_episode + index
        raw_date_time = str(llm_row.get("date_time", "")).strip().replace("T", " ")

        episode_folder = f"EP{episode_number:03d}"
        row = {
            "post_id": str(uuid.uuid4()),
            "date_time": raw_date_time,
            "title": str(llm_row.get("title", "")).strip(),
            "description": str(llm_row.get("description", "")).strip(),
            "hashtags": str(llm_row.get("hashtags", "")).strip(),
            "keywords": str(llm_row.get("keywords", "")).strip(),
            "category": category,
            "sub_category_name": sub_category,
            "series_name": series_name,
            "episode_number": episode_number,
            "landscape_video_path": os.path.join(storage_path, "videos", episode_folder, "landscape.mp4"),
            "landscape_thumbnail_path": os.path.join(storage_path, "thumbnails", episode_folder, "landscape.png"),
            "portrait_video_path": os.path.join(storage_path, "videos", episode_folder, "portrait.mp4"),
            "portrait_thumbnail_path": os.path.join(storage_path, "thumbnails", episode_folder, "portrait.png"),
            "ai_flag": "FALSE",
            "kids_flag": "FALSE",
            "status": "PLANNED",
        }
        rows.append(row)

    return rows


def generate_plansheet_rows(plan_input: dict[str, Any], month: str) -> list[dict[str, Any]]:
    plan_input = dict(plan_input)
    plan_input["month"] = month
    posts_per_week = int(plan_input.get("posts_per_week") or 7)

    today = date.today()
    if month == today.strftime("%Y-%m"):
        first_day = today + timedelta(days=1)
        last_day = date(today.year, today.month, calendar.monthrange(today.year, today.month)[1])
    else:
        year, month_number = map(int, month.split("-"))
        first_day = date(year, month_number, 1)
        last_day = date(year, month_number, calendar.monthrange(year, month_number)[1])

    post_slots = compute_post_slots(month, posts_per_week, first_day, last_day)
    total_posts = len(post_slots)
    prompt = build_llm_prompt(plan_input, total_posts, first_day, last_day)
    raw_response = call_llm(prompt, total_posts)
    _log_llm_response(raw_response)

    if not raw_response:
        raise RuntimeError("The LLM returned an empty response.")

    llm_items = parse_llm_response(raw_response, total_posts)
    if not llm_items:
        raise RuntimeError("The LLM response was not readable as JSON. See the newest file in backend/logs.")

    return build_rows(plan_input, llm_items)
