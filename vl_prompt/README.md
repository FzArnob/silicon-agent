# Valorant VLM PoC (2 FPS)

This PoC has two scripts:

1. `frame_to_json_poc.py`
   - Reads a gameplay video.
   - Samples at 2 FPS (configurable).
   - Makes one VLM call per sampled frame using:
     - `system_prompt`
     - text input
     - image input (`data_url`)
   - Writes one JSON file per frame with frame number and timestamp.

2. `json_to_script_poc.py`
   - Reads sequential `frame_*.json` outputs.
   - Streams them as timeline context to an LLM.
   - Produces a final script with continuous timing.

## Install

```bash
pip install -r requirements.txt
```

## Step 1: Video -> Sequential Frame JSON

```bash
python frame_to_json_poc.py \
  --video "C:/path/to/gameplay.mp4" \
  --output-dir "C:/path/to/output" \
  --fps 2 \
  --api-url "http://localhost:2000" \
  --model "qwen/qwen3-vl-8b"
```

Optional token:

```bash
set LM_API_TOKEN=your_token
```

Output structure:

- `output/frame_images/frame_000001.jpg`
- `output/frame_json/frame_000001.json`
- `output/sequential_frames.ndjson`
- `output/summary.json`

## Step 2: Sequential Frame JSON -> Final Script

```bash
python json_to_script_poc.py \
  --frame-json-dir "C:/path/to/output/frame_json" \
  --output "C:/path/to/output/final_script.json" \
  --api-url "http://localhost:2000" \
  --model "qwen/qwen3-14b"
```

## API Shape Used

VLM request uses one call with system prompt + text + image:

```json
{
  "model": "qwen/qwen3-vl-8b",
  "system_prompt": "...",
  "input": [
    {"type": "text", "content": "..."},
    {"type": "image", "data_url": "data:image/jpeg;base64,..."}
  ]
}
```

This follows the same `requests.post(..., json=payload)` pattern used in `desktop/backend/app/generator.py`.
