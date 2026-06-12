import json
import os
import csv
import uuid
import calendar
from datetime import date, timedelta

import requests

# ─── Configuration ───────────────────────────────────────────────────────────
LLM_API_URL = "http://localhost:2000"
OUTPUT_FOLDER = r"monthly_sheets"
JSON_INPUT_FILE = r"input_monthly.json"

EXPECTED_HEADERS = [
    "post_id", "upload_date", "upload_time",
    "title", "description", "hashtags", "keywords",
    "category", "sub_category_name", "series_name", "episode_number",
    "video_local_path", "thumbnail_local_path",
    "ai_flag", "kids_flag", "status"
]


# ─── Step 1: Compute upload dates (deterministic) ───────────────────────────
def compute_upload_dates(month_str: str, posts_per_week: int) -> list[str]:
    """
    Distribute `posts_per_week` uploads evenly across the given month.
    Returns a sorted list of 'YYYY-MM-DD' strings.
    """
    year, month = map(int, month_str.split("-"))
    days_in_month = calendar.monthrange(year, month)[1]

    first_day = date(year, month, 1)
    last_day = date(year, month, days_in_month)

    all_dates = []
    current = first_day

    while current <= last_day:
        # Find the Monday of the current week (ISO weekday: Mon=1)
        week_start = current - timedelta(days=current.weekday())

        # Determine the valid range for this week within the month
        week_end = week_start + timedelta(days=6)
        effective_start = max(week_start, first_day)
        effective_end = min(week_end, last_day)

        # Available days this week within the month
        available_days = []
        d = effective_start
        while d <= effective_end:
            available_days.append(d)
            d += timedelta(days=1)

        # Pick evenly spaced days from available pool
        count = min(posts_per_week, len(available_days))
        if count == len(available_days):
            chosen = available_days
        else:
            # Spread picks evenly
            step = len(available_days) / count
            chosen = [available_days[int(i * step)] for i in range(count)]

        all_dates.extend(chosen)

        # Move to next week's Monday
        current = week_start + timedelta(days=7)

    # Deduplicate and sort
    all_dates = sorted(set(all_dates))
    return [d.isoformat() for d in all_dates]


# ─── Step 2: Build LLM prompt (only creative fields) ────────────────────────
def build_llm_prompt(json_data: dict, upload_dates: list[str]) -> str:
    """
    Ask the LLM to generate ONLY the fields that require reasoning:
    upload_time, title, description, hashtags, keywords — one per upload date.
    Response format: JSON array (much more reliable than CSV).
    """
    total_posts = len(upload_dates)
    dates_list = ", ".join(upload_dates)

    # Build channel name substring hints
    channel = json_data.get("channel_name", "")
    channel_lower = channel.lower().replace(" ", "")
    words = channel.lower().split()
    name_tags = set()
    name_tags.add(f"#{channel_lower}")
    for w in words:
        name_tags.add(f"#{w}")
    for i in range(len(words)):
        for j in range(i + 1, len(words)):
            name_tags.add(f"#{''.join(words[i:j+1])}")
    channel_tag_hint = " ".join(sorted(name_tags))

    prompt = f"""You are a Social Media Content Planner.

CONTEXT:
- Channel: {json_data.get('channel_name')}
- Category: {json_data.get('category')} > {json_data.get('sub_category_name')}
- Series: {json_data.get('series_name')}
- Content type: {json_data.get('content_type')}
- Tone: {json_data.get('tone')}
- Language: {json_data.get('language')}
- Target audience regions: {', '.join(json_data.get('target_audience', []))}
- Timezone for upload times: {json_data.get('timezone')}
- Duration: {json_data.get('duration_range_seconds')} seconds
- Goal: {json_data.get('goal')}
- Special instructions: {json_data.get('special_instructions')}

TASK:
Generate content metadata for exactly {total_posts} posts with these upload dates:
{dates_list}

For EACH post, provide:
1. upload_time — HH:mm format in {json_data.get('timezone')} timezone, optimized for peak activity across target regions
2. title — catchy, engaging, under 80 characters, include song/music references for variety
3. description — 2-3 sentences, engaging, include call-to-action, under 300 characters
4. hashtags — 8-15 space-separated hashtags starting with #. MUST include these channel tags: {channel_tag_hint}. Also include relevant gaming/content hashtags.
5. keywords — 5-10 space-separated keywords WITHOUT #. Related to content for SEO.

OUTPUT FORMAT:
Return ONLY a valid JSON array with exactly {total_posts} objects. No markdown, no code fences, no explanation.
Each object must have exactly these keys: "upload_date", "upload_time", "title", "description", "hashtags", "keywords"

Example of ONE object:
{{"upload_date":"2026-07-01","upload_time":"18:30","title":"Neon Goes Crazy on Ascent | Montage","description":"Watch Neon dominate with insane plays. Drop a like if you enjoy! #valorant","hashtags":"#runfzrun #runfz #fzrun #fz #valorant #neon #montage #gaming","keywords":"valorant neon montage gaming highlights gameplay"}}

Return the full JSON array now. Ensure valid JSON. Double-check every quote and comma."""

    return prompt


# ─── Step 3: Call LLM API ────────────────────────────────────────────────────
def call_llm(prompt: str) -> str | None:
    """Send prompt to local LLM and return raw text output."""
    payload = {
        "model": "google/gemma-4-e2b",
        "input": prompt
    }

    try:
        response = requests.post(
            f"{LLM_API_URL}/api/v1/chat",
            headers={"Content-Type": "application/json"},
            json=payload,
            timeout=300
        )

        if response.status_code == 200:
            result = response.json()
            return _extract_text(result.get("output"))
        else:
            print(f"API Error {response.status_code}: {response.text}")
            return None

    except Exception as e:
        print(f"LLM API call failed: {e}")
        return None


def _extract_text(output_field) -> str | None:
    """Pull plain text from various API output shapes."""
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


# ─── Step 4: Parse LLM JSON response ────────────────────────────────────────
def parse_llm_response(raw_text: str, expected_count: int) -> list[dict] | None:
    """
    Robustly parse the LLM's JSON array output.
    Handles common LLM quirks: markdown fences, trailing commas, extra text.
    """
    if not raw_text:
        return None

    text = raw_text.strip()

    # Strip markdown code fences if present
    if text.startswith("```"):
        lines = text.split("\n")
        # Remove first line (```json or ```) and last line (```)
        start = 1
        end = len(lines)
        for i in range(len(lines) - 1, -1, -1):
            if lines[i].strip().startswith("```"):
                end = i
                break
        text = "\n".join(lines[start:end]).strip()

    # Find the JSON array boundaries
    first_bracket = text.find("[")
    last_bracket = text.rfind("]")
    if first_bracket == -1 or last_bracket == -1:
        print("ERROR: No JSON array found in LLM response.")
        print(f"Raw response (first 500 chars): {text[:500]}")
        return None

    json_str = text[first_bracket:last_bracket + 1]

    # Fix trailing commas before ] or } (common LLM mistake)
    import re
    json_str = re.sub(r',\s*}', '}', json_str)
    json_str = re.sub(r',\s*]', ']', json_str)

    try:
        data = json.loads(json_str)
    except json.JSONDecodeError as e:
        print(f"JSON parse error: {e}")
        print(f"Attempted to parse: {json_str[:500]}...")
        return None

    if not isinstance(data, list):
        print(f"ERROR: Expected list, got {type(data)}")
        return None

    if len(data) != expected_count:
        print(f"WARNING: Expected {expected_count} items, got {len(data)}. Adjusting...")
        # If we got more, truncate. If fewer, we'll handle downstream.
        data = data[:expected_count]

    # Validate each item has required keys
    required_keys = {"upload_date", "upload_time", "title", "description", "hashtags", "keywords"}
    validated = []
    for i, item in enumerate(data):
        if not isinstance(item, dict):
            print(f"WARNING: Item {i} is not a dict, skipping.")
            continue
        missing = required_keys - set(item.keys())
        if missing:
            print(f"WARNING: Item {i} missing keys: {missing}. Filling with defaults.")
            for key in missing:
                item[key] = ""
        validated.append(item)

    return validated


# ─── Step 5: Merge LLM output with deterministic fields → CSV rows ──────────
def build_csv_rows(
    json_data: dict,
    upload_dates: list[str],
    llm_items: list[dict],
    start_episode: int = 1
) -> list[dict]:
    """
    Combine LLM-generated creative fields with programmatic fields
    into final CSV rows.
    """
    storage_path = json_data.get("storage_path", "")
    category = json_data.get("category", "")
    sub_category = json_data.get("sub_category_name", "")
    series_name = json_data.get("series_name", "") if json_data.get("is_series") else ""

    rows = []
    for i, upload_date in enumerate(upload_dates):
        episode_num = start_episode + i

        # Get LLM data for this post (fallback to empty if missing)
        if i < len(llm_items):
            llm = llm_items[i]
        else:
            llm = {
                "upload_time": "18:00",
                "title": f"{series_name} - Episode {episode_num}",
                "description": "",
                "hashtags": "",
                "keywords": ""
            }

        # Build deterministic paths
        ep_folder = f"EP{episode_num:03d}"
        video_path = os.path.join(storage_path, "videos", ep_folder, "video.mp4")
        thumb_path = os.path.join(storage_path, "thumbnails", ep_folder, "thumbnail.png")

        row = {
            "post_id": str(uuid.uuid4()),
            "upload_date": upload_date,
            "upload_time": llm.get("upload_time", "18:00"),
            "title": llm.get("title", ""),
            "description": llm.get("description", ""),
            "hashtags": llm.get("hashtags", ""),
            "keywords": llm.get("keywords", ""),
            "category": category,
            "sub_category_name": sub_category,
            "series_name": series_name,
            "episode_number": episode_num,
            "video_local_path": video_path,
            "thumbnail_local_path": thumb_path,
            "ai_flag": "FALSE",
            "kids_flag": "FALSE",
            "status": "PLANNED"
        }
        rows.append(row)

    return rows


# ─── Step 6: Write CSV ──────────────────────────────────────────────────────
def save_csv(rows: list[dict], output_path: str) -> bool:
    """Write rows to a properly formatted CSV file."""
    if not rows:
        return False

    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    with open(output_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=EXPECTED_HEADERS, quoting=csv.QUOTE_ALL)
        writer.writeheader()
        writer.writerows(rows)

    return True


# ─── Main ────────────────────────────────────────────────────────────────────
def main():
    # 1. Load input JSON
    with open(JSON_INPUT_FILE, "r", encoding="utf-8") as f:
        json_data = json.load(f)

    month_str = json_data.get("month", "2026-07")
    posts_per_week = json_data.get("posts_per_week", 7)

    print(f"Planning content for: {month_str}")
    print(f"Posts per week: {posts_per_week}")

    # 2. Compute upload dates (deterministic)
    upload_dates = compute_upload_dates(month_str, posts_per_week)
    total_posts = len(upload_dates)
    print(f"Total posts scheduled: {total_posts}")
    print(f"Dates: {upload_dates[:5]}... (showing first 5)")

    # 3. Build LLM prompt (only creative fields)
    prompt = build_llm_prompt(json_data, upload_dates)
    print(f"\nPrompt length: {len(prompt)} chars")
    print("─" * 60)
    print(prompt)
    print("─" * 60)

    # 4. Call LLM
    print("\nCalling LLM API...")
    raw_response = call_llm(prompt)

    if not raw_response:
        print("FATAL: No response from LLM.")
        return

    print(f"LLM response length: {len(raw_response)} chars")

    # 5. Parse LLM JSON response
    llm_items = parse_llm_response(raw_response, total_posts)

    if not llm_items:
        print("FATAL: Could not parse LLM response into valid JSON.")
        print(f"Raw response:\n{raw_response[:1000]}")
        return

    print(f"Successfully parsed {len(llm_items)} items from LLM.")

    # 6. Merge with deterministic fields
    csv_rows = build_csv_rows(json_data, upload_dates, llm_items)

    # 7. Save CSV
    output_folder = os.path.abspath(OUTPUT_FOLDER)
    output_path = os.path.join(output_folder, f"{month_str}.csv")
    saved = save_csv(csv_rows, output_path)

    if saved:
        print(f"\nCSV saved to: {output_path}")
        print(f"Total rows: {len(csv_rows)}")
        # Preview first row
        if csv_rows:
            print("\nFirst row preview:")
            for k, v in csv_rows[0].items():
                print(f"  {k}: {v}")
    else:
        print("Failed to save CSV.")


if __name__ == "__main__":
    main()