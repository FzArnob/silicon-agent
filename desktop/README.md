# Silicon Agent Desktop

Monthly plansheet manager: Electron UI, FastAPI backend, SQLite storage.

## Prerequisites

- Node.js 18+
- Python 3.10+
- A local LLM server with an OpenAI-compatible `/v1/chat/completions` route that
  supports `response_format: json_schema` (LM Studio, llama.cpp, vLLM, Ollama).
  Default `http://localhost:2000`.

## Install and run

```
run.bat setup     REM npm install + pip install
run.bat start     REM launches Electron, which starts the backend itself
```

Or manually:

```
npm install
pip install -r backend/requirements.txt
npm start
```

## How it works

Two things are stored: **input sets** and **plansheets**.

- An **input set** is a named, reusable generation configuration (channel, category,
  audience, tone, cadence, storage path, special instructions). A set named `Default`
  is seeded into the database on first run and is pre-selected. Add, edit, and delete
  sets from the *Input set* menu in the title bar. At least one set always exists.
- A **plansheet** is one month of posts. Each month records which input set it was
  generated with. Generating replaces that month's rows; rows stay editable in the grid.

Field names are identical everywhere — the form, the API payloads, and the SQLite
columns all use the same keys, with no renaming or conversion in between. The form and
the grid are built from `backend/app/defaults.py`, served over `GET /api/meta`, so the
UI cannot drift from the database.

## Layout

```
electron/main      Electron main process, spawns the backend
electron/preload   Renderer bridge to the HTTP API
electron/renderer  UI (index.html, app.js, styles.css)
backend/app        FastAPI app, routes, services, generator, schema
data/app.db        SQLite database, created and migrated on startup
backend/logs       Raw LLM responses, one file per generation
```

## API

```
GET    /api/health
GET    /api/meta                          field definitions for the UI
GET    /api/input-sets
POST   /api/input-sets
PUT    /api/input-sets/{id}
DELETE /api/input-sets/{id}
GET    /api/plansheets/{month}
PUT    /api/plansheets/{month}            save rows + selected input set
PUT    /api/plansheets/{month}/input-set  switch the month's input set
POST   /api/plansheets/{month}/generate   generate and replace rows
DELETE /api/plansheets/{month}
```

`month` is `YYYY-MM`.

## Environment

| Variable      | Default                  | Description         |
| ------------- | ------------------------ | ------------------- |
| `LLM_API_URL` | `http://localhost:2000`  | LLM base URL; `/v1/chat/completions` is appended |
| `LLM_MODEL`   | `google/gemma-4-e2b`     | Model name          |

Generation asks the server to constrain decoding to a JSON schema, so the reply is
always valid JSON with exactly the right number of posts and exactly the expected keys.
Raw replies are kept in `backend/logs/` for inspection.
