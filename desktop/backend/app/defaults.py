"""Single source of truth for every field the app stores, edits, and generates.

The UI builds its forms and table from these definitions (served by /api/meta),
the SQLite tables use these exact column names, and the generator reads these
exact keys. Nothing is renamed or converted between layers.
"""

STATUS_VALUES = ["PLANNED", "FAILED", "COMPLETED", "PARTIALLY COMPLETED"]
FLAG_VALUES = ["TRUE", "FALSE"]

# Columns of the input_sets table, minus id/created_at/updated_at.
INPUT_FIELDS = [
    {"key": "name", "label": "Set Name", "type": "text"},
    {"key": "channel_name", "label": "Channel Name", "type": "text"},
    {"key": "category", "label": "Category", "type": "text"},
    {"key": "sub_category_name", "label": "Sub Category Name", "type": "text"},
    {"key": "is_series", "label": "Is Series", "type": "bool"},
    {"key": "series_name", "label": "Series Name", "type": "text"},
    {"key": "content_type", "label": "Content Type", "type": "text"},
    {"key": "target_audience", "label": "Target Audience", "type": "text"},
    {"key": "posts_per_week", "label": "Posts Per Week", "type": "int"},
    {"key": "goal", "label": "Goal", "type": "text"},
    {"key": "tone", "label": "Tone", "type": "text"},
    {"key": "duration_range_seconds", "label": "Duration Range Seconds", "type": "text"},
    {"key": "language", "label": "Language", "type": "text"},
    {"key": "timezone", "label": "Timezone", "type": "text"},
    {"key": "storage_path", "label": "Storage Path", "type": "text"},
    {"key": "special_instructions", "label": "Special Instructions", "type": "textarea"},
]

INPUT_KEYS = [field["key"] for field in INPUT_FIELDS]

# Columns of the plansheet_rows table, minus id/plansheet_id/row_order/timestamps.
ROW_FIELDS = [
    {"key": "post_id", "label": "Post ID", "type": "readonly"},
    {"key": "date_time", "label": "Date Time", "type": "datetime"},
    {"key": "title", "label": "Title", "type": "textarea"},
    {"key": "description", "label": "Description", "type": "textarea"},
    {"key": "hashtags", "label": "Hashtags", "type": "textarea"},
    {"key": "keywords", "label": "Keywords", "type": "textarea"},
    {"key": "category", "label": "Category", "type": "text"},
    {"key": "sub_category_name", "label": "Sub Category Name", "type": "text"},
    {"key": "series_name", "label": "Series Name", "type": "text"},
    {"key": "episode_number", "label": "Episode Number", "type": "text"},
    {"key": "landscape_video_path", "label": "Landscape Video Path", "type": "text"},
    {"key": "landscape_thumbnail_path", "label": "Landscape Thumbnail Path", "type": "text"},
    {"key": "portrait_video_path", "label": "Portrait Video Path", "type": "text"},
    {"key": "portrait_thumbnail_path", "label": "Portrait Thumbnail Path", "type": "text"},
    {"key": "ai_flag", "label": "AI Flag", "type": "select", "options": FLAG_VALUES},
    {"key": "kids_flag", "label": "Kids Flag", "type": "select", "options": FLAG_VALUES},
    {"key": "status", "label": "Status", "type": "select", "options": STATUS_VALUES},
]

ROW_COLUMNS = [field["key"] for field in ROW_FIELDS]

# Seeded into input_sets on first run so the app always has a selectable set.
DEFAULT_INPUT_SET = {
    "name": "Default",
    "channel_name": "Run Fz Run",
    "category": "Gaming",
    "sub_category_name": "Valorant",
    "is_series": 1,
    "series_name": "Neon - Valorant Music Montages",
    "content_type": "Shorts, Musical Gameplay Montages",
    "target_audience": "Japan, Korea, India, Indonesia, Philippines, Bangladesh",
    "posts_per_week": 7,
    "goal": "Maximum Reach",
    "tone": "Energetic, Engaging, Trendy, Fun",
    "duration_range_seconds": "45-120",
    "language": "English",
    "timezone": "Asia/Dhaka",
    "storage_path": "D:/Content/RunFzRun",
    "special_instructions": (
        "Music-driven Valorant Neon montage series featuring viewer-requested songs. "
        "Focused on strong first 2-second hooks, high shareability, and alignment with "
        "current platform trends. Choose upload time based on target audience's peak "
        "activity hours and adjust it for the timezone provided."
    ),
}
