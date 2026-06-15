from copy import deepcopy

REQUIRED_COLUMNS = [
    "post_id", "upload_date", "upload_time",
    "title", "description", "hashtags", "keywords",
    "category", "sub_category_name", "series_name", "episode_number",
    "landscape_video_path", "landscape_thumbnail_path",
    "portrait_video_path", "portrait_thumbnail_path",
    "ai_flag", "kids_flag", "status",
]

DEFAULT_PLAN_INPUT = {
    "month": "",
    "timezone": "Asia/Dhaka",
    "channel_name": "Run Fz Run",
    "category": "Gaming",
    "sub_category_name": "Valorant",
    "target_audience": [
        "Japan",
        "Korea",
        "India",
        "Indonesia",
        "Philippines",
        "Bangladesh",
    ],
    "content_type": "Shorts, Musical Gameplay Montages",
    "posts_per_week": 7,
    "is_series": True,
    "series_name": "Neon - Valorant Music Montages",
    "goal": "Maximum Reach",
    "tone": "Energetic, Engaging, Trendy, Fun",
    "duration_range_seconds": "45-120",
    "language": "English",
    "storage_path": "D:/Content/RunFzRun/2026-07",
    "special_instructions": "Music-driven Valorant Neon montage series featuring viewer-requested songs. Focused on strong first 2-second hooks, high shareability, and alignment with current platform trends. Choose upload time based on target audience's peak activity hours and adjust it for the timezone provided.",
}


def make_default_plan_input(month: str) -> dict:
    plan_input = deepcopy(DEFAULT_PLAN_INPUT)
    plan_input["month"] = month
    return plan_input
