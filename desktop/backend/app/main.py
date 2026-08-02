from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .db import init_db
from .defaults import INPUT_FIELDS, ROW_FIELDS
from .routes.input_sets import router as input_sets_router
from .routes.plansheets import router as plansheets_router


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(title="Silicon Agent Desktop Backend", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/meta")
def meta() -> dict[str, Any]:
    """Field definitions the renderer uses to build its form and table."""
    return {"input_fields": INPUT_FIELDS, "row_fields": ROW_FIELDS}


app.include_router(input_sets_router)
app.include_router(plansheets_router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("backend.app.main:app", host="127.0.0.1", port=8000, reload=False)
