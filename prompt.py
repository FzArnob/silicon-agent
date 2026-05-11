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
    """Calculate how many images to pick per category.
    The lowest-count category gets 1 image; others scale proportionally, capped at 4."""
    category_totals = {cat: len(scenes) for cat, scenes in eligible_categories.items()}

    if not category_totals:
        return {}

    min_count = min(category_totals.values())

    counts = {}
    for cat, total in category_totals.items():
        target = round(total / min_count)  # min category → 1, others scale up
        counts[cat] = min(4, max(1, target))  # floor 1, cap 4

    return counts


def pick_scenes(eligible_categories, counts, config_row):
    """Randomly pick scenes per category based on counts."""
    picked = {}
    for cat, count in counts.items():
        available = eligible_categories[cat]
        chosen = random.sample(available, count)
        picked[cat] = chosen
    return picked


def build_image_prompts(picked_scenes, config_row):
    """Build one prompt per image from picked scenes, preserving category order from scene.csv."""
    all_scenes = []
    for category, scenes in picked_scenes.items():
        category_scenes = [
            {"category": category, "dependency": s["dependency"], "details": s["details"]}
            for s in scenes
        ]
        random.shuffle(category_scenes)  # randomize within category only
        all_scenes.extend(category_scenes)

    image_prompts = []
    for scene in all_scenes:
        prompt = (
            f"Generate 1 image, 16:9 ratio 4K.\n\n"
            f"[Scene: {scene['category']}]\n"
            f"{scene['details']}\n\n"
            f"Maintain strict visual continuity with the master prompt setup."
        )
        image_prompts.append(prompt)

    return image_prompts


def generate_session_prompts():
    """Main function: generate master prompt and image prompts for a session."""
    config_row = pick_config_row()
    master_prompt = build_master_prompt(config_row)

    scenes = load_scenes()
    eligible = get_eligible_categories(scenes, config_row)
    counts = calculate_scene_counts(eligible)
    picked = pick_scenes(eligible, counts, config_row)
    image_prompts = build_image_prompts(picked, config_row)

    return master_prompt, image_prompts, config_row


if __name__ == "__main__":
    master, images, config = generate_session_prompts()
    print(f"Setup: {config['Setup Name']}")
    print(f"Master prompt length: {len(master)} chars")
    print(f"Images: {len(images)}\n")
    for i, p in enumerate(images, 1):
        print(f"--- Image {i} ---")
        print(p)
        print()
