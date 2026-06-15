# Silicon Agent Desktop

Desktop plansheet manager built with Electron (UI), FastAPI (backend), and SQLite (storage).

## Structure

- electron/main: Electron main process and backend process launcher
- electron/preload: Safe renderer bridge APIs
- electron/renderer: Desktop UI
- backend/app: FastAPI app, routes, services, generator, SQLite setup
- backend/scripts: Migration scripts
- data/app.db: SQLite database created at runtime

## Prerequisites

- Node.js 18+
- Python 3.10+

## Install

1. Install Node dependencies:

   npm install

2. Install Python dependencies:

   pip install -r backend/requirements.txt

## Run

npm start

This launches Electron and starts the local FastAPI backend automatically.

## Optional Migration from Existing CSV

python backend/scripts/import_csv_to_sqlite.py

This imports monthly CSV files from social/plansheet/monthly_sheets into SQLite and stores monthly generation input in SQLite as well.

## API

- GET /api/health
- GET /api/plansheets/{month}
- PUT /api/plansheets/{month}
- POST /api/plansheets/{month}/generate
- DELETE /api/plansheets/{month}

## Notes

- Plansheet rows and generation input are both persisted in SQLite.
- Existing generator logic is preserved and adapted for DB-backed persistence.
- LLM endpoint defaults to http://localhost:2000 and model google/gemma-4-e2b.
