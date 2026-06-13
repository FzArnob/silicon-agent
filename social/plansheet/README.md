# Monthly Sheet Generator

This script automates the creation of a social media content plan for a specific month. It uses a local LLM to generate creative content metadata (titles, descriptions, hashtags, keywords) based on provided channel context and then merges this with deterministic data (dates, paths, IDs) to produce a final CSV file.

## Features

- **Smart Date Scheduling**: Automatically distributes a specified number of posts per week across a given month, ensuring even spacing. For the current month, scheduling starts from tomorrow instead of the 1st.
- **LLM-Powered Creativity**: Integrates with a local LLM (Gemma-4-e2b) to generate context-aware content metadata.
- **Context-Aware Prompting**: Dynamically builds prompts using channel names, categories, series info, tone, target audience, and special instructions.
- **Robust JSON Parsing**: Handles common LLM output quirks like markdown code fences and trailing commas.
- **Automated CSV Generation**: Produces a standardized CSV file with all required headers for downstream processing.

## How It Works

1.  **Input Loading**: Reads configuration and context from `input_monthly.json`.
2.  **Date Computation**: Calculates upload dates for the target month based on the `posts_per_week` parameter. For the current month, scheduling starts from tomorrow instead of the 1st.
3.  **Prompt Construction**: Builds a detailed prompt for the LLM, including:
    - Channel context (name, category, series, etc.)
    - Target audience and timezone information
    - Specific goals and special instructions
    - A list of all calculated upload dates
4.  **LLM Interaction**: Sends the prompt to a local LLM API (`http://localhost:2000/api/v1/chat`).
5.  **Response Parsing**: Extracts and validates the JSON array of creative content from the LLM's response.
6.  **Data Merging**: Combines the LLM's creative output with deterministic fields:
    - `post_id`: Unique UUID
    - `landscape_video_path` & `landscape_thumbnail_path`: Generated based on episode numbers and storage paths (e.g., `videos/EPXXX/landscape.mp4`, `thumbnails/EPXXX/landscape.png`)
    - `portrait_video_path` & `portrait_thumbnail_path`: Generated based on episode numbers and storage paths (e.g., `videos/EPXXX/portrait.mp4`, `thumbnails/EPXXX/portrait.png`)
    - `episode_number`: Incremental numbering.
    - `status`: Defaults to "PLANNED".
7.  **CSV Export**: Saves the final dataset to `monthly_sheets/[YYYY-MM].csv`.

## Rules & Constraints

- **Output Format**: The LLM is strictly instructed to return a valid JSON array.
- **Content Limits**:
    - Titles: Under 80 characters.
    - Descriptions: 2-3 sentences, under 300 characters.
    - Hashtags: 8-15 tags, including specific channel-related tags.
    - Keywords: 5-10 SEO-friendly keywords.
- **Timezone**: Upload times are optimized for the target audience's timezone.
- **Deterministic Paths**: Video and thumbnail paths are strictly formatted as:
    - Landscape: `videos/EPXXX/landscape.mp4` and `thumbnails/EPXXX/landscape.png`
    - Portrait: `videos/EPXXX/portrait.mp4` and `thumbnails/EPXXX/portrait.png`

## Folder Structure

```
social/
├── plansheet/
│   ├── generate_monthly_sheet.py      # The main script
│   ├── input_monthly.json              # Configuration & Context
│   ├── monthly_sheets/                 # Output directory for CSVs
│   └── requirements.txt                # Python dependencies
```

## Requirements

- Python 3.x
- `requests` library
- A local LLM server running at `http://localhost:2000` with the `google/gemma-4-e2b` model.

## Usage

1. Ensure your local LLM server is running.
2. Configure your channel details in `input_monthly.json`.
3. Run the script:
   ```bash
   python social/plansheet/generate_monthly_sheet.py
   ```
