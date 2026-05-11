import csv
import json
import os
import random
import math
from collections import Counter, defaultdict
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_CSV = os.path.join(BASE_DIR, "data", "config.csv")
SCENE_CSV = os.path.join(BASE_DIR, "data", "scene.csv")
MASTER_PROMPT_MD = os.path.join(BASE_DIR, "data", "master_prompt.md")
TRACKER_JSON = os.path.join(BASE_DIR, "data", "config_tracker.json")


def load_tracker():
    if os.path.exists(TRACKER_JSON):
        with open(TRACKER_JSON, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_tracker(tracker):
    with open(TRACKER_JSON, "w", encoding="utf-8") as f:
        json.dump(tracker, f, indent=2, ensure_ascii=False)


def pick_config_row():
    """Pick the least recently used config row and update tracker."""
    with open(CONFIG_CSV, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    tracker = load_tracker()

    # Find the row with oldest (or missing) last_used date
    oldest_date = None
    chosen_row = None
    for row in rows:
        setup_name = row["Setup Name"]
        last_used = tracker.get(setup_name, {}).get("last_used", "1970-01-01")
        if oldest_date is None or last_used < oldest_date:
            oldest_date = last_used
            chosen_row = row

    # Update tracker
    setup_name = chosen_row["Setup Name"]
    tracker[setup_name] = {"last_used": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
    save_tracker(tracker)

    return chosen_row


def format_config_for_prompt(config_row):
    """Format a config row into readable prompt text."""
    lines = []
    for header, value in config_row.items():
        if value and value.strip() and value.strip().lower() != "none":
            lines.append(f"- **{header}**: {value.strip()}")
    return "\n".join(lines)


def build_master_prompt(config_row):
    """Build the master prompt with config data inserted."""
    with open(MASTER_PROMPT_MD, "r", encoding="utf-8") as f:
        template = f.read()

    config_text = format_config_for_prompt(config_row)
    master_prompt = template.replace("[SETUP CONFIGURATION HERE]", config_text)
    return master_prompt


def load_scenes():
    """Load scenes grouped by category."""
    categories = defaultdict(list)
    with open(SCENE_CSV, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            cat = row["category"].strip()
            dep = row["config_dependency"].strip()
            details = row["scene_details"].strip()
            categories[cat].append({"dependency": dep, "details": details})
    return categories


def get_eligible_categories(scenes, config_row):
    """Filter categories based on config dependencies."""
    eligible = {}
    for category, scene_list in scenes.items():
        dep = scene_list[0]["dependency"]
        if dep == "None":
            # No dependency - always eligible
            eligible[category] = scene_list
        else:
            # Check if the config row has a non-None value for this dependency
            config_value = config_row.get(dep, "").strip()
            if config_value and config_value.lower() != "none":
                eligible[category] = scene_list
    return eligible


def calculate_scene_counts(eligible_categories):
    """Calculate how many scenes to pick per category using ratio logic."""
    category_totals = {cat: len(scenes) for cat, scenes in eligible_categories.items()}

    if not category_totals:
        return {}

    min_count = min(category_totals.values())
    base = max(1, min_count // 2)

    counts = {}
    for cat, total in category_totals.items():
        target = max(1, round((total / min_count) * base))
        # Don't exceed available scenes
        counts[cat] = min(target, total)

    return counts


def pick_scenes(eligible_categories, counts, config_row):
    """Randomly pick scenes per category based on counts."""
    picked = {}
    for cat, count in counts.items():
        available = eligible_categories[cat]
        chosen = random.sample(available, count)
        picked[cat] = chosen
    return picked


def build_batch_prompts(picked_scenes, config_row, batch_size=5):
    """Build numbered batch prompts from picked scenes."""
    # Flatten all scenes with category info
    all_scenes = []
    for category, scenes in picked_scenes.items():
        for scene in scenes:
            all_scenes.append({
                "category": category,
                "dependency": scene["dependency"],
                "details": scene["details"]
            })

    # Shuffle for variety
    random.shuffle(all_scenes)

    # Build batches (minimum batch_size per batch)
    batches = []
    for i in range(0, len(all_scenes), batch_size):
        batch = all_scenes[i:i + batch_size]
        # If remaining is less than batch_size and there's a previous batch,
        # merge with last batch only if remainder is very small (< 3)
        if len(batch) < 3 and batches:
            batches[-1].extend(batch)
        else:
            batches.append(batch)

    # Format each batch into a prompt
    batch_prompts = []
    for batch_idx, batch in enumerate(batches, 1):
        lines = [f"Generate the following {len(batch)} images for this session:\n"]
        for idx, scene in enumerate(batch, 1):
            ref_line = ""
            if scene["dependency"] != "None":
                dep_key = scene["dependency"]
                dep_value = config_row.get(dep_key, "").strip()
                ref_line = f" [Reference: {dep_key} = {dep_value}]"

            lines.append(f"{idx}. [{scene['category']}] {scene['details']}{ref_line}")

        lines.append("\nMaintain strict visual continuity with the master prompt setup. Only change camera angle and framing per instruction above.")
        batch_prompts.append("\n".join(lines))

    return batch_prompts


def generate_session_prompts():
    """Main function: generate master prompt and batch prompts for a session."""
    config_row = pick_config_row()
    master_prompt = build_master_prompt(config_row)

    scenes = load_scenes()
    eligible = get_eligible_categories(scenes, config_row)
    counts = calculate_scene_counts(eligible)
    picked = pick_scenes(eligible, counts, config_row)
    batch_prompts = build_batch_prompts(picked, config_row)

    return master_prompt, batch_prompts, config_row


if __name__ == "__main__":
    master, batches, config = generate_session_prompts()
    print(f"Setup: {config['Setup Name']}")
    print(f"Master prompt length: {len(master)} chars")
    print(f"Batches: {len(batches)}")
    for i, b in enumerate(batches, 1):
        scene_count = b.count("\n[") + b.count("\n1.")
        print(f"  Batch {i}: {b[:80]}...")
