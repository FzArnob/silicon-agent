from __future__ import annotations

import calendar
import json
import os
import re
import uuid
from datetime import date, timedelta
from typing import Any

import requests

from .defaults import REQUIRED_COLUMNS

LLM_API_URL = os.getenv("LLM_API_URL", "http://localhost:2000")
LLM_MODEL = os.getenv("LLM_MODEL", "google/gemma-4-e2b")


def compute_upload_dates(month_str: str, posts_per_week: int, first_day: date | None = None, last_day: date | None = None) -> list[str]:
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

        count = min(posts_per_week, len(available_days))
        if count == len(available_days):
            chosen = available_days
        else:
            step = len(available_days) / count
            chosen = [available_days[int(index * step)] for index in range(count)]

        all_dates.extend(chosen)
        current = week_start + timedelta(days=7)

    unique_dates = sorted(set(all_dates))
    return [day.isoformat() for day in unique_dates]


def build_llm_prompt(plan_input: dict[str, Any], upload_dates: list[str]) -> str:
    total_posts = len(upload_dates)
    dates_list = ", ".join(upload_dates)

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
- Target audience regions: {', '.join(plan_input.get('target_audience', []))}
- Timezone for upload times: {plan_input.get('timezone')}
- Duration: {plan_input.get('duration_range_seconds')} seconds
- Goal: {plan_input.get('goal')}
- Special instructions: {plan_input.get('special_instructions')}

TASK:
Generate content metadata for exactly {total_posts} posts with these upload dates:
{dates_list}

For EACH post, provide:
1. upload_time - HH:mm format in {plan_input.get('timezone')} timezone, optimized for peak activity across target regions
2. title - catchy, engaging, under 80 characters, include song/music references for variety
3. description - 2-3 sentences, engaging, include call-to-action, under 300 characters
4. hashtags - 8-15 space-separated hashtags starting with #. MUST include these channel tags: {channel_tag_hint}. Also include relevant gaming/content hashtags.
5. keywords - 5-10 space-separated keywords WITHOUT #. Related to content for SEO.

OUTPUT FORMAT:
Return ONLY a valid JSON array with exactly {total_posts} objects. No markdown, no code fences, no explanation.
Each object must have exactly these keys: "upload_date", "upload_time", "title", "description", "hashtags", "keywords"

Example of ONE object:
{{"upload_date":"2026-07-01","upload_time":"18:30","title":"Neon Goes Crazy on Ascent | Montage","description":"Watch Neon dominate with insane plays. Drop a like if you enjoy! #valorant","hashtags":"#runfzrun #runfz #fzrun #fz #valorant #neon #montage #gaming","keywords":"valorant neon montage gaming highlights gameplay"}}

Return the full JSON array now. Ensure valid JSON. Double-check every quote and comma."""
    return prompt


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


def call_llm(prompt: str) -> str | None:
    payload = {
        "model": LLM_MODEL,
        "input": prompt,
    }

    try:
        response = requests.post(
            f"{LLM_API_URL}/api/v1/chat",
            headers={"Content-Type": "application/json"},
            json=payload,
            timeout=300,
        )
        if response.status_code == 200:
            result = response.json()
            return _extract_text(result.get("output"))
        return None
    except Exception:
        return None


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

    json_str = text[first_bracket:last_bracket + 1]
    json_str = re.sub(r',\s*}', '}', json_str)
    json_str = re.sub(r',\s*]', ']', json_str)

    try:
        data = json.loads(json_str)
    except json.JSONDecodeError:
        return None

    if not isinstance(data, list):
        return None

    if len(data) != expected_count:
        data = data[:expected_count]

    required_keys = {"upload_date", "upload_time", "title", "description", "hashtags", "keywords"}
    validated: list[dict[str, Any]] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        missing = required_keys - set(item.keys())
        for key in missing:
            item[key] = ""
        validated.append(item)

    return validated


def build_rows(plan_input: dict[str, Any], upload_dates: list[str], llm_items: list[dict[str, Any]], start_episode: int = 1) -> list[dict[str, Any]]:
    storage_path = str(plan_input.get("storage_path", ""))
    category = str(plan_input.get("category", ""))
    sub_category = str(plan_input.get("sub_category_name", ""))
    series_name = str(plan_input.get("series_name", "")) if plan_input.get("is_series") else ""

    rows: list[dict[str, Any]] = []
    for index, upload_date in enumerate(upload_dates):
        episode_number = start_episode + index
        if index < len(llm_items):
            llm_row = llm_items[index]
        else:
            llm_row = {
                "upload_time": "18:00",
                "title": f"{series_name} - Episode {episode_number}",
                "description": "",
                "hashtags": "",
                "keywords": "",
            }

        episode_folder = f"EP{episode_number:03d}"
        row = {
            "post_id": str(uuid.uuid4()),
            "upload_date": upload_date,
            "upload_time": str(llm_row.get("upload_time", "18:00")),
            "title": str(llm_row.get("title", "")),
            "description": str(llm_row.get("description", "")),
            "hashtags": str(llm_row.get("hashtags", "")),
            "keywords": str(llm_row.get("keywords", "")),
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


def generate_plansheet_rows(plan_input: dict[str, Any], month: str) -> tuple[list[dict[str, Any]], list[str]]:
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

    upload_dates = compute_upload_dates(month, posts_per_week, first_day, last_day)
    prompt = build_llm_prompt(plan_input, upload_dates)
    raw_response = call_llm(prompt)
    if not raw_response:
        raise RuntimeError("No response from LLM API")

    llm_items = parse_llm_response(raw_response, len(upload_dates))
    if not llm_items:
        raise RuntimeError("Could not parse LLM response")

    rows = build_rows(plan_input, upload_dates, llm_items)
    return rows, upload_dates
