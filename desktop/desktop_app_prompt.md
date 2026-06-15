# Desktop App Build Prompt

Build a desktop application for the existing plansheet workflow using Electron for the UI, Python FastAPI for the backend, and SQLite for persistence.

## Goal

Create a simple, modern desktop app that replaces the current browser-based plansheet manager while preserving the current business logic:

- Select a month and load that month’s plansheet.
- Generate a plansheet from the existing LLM-based monthly generation flow.
- Edit plansheet rows in a table/grid.
- Save edits back to a database.
- Remove a month’s plansheet.
- Keep the UI clean, minimal, and polished.

The current app is CSV-based and uses JSON input for generation. In the new version, plansheets must be stored in SQLite, and the generation input JSON must also be persisted in SQLite instead of being used as the primary file-based source of truth.

## Current Logic To Preserve

Read the existing implementation and keep these behaviors:

- Month-based plansheet loading and editing.
- Default plansheet columns:
  - post_id
  - upload_date
  - upload_time
  - title
  - description
  - hashtags
  - keywords
  - category
  - sub_category_name
  - series_name
  - episode_number
  - landscape_video_path
  - landscape_thumbnail_path
  - portrait_video_path
  - portrait_thumbnail_path
  - ai_flag
  - kids_flag
  - status
- Generate rows using deterministic scheduling plus LLM-generated creative fields.
- Preserve the current row behaviors:
  - editable fields in a table
  - read-only post_id
  - validation for upload_date and upload_time
  - undo support
  - dirty-state tracking
  - save, generate, and remove actions

The current backend flow is:

- Load month data.
- If the month plansheet does not exist, show an empty state with a generate action.
- If it exists, show a grid for editing.
- Generate content by calling the monthly sheet generator.
- Save changes.
- Delete the month’s plansheet.

## Target Architecture

Use this stack:

- Electron as the desktop shell and UI container.
- Python FastAPI as the backend service.
- SQLite as the database.
- A clean API between Electron and FastAPI.

Recommended structure:

```text
desktop/
  electron/
    main/
    renderer/
    preload/
  backend/
    app/
    db/
    services/
    models/
    routes/
  data/
    app.db
  docs/
  README.md
```

## UI Direction

Use the existing web UI as the functional reference, but redesign it for desktop with a simple modern feel.

Keep the UI focused on these core areas:

- Month selector at the top.
- Status summary.
- Primary actions: generate, save, remove, undo.
- Spreadsheet-like editor for plansheet rows.

Design requirements:

- Minimal, modern, and easy to scan.
- Avoid clutter and unnecessary panels.
- Use a restrained visual style with good spacing, strong typography, and subtle elevation.
- Keep the table dense enough for content work, but readable.
- Make the empty state and loading state feel intentional.
- Support keyboard-driven editing where practical.

## Backend Requirements

Create a FastAPI backend that owns all plansheet persistence and generation logic.

Backend responsibilities:

- Store and retrieve plansheets by month.
- Create or update a plansheet for a month.
- Delete a month’s plansheet.
- Trigger generation for a month.
- Expose a normalized API for the Electron UI.

Use SQLite tables that support:

- monthly plansheet metadata
- saved generation input/configuration for each month
- plansheet rows
- stable row ordering
- timestamps for created/updated tracking

Suggested data model:

- plansheets table
  - id
  - month
  - created_at
  - updated_at
- plansheet_inputs table
  - id
  - plansheet_id
  - raw_input_json
  - parsed fields needed for generation
  - created_at
  - updated_at
- plansheet_rows table
  - id
  - plansheet_id
  - row_order
  - all plansheet fields listed above

## API Requirements

Implement an API similar to this:

- GET /api/plansheets/{month}
  - Return one month’s plansheet, columns, rows, and existence status.
- POST /api/plansheets/{month}
  - Save the full plansheet payload.
- DELETE /api/plansheets/{month}
  - Remove the month’s plansheet.
- POST /api/plansheets/{month}/generate
  - Generate and persist a new plansheet for the month.

Keep the response format simple and predictable so the Electron renderer can use it directly.

## Generation Logic

Preserve the current generator behavior, but adapt it to SQLite-backed storage.

The generator should still:

- Read the monthly configuration.
- Compute upload dates deterministically.
- Generate creative fields with the local LLM.
- Build deterministic media paths and metadata.
- Save the final plansheet into SQLite instead of writing CSV files.

If a month already exists, define a clear overwrite/update strategy and make it explicit in the API.

## Data Migration

Replace the current JSON-based plansheet storage with SQLite-backed storage.

Requirements:

- Do not rely on monthly CSV files as the source of truth.
- Do not rely on JSON files for saving plansheet records or generation input.
- Store the generation input/configuration in SQLite so the backend can reload or edit it later.
- If needed, provide a migration script to import existing monthly CSV files into SQLite.

## Desktop App Behavior

The Electron app should:

- Launch the FastAPI backend locally.
- Load the UI inside the Electron window.
- Communicate with the backend via HTTP.
- Handle startup and shutdown cleanly.

Expected user flow:

1. Open the desktop app.
2. See the current month and status.
3. Choose a month.
4. Load existing plansheet data or see an empty state.
5. Generate a new month if no plansheet exists.
6. Edit cells directly in the table.
7. Save changes.
8. Remove the month if needed.

## Implementation Notes

- Keep the first version simple and stable.
- Favor readability over overengineering.
- Build the UI with native-feeling desktop conventions, but keep the existing spreadsheet editing workflow.
- Use sane defaults and avoid adding unnecessary features.
- Make sure the app works offline once the local backend is running.
- If background generation takes time, show clear loading and progress states.

## Acceptance Criteria

The work is complete when:

- Electron desktop app launches successfully.
- FastAPI backend serves the desktop app data.
- SQLite stores all plansheet records.
- Month loading, editing, saving, generation, and deletion all work.
- The UI feels simple and modern.
- The previous CSV/JSON storage path is no longer the primary persistence layer for plansheets.

## Deliverables

Produce:

- A working Electron app.
- A FastAPI backend.
- SQLite schema and database initialization.
- A migration path if existing monthly CSV data needs importing.
- Clear setup and run instructions.

Start by reading the current plansheet logic, then implement the desktop architecture in small, testable steps.