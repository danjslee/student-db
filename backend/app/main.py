from dotenv import load_dotenv
load_dotenv()

import os
import secrets
from pathlib import Path

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from sqlalchemy import inspect, text

from app.database import engine, Base
from app.routers import students, products, enrollments, chat, analytics, webhooks, admin, sales, qualitative

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
_add_column_if_missing("enrollments", "transformational_score", "INTEGER")
_add_column_if_missing("enrollments", "delivered_on_promise_score", "INTEGER")
_add_column_if_missing("sales", "scholarship", "INTEGER DEFAULT 0")

app = FastAPI(title="Every Student Database", version="1.0.0")

# CORS — allow the React frontend (dev server)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Basic auth — protects all routes except webhooks and static assets
DASHBOARD_PASSWORD = os.getenv("DASHBOARD_PASSWORD", "")

# Paths that skip auth (webhooks need to stay public)
_PUBLIC_PREFIXES = ("/api/webhook/", "/docs", "/openapi.json", "/assets/")


@app.middleware("http")
async def basic_auth_middleware(request: Request, call_next):
    path = request.url.path

    # Skip auth for public paths
    if not DASHBOARD_PASSWORD or any(path.startswith(p) for p in _PUBLIC_PREFIXES):
        return await call_next(request)

    # Check for Basic auth header
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Basic "):
        import base64
        try:
            decoded = base64.b64decode(auth[6:]).decode()
            username, password = decoded.split(":", 1)
            if secrets.compare_digest(password, DASHBOARD_PASSWORD):
                return await call_next(request)
        except Exception:
            pass

    # No valid auth — return 401 with WWW-Authenticate to trigger browser login prompt
    return Response(
        status_code=401,
        headers={"WWW-Authenticate": 'Basic realm="Student Dashboard"'},
        content="Unauthorized",
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
app.include_router(qualitative.router)

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
