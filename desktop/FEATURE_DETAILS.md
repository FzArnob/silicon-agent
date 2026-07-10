# Silicon Agent Desktop Application - Complete Feature Documentation

## Overview

**Silicon Agent Desktop** is a modern, Electron-based desktop application that provides a polished UI for managing social media plansheets. It replaces the browser-based CSV workflow with a SQLite-backed persistent storage system and a FastAPI backend service.

---

## Table of Contents

1. [Architecture](#architecture)
2. [Technology Stack](#technology-stack)
3. [Project Structure](#project-structure)
4. [Core Features](#core-features)
5. [Data Model](#data-model)
6. [API Specification](#api-specification)
7. [User Interface](#user-interface)
8. [Generation Logic](#generation-logic)
9. [Database Schema](#database-schema)
10. [Configuration & Defaults](#configuration--defaults)
11. [File I/O & Migration](#file-io--migration)
12. [Error Handling](#error-handling)
13. [Build & Deployment](#build--deployment)

---

## Architecture

### Three-Tier Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Electron (UI Layer)                   │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐  │
│  │ Main Process│  │ Preload API │  │ Renderer UI     │  │
│  └─────────────┘  └─────────────┘  └─────────────────┘  │
└─────────────────────────────────────────────────────────┘
                          ↕ HTTP (localhost:8000)
┌─────────────────────────────────────────────────────────┐
│              FastAPI Backend Service                     │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐  │
│  │ Routes      │  │ Services    │  │ Generator       │  │
│  └─────────────┘  └─────────────┘  └─────────────────┘  │
└─────────────────────────────────────────────────────────┘
                          ↕ SQLite Connection
┌─────────────────────────────────────────────────────────┐
│              SQLite Database (app.db)                    │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐  │
│  │ plansheets  │  │ inputs      │  │ rows            │  │
│  └─────────────┘  └─────────────┘  └─────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

### Process Flow

1. **Startup**: Electron main process spawns FastAPI backend via `uvicorn`
2. **Health Check**: Polls `/api/health` endpoint until backend is ready (30s timeout)
3. **UI Initialization**: Renderer loads and establishes connection to backend
4. **Data Operations**: All CRUD operations go through REST API
5. **Cleanup**: Backend process terminates on app quit

---

## Technology Stack

### Frontend (Electron)
- **Framework**: Electron 42.4.0
- **Language**: JavaScript (ES6+)
- **UI Pattern**: SPA with declarative DOM manipulation
- **State Management**: Custom state object with dirty tracking
- **Styling**: CSS3 with custom properties, backdrop-filter effects

### Backend (FastAPI)
- **Framework**: FastAPI 0.100+
- **Language**: Python 3.10+
- **Database Driver**: sqlite3 (stdlib)
- **CORS**: Enabled for Electron renderer communication
- **Auto-reload**: Disabled in production (`reload=False`)

### Database
- **Type**: SQLite 3.x
- **Location**: `backend/data/app.db`
- **Foreign Keys**: Enabled via PRAGMA
- **Transactions**: Context manager with commit/rollback

---

## Project Structure

```
desktop/
├── electron/
│   ├── main/
│   │   └── main.js              # Electron main process
│   ├── preload/
│   │   └── preload.js           # Secure bridge to renderer
│   └── renderer/
│       ├── app.js               # UI logic & state management
│       ├── index.html           # HTML template
│       └── styles.css           # Desktop UI styling
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py              # FastAPI app entry point
│   │   ├── db.py                # Database connection & schema
│   │   ├── defaults.py          # Default configuration values
│   │   ├── generator.py         # LLM-based generation logic
│   │   ├── routes/
│   │   │   ├── __init__.py
│   │   │   └── plansheets.py    # Plansheet API endpoints
│   │   └── services/
│   │       ├── __init__.py
│   │       └── plansheet_service.py  # Business logic layer
│   ├── data/                    # SQLite database location
│   ├── logs/                    # LLM execution logs
│   └── scripts/
│       └── import_csv_to_sqlite.py  # Migration script
├── package.json                 # Node dependencies & scripts
├── run.bat                      # Windows batch launcher
└── README.md                    # Quick start guide
```

---

## Core Features

### 1. Month Selection & Navigation

**Location**: Top-left header bar

**Components**:
- **Month Button**: Displays currently selected month (YYYY-MM format)
- **Picker Panel**: Dropdown calendar for year/month selection
- **Year Navigation**: Previous/Next year buttons
- **This Month Button**: Quick-select current calendar month

**Behavior**:
- Clicking month button opens picker panel with animation
- Grid displays all 12 months as clickable cells
- Disabled state shown for past months (optional)
- Selected month highlighted with border glow effect

### 2. Plansheet Generation

**Location**: Primary action button in top-right header

**Trigger**: `Generate` button click or API call to `/api/plansheets/{month}/generate`

**Process**:
1. Loads existing input configuration (if any)
2. Merges with provided overrides
3. Calls LLM endpoint for content generation
4. Computes deterministic upload slots
5. Saves generated rows to SQLite
6. Returns updated plansheet state

**LLM Integration**:
- **Default URL**: `http://localhost:2000`
- **Default Model**: `google/gemma-4-e2b`
- **Environment Override**: `LLM_API_URL` and `LLM_MODEL` env vars
- **Timeout**: 300 seconds per request

### 3. Data Editing

**Location**: Spreadsheet-like table in main content area

**Editable Columns**:
| Column | Editable | Notes |
|--------|----------|-------|
| post_id | ❌ No | Auto-generated, read-only |
| date_time | ✅ Yes | YYYY-MM-DD HH:mm format |
| title | ✅ Yes | Max 80 characters recommended |
| description | ✅ Yes | Max 300 characters recommended |
| hashtags | ✅ Yes | Space-separated, starts with # |
| keywords | ✅ Yes | Space-separated, no # prefix |
| category | ✅ Yes | Content category |
| sub_category_name | ✅ Yes | Sub-category name |
| series_name | ✅ Yes | Series identifier |
| episode_number | ✅ Yes | Auto-increment if empty |
| landscape_video_path | ✅ Yes | File path string |
| landscape_thumbnail_path | ✅ Yes | File path string |
| portrait_video_path | ✅ Yes | File path string |
| portrait_thumbnail_path | ✅ Yes | File path string |
| ai_flag | ✅ Yes | Boolean flag |
| kids_flag | ✅ Yes | Boolean flag |
| status | ✅ Yes | PLANNED/FAILED/COMPLETED/PARTIALLY_COMPLETED |

**Dirty State Tracking**:
- Individual cell changes tracked per row
- `dirty` flag set when any cell modified
- `inputDirty` tracks generation input changes
- `rowsDirty` tracks row data changes
- Save button visibility tied to dirty state

### 4. Data Persistence

**Save Operations**:
1. **Save (All)**: Persists both input config AND rows (`PUT /api/plansheets/{month}`)
2. **Save Input Only**: Persists generation config only, keeps rows unchanged
3. **Auto-save**: Optional implementation for form fields

**Undo Support**:
- Last change pushed to `undoStack` on save
- Undo button restores previous state
- Ctrl+Z keyboard shortcut supported
- Stack cleared on new load or generate

### 5. Data Removal

**Location**: Danger zone in top-right header

**Action**: `Remove` button deletes entire month's plansheet

**API Call**: `DELETE /api/plansheets/{month}`

**Behavior**:
- Cascades delete to inputs and rows tables
- Confirms deletion (optional UI confirmation)
- Shows success/error toast notification

---

## Data Model

### Plansheet Entity

Represents a single month's content calendar.

```python
{
    "exists": bool,              # Whether plansheet exists for this month
    "month": str,               # YYYY-MM format (e.g., "2026-07")
    "current_month": str,       # Current system month
    "columns": list[str],       # Column definitions
    "input": dict,              # Generation input configuration
    "rows": list[dict],         # Content rows
    "row_count": int            # Total row count
}
```

### Input Configuration

Generation parameters stored per-month:

```python
{
    "month": str,
    "timezone": str,           # e.g., "Asia/Dhaka"
    "channel_name": str,       # e.g., "Run Fz Run"
    "category": str,           # e.g., "Gaming"
    "sub_category_name": str,  # e.g., "Valorant"
    "target_audience": list[str],  # [region1, region2, ...]
    "content_type": str,       # e.g., "Shorts, Musical Gameplay Montages"
    "posts_per_week": int,     # Default: 7
    "is_series": bool,         # Whether this is a series
    "series_name": str,        # Series identifier if applicable
    "goal": str,               # e.g., "Maximum Reach"
    "tone": str,              # e.g., "Energetic, Engaging"
    "duration_range_seconds": str,  # e.g., "45-120"
    "language": str,          # e.g., "English"
    "storage_path": str,      # Local path for generated files
    "special_instructions": str  # Additional LLM context
}
```

### Row Schema

Individual content item:

```python
{
    "post_id": str,           # Unique identifier (auto-generated)
    "date_time": str,         # Upload timestamp
    "title": str,             # Content title
    "description": str,       # Content description
    "hashtags": str,          # Hashtag string
    "keywords": str,          # Keyword string
    "category": str,
    "sub_category_name": str,
    "series_name": str,
    "episode_number": int | str,
    "landscape_video_path": str,
    "landscape_thumbnail_path": str,
    "portrait_video_path": str,
    "portrait_thumbnail_path": str,
    "ai_flag": str,           # Boolean as string
    "kids_flag": str,         # Boolean as string
    "status": str             # Content status
}
```

---

## API Specification

### Base URL

`http://127.0.0.1:8000` (configured in preload.js)

### Endpoints

#### 1. Health Check

**Endpoint**: `GET /api/health`

**Response**:
```json
{
    "status": "ok"
}
```

**Purpose**: Verify backend is running and accepting connections.

---

#### 2. Get Plansheet

**Endpoint**: `GET /api/plansheets/{month}`

**Path Parameter**:
- `month`: YYYY-MM format (e.g., "2026-07")

**Response** (when exists):
```json
{
    "exists": true,
    "month": "2026-07",
    "current_month": "2026-07",
    "columns": ["post_id", "date_time", ...],
    "input": {
        "channel_name": "Run Fz Run",
        "posts_per_week": 7,
        ...
    },
    "rows": [
        {
            "post_id": "abc123",
            "date_time": "2026-07-01 18:30",
            "title": "...",
            ...
        }
    ],
    "row_count": 14
}
```

**Response** (when not exists):
```json
{
    "exists": false,
    "month": "2026-07",
    "current_month": "2026-07",
    "columns": [...],
    "input": {...},  // Default template
    "rows": [],
    "row_count": 0
}
```

---

#### 3. Save Plansheet

**Endpoint**: `PUT /api/plansheets/{month}`

**Path Parameter**: `month` (YYYY-MM)

**Request Body**:
```json
{
    "input": {
        "channel_name": "Run Fz Run",
        ...
    },
    "rows": [
        {
            "post_id": "...",
            "date_time": "...",
            ...
        }
    ]
}
```

**Response**: Same as GET /api/plansheets/{month}

**Notes**:
- Input and rows are optional (saves defaults if omitted)
- Overwrites existing data for the month
- Validates month format (YYYY-MM with hyphen at position 4)

---

#### 4. Generate Plansheet

**Endpoint**: `POST /api/plansheets/{month}/generate`

**Path Parameter**: `month` (YYYY-MM)

**Request Body** (optional):
```json
{
    "input": {
        "channel_name": "...",
        ...
    }
}
```

**Response**: Same as GET endpoint, with newly generated rows

**Error Response** (generation fails):
```json
{
    "detail": "LLM request failed: ..."
}
```

---

#### 5. Delete Plansheet

**Endpoint**: `DELETE /api/plansheets/{month}`

**Path Parameter**: `month` (YYYY-MM)

**Response**:
```json
{
    "ok": true
}
```

**Behavior**: Cascades delete to all related records.

---

## User Interface

### Layout Structure

```
┌─────────────────────────────────────────────────────────────┐
│  ┌──────────────────┐  ┌─────────────────────────────────┐ │
│  │ Month Selector   │  │ Generate | Save | Remove | Undo │ │
│  │ [2026-07 ▼]      │  └─────────────────────────────────┘ │
│  └──────────────────┘                                      │
│                                                             │
│  Status Bar: "Backend ready"                                │
│                                                             │
│  ┌───────────────────────────────────────────────────────┐ │
│  │ Plansheet Table                                        │ │
│  │ ┌───────────────────────────────────────────────────┐ │ │
│  │ │ post_id │ date_time │ title │ description │ ...   │ │ │
│  │ ├─────────┼───────────┼───────┼─────────────┼───────┤ │ │
│  │ │ abc123  │ 2026-07-01│ Hook  │ Watch Neon  │ ...   │ │ │
│  │ └─────────┴───────────┴───────┴─────────────┼───────┤ │ │
│  │                                              │       │ │
│  │                                              │       │ │
│  └──────────────────────────────────────────────┘         │
│                                                             │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  Generation Input Drawer (slide-out from right)             │
│  ┌───────────────────────────────────────────────────────┐ │
│  │ Channel Name: [________________]                       │ │
│  │ Category: [___________] Sub Category: [_____________] │ │
│  │ Posts Per Week: [7]                                    │ │
│  │ Timezone: [___________] Storage Path: [_____________] │ │
│  │ Target Audience: [Japan, Korea, ...]                   │ │
│  │ Special Instructions: [______________________________] │ │
│  │                                                        │ │
│  │                    [Save] [Close]                      │ │
│  └───────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### Visual Design System

**Color Palette**:
- Background 0: `#0b1020` (darkest)
- Background 1: `#111a33`
- Background 2: `#162345`
- Surface: `rgba(13, 24, 48, 0.8)`
- Line: `rgba(157, 180, 235, 0.25)`
- Text: `#e8eefc`
- Muted: `#b2c1e4`
- Primary: `#30c8d5`
- Success: `#55d67a`
- Danger: `#f07483`

**Typography**:
- Font Family: "Segoe UI", "SF Pro Text", "Helvetica Neue"
- Sizes: 12px (labels), 14px (pickers), 16px (body)

**Effects**:
- Backdrop blur: 8px
- Shadow: `0 18px 40px rgba(3, 9, 20, 0.45)`
- Border radius: 10-14px (rounded corners)

### Interactive Elements

**Buttons**:
- Primary: Cyan accent (`#30c8d5`)
- Success: Green accent (`#55d67a`)
- Danger: Red accent (`#f07483`)
- Muted: Subtle gray-blue

**States**:
- Hover: Border color brightens, subtle lift effect
- Active: Pressed state with darker background
- Disabled: 45% opacity, not-allowed cursor
- Busy: Spinner overlay on button

**Toast Notifications**:
- Position: Bottom-right corner
- Duration: Auto-dismiss (3-5 seconds)
- Types: info, success, error, warning

---

## Generation Logic

### Upload Slot Computation

The generator computes deterministic upload dates based on posting cadence.

**Algorithm**:
1. Parse month string to get year and month
2. Calculate days in month using calendar.monthrange()
3. Generate weekly slots based on posts_per_week parameter
4. Distribute posts across available weekdays
5. When posts_per_week > 7, allow multiple posts per day
6. Return ISO date strings for each slot

**Example**:
```python
compute_post_slots("2026-07", posts_per_week=7)
# Returns: ["2026-07-01", "2026-07-03", "2026-07-05", ...]
```

### LLM Prompt Construction

Builds comprehensive prompt with context from input configuration:

**Prompt Sections**:
1. **Context**: Channel, category, series, tone, audience, timezone
2. **Task**: Generate content metadata for N posts
3. **Posting Cadence**: Upload window, posts per week rules
4. **Per-Post Requirements**:
   - date_time: Optimized for peak activity
   - title: Catchy, <80 chars, music references
   - description: 2-3 sentences, CTA included, <300 chars
   - hashtags: 8-15 tags including channel tags
   - keywords: 5-10 SEO keywords without #

**Example Prompt**:
```markdown
You are a Social Media Content Planner.

CONTEXT:
- Channel: Run Fz Run
- Category: Gaming > Valorant
- Series: Neon - Valorant Music Montages
- Tone: Energetic, Engaging, Trendy, Fun
- Language: English
- Target audience regions: Japan, Korea, India, Indonesia, Philippines, Bangladesh
- Timezone for upload times: Asia/Dhaka
- Duration: 45-120 seconds
- Goal: Maximum Reach
- Special instructions: Music-driven Valorant Neon montage series...

TASK:
Generate content metadata for exactly 14 posts.

POSTING CADENCE:
- Required posts per week: 7
- Allowed upload date window: 2026-07-01 to 2026-07-31
- You decide date_time.
- When posts_per_week is greater than 7, multiple posts on the same date are expected.

For EACH post, provide:
1. date_time - YYYY-MM-DD HH:mm format in Asia/Dhaka timezone
2. title - catchy, engaging, under 80 characters
3. description - 2-3 sentences, engaging, include call-to-action
4. hashtags - 8-15 space-separated hashtags starting with #
5. keywords - 5-10 space-separated keywords WITHOUT #

OUTPUT FORMAT:
Return ONLY a valid JSON array...
```

### Response Parsing

Handles LLM response variations:
1. **Markdown Code Blocks**: Extracts JSON from ```json ... ``` blocks
2. **Trailing Commas**: Removes invalid trailing commas before } or ]
3. **Missing Commas**: Adds missing commas between objects
4. **Validation**: Ensures parsed result is a valid JSON array

### Fallback Behavior

If LLM call fails:
- Returns empty rows list
- Logs error to `backend/logs/execution_*.log`
- UI shows error toast notification

---

## Database Schema

### Tables

#### 1. plansheets

Main metadata table for each month's plansheet.

```sql
CREATE TABLE IF NOT EXISTS plansheets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    month TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

**Indexes**: None (single-column unique constraint)

---

#### 2. plansheet_inputs

Stores generation configuration for each plansheet.

```sql
CREATE TABLE IF NOT EXISTS plansheet_inputs (
    plansheet_id INTEGER PRIMARY KEY,
    month TEXT NOT NULL,
    raw_input_json TEXT NOT NULL,
    channel_name TEXT,
    category TEXT,
    sub_category_name TEXT,
    series_name TEXT,
    content_type TEXT,
    posts_per_week INTEGER,
    is_series INTEGER,
    goal TEXT,
    tone TEXT,
    duration_range_seconds TEXT,
    language TEXT,
    timezone TEXT,
    storage_path TEXT,
    special_instructions TEXT,
    target_audience_json TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (plansheet_id) REFERENCES plansheets(id) ON DELETE CASCADE
);
```

**Indexes**: None (foreign key provides join capability)

---

#### 3. plansheet_rows

Individual content rows with all field values.

```sql
CREATE TABLE IF NOT EXISTS plansheet_rows (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    plansheet_id INTEGER NOT NULL,
    row_order INTEGER NOT NULL,
    post_id TEXT NOT NULL,
    date_time TEXT,
    title TEXT,
    description TEXT,
    hashtags TEXT,
    keywords TEXT,
    category TEXT,
    sub_category_name TEXT,
    series_name TEXT,
    episode_number INTEGER,
    landscape_video_path TEXT,
    landscape_thumbnail_path TEXT,
    portrait_video_path TEXT,
    portrait_thumbnail_path TEXT,
    ai_flag TEXT,
    kids_flag TEXT,
    status TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (plansheet_id) REFERENCES plansheets(id) ON DELETE CASCADE,
    UNIQUE (plansheet_id, row_order)
);
```

**Indexes**:
```sql
CREATE INDEX IF NOT EXISTS idx_plansheet_rows_sheet_order
    ON plansheet_rows (plansheet_id, row_order);
```

---

#### Schema Migration

Handles backward compatibility with `upload_date` and `upload_time` columns:

```python
def _migrate_plansheet_rows_schema(connection):
    columns_info = connection.execute("PRAGMA table_info(plansheet_rows)").fetchall()
    column_names = {str(row[1]) for row in columns_info}

    if "date_time" not in column_names:
        connection.execute("ALTER TABLE plansheet_rows ADD COLUMN date_time TEXT")

    if "upload_date" in column_names:
        connection.execute(
            """
            UPDATE plansheet_rows
            SET date_time =
                CASE
                    WHEN TRIM(COALESCE(upload_date, '')) = '' THEN ''
                    ELSE TRIM(upload_date) || ' ' ||
                        CASE
                            WHEN TRIM(COALESCE(upload_time, '')) = '' THEN '00:00'
                            ELSE TRIM(upload_time)
                        END
                END
            WHERE TRIM(COALESCE(date_time, '')) = ''
            """
        )
```

---

## Configuration & Defaults

### Default Generation Input

Located in `backend/app/defaults.py`:

```python
DEFAULT_PLAN_INPUT = {
    "month": "",
    "timezone": "Asia/Dhaka",
    "channel_name": "Run Fz Run",
    "category": "Gaming",
    "sub_category_name": "Valorant",
    "target_audience": [
        "Japan", "Korea", "India", "Indonesia", 
        "Philippines", "Bangladesh"
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
```

### Required Columns

All tables use this column definition:

```python
REQUIRED_COLUMNS = [
    "post_id", "date_time",
    "title", "description", "hashtags", "keywords",
    "category", "sub_category_name", "series_name", "episode_number",
    "landscape_video_path", "landscape_thumbnail_path",
    "portrait_video_path", "portrait_thumbnail_path",
    "ai_flag", "kids_flag", "status",
]
```

### Status Values

Valid status enum:

```python
STATUS_VALUES = ["PLANNED", "FAILED", "COMPLETED", "PARTIALLY COMPLETED"]
```

---

## File I/O & Migration

### Database Initialization

Called on backend startup and before each connection:

```python
def init_db() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DATABASE_PATH) as connection:
        connection.execute("PRAGMA foreign_keys = ON;")
        connection.executescript(SCHEMA_SQL)
        _migrate_plansheet_rows_schema(connection)
        connection.commit()
```

**Database Location**: `backend/data/app.db`

---

### CSV Import Migration Script

Located in `backend/scripts/import_csv_to_sqlite.py`:

**Purpose**: Migrate existing monthly CSV files from `social/plansheet/monthly_sheets/` into SQLite.

**Usage**:
```bash
python backend/scripts/import_csv_to_sqlite.py
```

**Behavior**:
1. Reads all CSV files from monthly_sheets directory
2. Parses each row's fields
3. Inserts into plansheet_rows table
4. Stores generation input in plansheet_inputs table
5. Creates plansheet metadata records

**Notes**:
- Does NOT rely on CSV as source of truth after migration
- Generation input stored in SQLite for future edits
- Can be run multiple times (idempotent)

---

## Error Handling

### API Error Responses

**400 Bad Request**: Invalid month format

```json
{
    "detail": "Invalid month format. Use YYYY-MM."
}
```

**500 Internal Server Error**: Generation failure

```json
{
    "detail": "LLM request failed: ..."
}
```

### UI Error Handling

**Toast Notifications**:
- **Error**: Red background, error icon
- **Success**: Green background, checkmark icon
- **Info**: Blue background, info icon
- **Warning**: Yellow background, warning icon

**Busy State**:
- Spinner overlay on buttons during async operations
- Disabled button state while processing
- Status bar shows operation name

### Backend Startup Errors

If backend fails to start within 30 seconds:
- Console logs: "Backend did not become ready in time."
- UI shows error toast
- Status bar displays connection error

---

## Build & Deployment

### Prerequisites

**System Requirements**:
- Node.js 18+
- Python 3.10+
- Windows (primary target), macOS, Linux supported

### Installation Steps

#### 1. Install Node Dependencies

```bash
npm install
```

Creates `node_modules/` with Electron and dev dependencies.

---

#### 2. Install Python Dependencies

```bash
pip install -r backend/requirements.txt
```

Installs FastAPI, uvicorn, requests, and other Python packages.

---

#### 3. Initialize Database

```bash
python backend/scripts/import_csv_to_sqlite.py
```

Or via batch script:
```bash
run.bat init-db
```

Creates `backend/data/app.db` with schema.

---

### Running the Application

#### Quick Start (Batch Script)

```bash
run.bat
```

Automatically:
1. Installs Node dependencies
2. Installs Python dependencies
3. Starts backend and Electron UI

---

#### Manual Start

**Step 1**: Install dependencies
```bash
npm install
pip install -r backend/requirements.txt
```

**Step 2**: Start application
```bash
npm start
```

Or via batch:
```bash
run.bat all
```

---

### Available Batch Commands

| Command | Description |
|---------|-------------|
| `setup` | Full setup (node + python deps) |
| `node-deps` | Install Node dependencies only |
| `py-deps` | Install Python dependencies only |
| `init-db` | Initialize SQLite database |
| `import-csv` | Import CSV files to SQLite |
| `backend` | Start FastAPI backend only |
| `electron` | Start Electron UI only (backend must be running) |
| `dev` | Development mode (both processes) |
| `all` | Full setup and start |
| `help` | Show all commands |

---

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `LLM_API_URL` | `http://localhost:2000` | LLM service endpoint |
| `LLM_MODEL` | `google/gemma-4-e2b` | LLM model name |
| `PYTHONUNBUFFERED` | `1` | Disable Python output buffering |
| `PYTHONPATH` | Auto-set | Project root for imports |

---

### Log Files

**Location**: `backend/logs/`

**Files**:
- `execution_YYYYMMDD_HHMMSS.log` - LLM request/response logs
- Backend stdout/stderr (in terminal)

---

## Troubleshooting

### Backend Not Starting

**Symptoms**: Status bar shows "Backend unavailable"

**Solutions**:
1. Check Python installation: `python --version`
2. Verify requirements installed: `pip list`
3. Check backend logs in terminal
4. Ensure port 8000 is not in use

---

### LLM Generation Fails

**Symptoms**: Empty rows after generate, error toast

**Solutions**:
1. Verify LLM service running at configured URL
2. Check `LLM_API_URL` environment variable
3. Review log file in `backend/logs/`
4. Test LLM endpoint manually with curl

---

### Database Errors

**Symptoms**: SQLite connection errors, schema issues

**Solutions**:
1. Delete `backend/data/app.db` and reinitialize
2. Run `run.bat init-db`
3. Check disk space for database file

---

### Electron Crashes

**Symptoms**: App closes immediately on startup

**Solutions**:
1. Reinstall Node dependencies: `npm install`
2. Clear Electron cache: delete `node_modules/.cache/`
3. Check console for JavaScript errors
4. Verify backend is running before launch

---

## Security Considerations

### Preload Script Isolation

The preload script uses `contextBridge` to expose only necessary APIs:

```javascript
contextBridge.exposeInMainWorld("desktopApi", {
  health: () => request("/api/health"),
  getPlansheet: (month) => request(`/api/plansheets/${encodeURIComponent(month)}`),
  savePlansheet: (month, body) => request(`/api/plansheets/${encodeURIComponent(month)}`, {
    method: "PUT",
    body: JSON.stringify(body || {}),
  }),
  generatePlansheet: (month, body) => request(`/api/plansheets/${encodeURIComponent(month)}/generate`, {
    method: "POST",
    body: JSON.stringify(body || {}),
  }),
  deletePlansheet: (month) => request(`/api/plansheets/${encodeURIComponent(month)}`, {
    method: "DELETE",
  }),
});
```

**Security Features**:
- Context isolation enabled
- Node integration disabled in renderer
- Sandboxed mode off (for development flexibility)
- No direct file system access from renderer

---

## Performance Considerations

### Database Optimization

- Foreign keys enabled via PRAGMA
- Index on (plansheet_id, row_order) for efficient row retrieval
- Row factory set to sqlite.Row for dict-like access

### Memory Management

- Electron main process manages backend lifecycle
- Renderer state reset on month change
- Undo stack limited to last operation

### Network Optimization

- Backend runs locally (no network latency)
- Single HTTP connection pool
- Minimal payload sizes (JSON only)

---

## Future Enhancements

### Potential Features

1. **Multi-user Support**: Add authentication layer
2. **Export/Import**: CSV export, backup/restore functionality
3. **Notifications**: Desktop notifications for generation completion
4. **Dark/Light Theme**: Toggleable theme system
5. **Keyboard Shortcuts**: Enhanced shortcut mapping
6. **Search/Filter**: Filter rows by category, status, etc.
7. **Drag-and-Drop**: Reorder rows visually
8. **Batch Operations**: Select multiple rows for bulk edit
9. **Version History**: Track changes over time
10. **Cloud Sync**: Sync plansheets across devices

---

## License & Attribution

This application is part of the Silicon Agent project. See root directory LICENSE file for terms.

---

## Support

For issues, questions, or contributions:
- Check README.md for quick start
- Review this documentation for detailed behavior
- Inspect source code in `electron/`, `backend/` directories
- Check logs in `backend/logs/` for runtime errors

---

**Version**: 0.1.0  
**Last Updated**: 2026-07-10  
**Author**: Silicon Agent Team
