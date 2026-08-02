# Silicon Agent Desktop — Feature Details

## Design rule

One name per piece of data, used unchanged at every layer.

`backend/app/defaults.py` declares two field lists. `INPUT_FIELDS` are the columns of
the `input_sets` table; `ROW_FIELDS` are the content columns of the `plansheet_rows`
table. Both are served to the renderer over `GET /api/meta`, and the renderer builds the
input form and the grid straight from them. SQL statements build their column lists from
the same constants. There is no mapping layer, no `raw_input_json` blob, no
comma-string-to-array conversion, and no per-layer renaming: what you type in a field is
what sits in that column.

---

## Input sets

A named, reusable generation configuration. Sets are global, not per-month.

- On first run the seeded set `Default` is inserted, and it is pre-selected everywhere.
- The *Input set* menu in the title bar selects the set for the current month.
- The gear button opens the manager: a list of sets on the left, the full field form on
  the right. Create, edit, and delete from there.
- `+ New set` starts from a copy of the selected set with a free name, so a variant is a
  few edits rather than sixteen fields of retyping.
- Set names are unique. The last remaining set cannot be deleted, which keeps the
  "always something selected" guarantee true.
- Deleting a set does not touch generated rows. Months pointing at it fall back to the
  first available set.

### Fields

| Key | Type | Notes |
| --- | --- | --- |
| `name` | text | unique, required |
| `channel_name` | text | |
| `category` | text | |
| `sub_category_name` | text | |
| `is_series` | bool | stored as `0` / `1`, shown as a toggle |
| `series_name` | text | written to rows only when `is_series` is on |
| `content_type` | text | |
| `target_audience` | text | plain comma-separated string |
| `posts_per_week` | int | |
| `goal` | text | |
| `tone` | text | |
| `duration_range_seconds` | text | |
| `language` | text | |
| `timezone` | text | |
| `storage_path` | text | base path for generated media paths |
| `special_instructions` | textarea | |

---

## Plansheets

One month of posts, keyed by `YYYY-MM`, holding the input set it was generated with.

- **Generate / Regenerate** — sends the selected set to the LLM and replaces the month's
  rows. Regenerating asks for confirmation first.
- **Save** — writes the grid back, plus the selected input set. Appears only when
  something changed. `Ctrl+S` also works.
- **Undo** — restores the grid to the last saved state. `Ctrl+Z` also works.
- **Delete month** — removes the plansheet and its rows.
- Switching months with unsaved edits asks before discarding.

### Row fields

`post_id` is generated and read-only. `date_time` uses a calendar + time picker and must
be `YYYY-MM-DD HH:mm` before a save is accepted. `ai_flag`, `kids_flag`, and `status` are
pickers (`TRUE`/`FALSE`, and `PLANNED` / `FAILED` / `COMPLETED` / `PARTIALLY COMPLETED`).
Everything else is free text. Edited cells are outlined in green until saved.

---

## Generation

Unchanged from the previous version. `backend/app/generator.py`:

1. Computes the upload window — for the current month, tomorrow through month end;
   otherwise the whole month.
2. `compute_post_slots` distributes `posts_per_week` across that window to get the post
   count.
3. `build_llm_prompt` builds the prompt from the input set.
4. `call_llm` posts to `{LLM_API_URL}/v1/chat/completions` with a 300s timeout and a
   `response_format` of `json_schema`, so the server constrains decoding to
   `build_response_schema(total_posts)`. The raw response is written to
   `backend/logs/execution_<timestamp>.log`.
5. `parse_llm_response` strips code fences and, if strict parsing still fails, repairs
   and salvages per object.
6. `build_rows` assigns `post_id`, episode numbers, and media paths under `storage_path`,
   and defaults `ai_flag` / `kids_flag` to `FALSE` and `status` to `PLANNED`.

A failure at any step returns `502` with the reason and leaves existing rows intact.

### JSON correctness

The response schema is enforced by the server, not requested in the prompt. It is
compiled into a decoding grammar, so the model physically cannot emit a token that
breaks the structure: the reply is always valid JSON, always a top-level array of
exactly `total_posts` objects, and every object has exactly `date_time`, `title`,
`description`, `hashtags`, and `keywords` — no missing keys, no extras. Quotes,
newlines, and emoji inside values are escaped correctly.

This requires an endpoint that accepts `response_format` with `json_schema`
(LM Studio, llama.cpp, vLLM, Ollama, and the OpenAI API all do). The LM Studio-native
`/api/v1/chat` route does **not**, which is why the OpenAI-compatible route is used.

`parse_llm_response` is the safety net for a server without schema support. Beyond
stripping code fences it repairs trailing commas, missing commas between objects, and a
key that lost its opening quote (`,hashtags":` → `,"hashtags":`). If the array still
will not parse, `_salvage_objects` walks the top-level `{...}` spans and parses each on
its own, so one corrupt object costs one post instead of the entire month.

---

## Database

`data/app.db`, created and migrated on backend startup.

```sql
input_sets(id, name UNIQUE, <16 input columns>, created_at, updated_at)
plansheets(id, month UNIQUE, input_set_id -> input_sets(id) ON DELETE SET NULL,
           created_at, updated_at)
plansheet_rows(id, plansheet_id -> plansheets(id) ON DELETE CASCADE, row_order,
               <17 row columns>, created_at, updated_at,
               UNIQUE (plansheet_id, row_order))
```

All row content columns are `TEXT NOT NULL DEFAULT ''`.

### Migration from the pre-input-set schema

`_migrate_legacy_tables` runs once on an older database:

- drops `plansheet_inputs` (per-month input JSON is replaced by input sets),
- adds `plansheets.input_set_id`,
- folds legacy `upload_date` + `upload_time` into `date_time` and rebuilds
  `plansheet_rows` without the dead columns, preserving every row.

`input_sets` is seeded with `Default` only when the table is empty.

---

## Errors

| Status | Cause |
| --- | --- |
| `400` | bad month format, duplicate or blank set name, unknown set, deleting the last set |
| `502` | LLM unreachable, empty response, or unparseable response |

The renderer surfaces every failure as a toast and leaves current state untouched.
