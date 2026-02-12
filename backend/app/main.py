from dotenv import load_dotenv
load_dotenv()

import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from sqlalchemy import inspect, text

from app.database import engine, Base
from app.routers import students, products, enrollments, chat, analytics, webhooks, admin, sales

# Create tables on startup (creates new tables like 'sales')
Base.metadata.create_all(bind=engine)

# Add missing columns to existing tables (create_all won't alter existing tables)
def _add_column_if_missing(table, column, col_type):
    with engine.connect() as conn:
        columns = [c["name"] for c in inspect(engine).get_columns(table)]
        if column not in columns:
            conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}"))
            conn.commit()

_add_column_if_missing("enrollments", "sale_id", "INTEGER REFERENCES sales(id)")
_add_column_if_missing("enrollments", "source", "TEXT")
_add_column_if_missing("products", "typeform_form_id", "TEXT")
_add_column_if_missing("products", "typeform_field_map", "TEXT")

app = FastAPI(title="Every Student Database", version="1.0.0")

# CORS — allow the React frontend (dev server)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(students.router)
app.include_router(products.router)
app.include_router(enrollments.router)
app.include_router(chat.router)
app.include_router(analytics.router)
app.include_router(webhooks.router)
app.include_router(admin.router)
app.include_router(sales.router)

# Serve the React frontend (built files)
FRONTEND_DIR = Path(__file__).parent.parent / "frontend_dist"

if FRONTEND_DIR.is_dir():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIR / "assets"), name="static-assets")

    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        """Serve the React SPA — any non-API route gets index.html."""
        file_path = FRONTEND_DIR / full_path
        if full_path and file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(FRONTEND_DIR / "index.html")
else:
    @app.get("/")
    def root():
        return {"message": "Every Student Database API", "docs": "/docs"}
