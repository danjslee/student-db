from dotenv import load_dotenv
load_dotenv()

import asyncio
import base64
import hashlib
import hmac
import os
import logging
import secrets
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse

from sqlalchemy import inspect, text

from app.database import engine, Base
from app.routers import students, products, enrollments, chat, analytics, webhooks, admin, sales, qualitative, scholarships, emails, broadcasts

logger = logging.getLogger(__name__)

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
_add_column_if_missing("products", "deferred_optin_form_id", "TEXT")
_add_column_if_missing("products", "completion_survey_form_id", "TEXT")
_add_column_if_missing("products", "completion_survey_field_map", "TEXT")
_add_column_if_missing("products", "kit_onboarded_tag", "TEXT")
_add_column_if_missing("products", "kit_offboarded_tag", "TEXT")
_add_column_if_missing("products", "kit_rsvp_tag", "TEXT")
_add_column_if_missing("products", "course_start_date", "DATE")
_add_column_if_missing("products", "sales_target", "INTEGER")
_add_column_if_missing("scholarship_applications", "processing_status", "TEXT DEFAULT 'new'")
_add_column_if_missing("enrollments", "kit_tag_pending", "BOOLEAN DEFAULT 0")
_add_column_if_missing("products", "circle_access_group_id", "INTEGER")
_add_column_if_missing("products", "circle_onboarded_access_group_id", "INTEGER")
_add_column_if_missing("products", "circle_offboarded_access_group_id", "INTEGER")
_add_column_if_missing("email_sends", "broadcast_id", "INTEGER REFERENCES scheduled_broadcasts(id)")


# ---------------------------------------------------------------------------
# Lifespan — start broadcast scheduler
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.broadcast_scheduler import broadcast_loop
    from app.circle_reconciler import reconcile_loop
    broadcast_task = asyncio.create_task(broadcast_loop())
    reconcile_task = asyncio.create_task(reconcile_loop())
    logger.info("Broadcast scheduler started")
    yield
    broadcast_task.cancel()
    reconcile_task.cancel()
    for t in (broadcast_task, reconcile_task):
        try:
            await t
        except asyncio.CancelledError:
            pass
    logger.info("Background tasks stopped")


app = FastAPI(title="Every Student Database", version="1.0.0", lifespan=lifespan)

# CORS — allow the React frontend (dev server)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Auth — cookie-based login page + Basic auth fallback for API
DASHBOARD_PASSWORD = os.getenv("DASHBOARD_PASSWORD", "")
_COOKIE_NAME = "every_session"

# Paths that skip auth (webhooks need to stay public)
_PUBLIC_PREFIXES = ("/api/webhook/", "/api/emails/unsubscribe", "/docs", "/openapi.json", "/assets/", "/static/", "/login")


def _make_session_token(password: str) -> str:
    return hmac.new(password.encode(), b"every-student-db-session", hashlib.sha256).hexdigest()


@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    path = request.url.path

    # Skip auth for public paths
    if not DASHBOARD_PASSWORD or any(path.startswith(p) for p in _PUBLIC_PREFIXES):
        return await call_next(request)

    # Check session cookie first
    token = request.cookies.get(_COOKIE_NAME, "")
    if token and hmac.compare_digest(token, _make_session_token(DASHBOARD_PASSWORD)):
        return await call_next(request)

    # Fall back to Basic auth (for API/curl access)
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Basic "):
        try:
            decoded = base64.b64decode(auth[6:]).decode()
            username, password = decoded.split(":", 1)
            if secrets.compare_digest(password, DASHBOARD_PASSWORD):
                return await call_next(request)
        except Exception:
            pass

    # Redirect browsers to login page
    accept = request.headers.get("Accept", "")
    if "text/html" in accept:
        return RedirectResponse("/login", status_code=302)
    return Response(
        status_code=401,
        headers={"WWW-Authenticate": 'Basic realm="Student Dashboard"'},
        content="Unauthorized",
    )


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, error: str = ""):
    error_html = '<p style="color:#dc2626;margin-bottom:1rem">Incorrect password</p>' if error else ""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Login — Every Student Database</title>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
         background: #0c0a09; color: #ffffff;
         display: flex; align-items: center; justify-content: center; min-height: 100vh; }}
  .login-card {{ width: 340px; text-align: center; }}
  h1 {{ font-family: Georgia, 'Times New Roman', serif; font-size: 1.6rem; font-weight: 400;
       margin-bottom: 2rem; }}
  form {{ display: flex; flex-direction: column; gap: 1rem; }}
  input {{ font-family: inherit; font-size: 1rem; padding: 0.7rem 1rem;
          border: 1px solid #292524; border-radius: 6px; background: #1c1917; color: #ffffff;
          text-align: center; outline: none; }}
  input:focus {{ border-color: #b5f0f0; }}
  button {{ font-family: inherit; font-size: 1rem; font-weight: 500;
           padding: 0.7rem 1rem; background: #b5f0f0; color: #0c0a09; border: none;
           border-radius: 6px; cursor: pointer; transition: background 0.2s; }}
  button:hover {{ background: #8fd4d4; }}
</style>
</head>
<body>
<div class="login-card">
  <h1>Every Student Database</h1>
  {error_html}
  <form method="post" action="/login" autocomplete="on">
    <input type="hidden" name="username" value="admin" autocomplete="username">
    <input type="password" name="password" placeholder="Password" autocomplete="current-password" autofocus required>
    <button type="submit">Sign in</button>
  </form>
</div>
</body>
</html>"""


@app.post("/login")
async def login_submit(request: Request):
    form = await request.form()
    password = form.get("password", "")
    if secrets.compare_digest(password, DASHBOARD_PASSWORD):
        response = RedirectResponse("/", status_code=302)
        response.set_cookie(
            _COOKIE_NAME,
            _make_session_token(DASHBOARD_PASSWORD),
            max_age=60 * 60 * 24 * 30,  # 30 days
            httponly=True,
            samesite="lax",
            secure=True,
        )
        return response
    return RedirectResponse("/login?error=1", status_code=302)

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
app.include_router(scholarships.router)
app.include_router(emails.router)
app.include_router(broadcasts.router)

# Serve static email assets (logos, images)
STATIC_DIR = Path(__file__).parent.parent / "static"
if STATIC_DIR.is_dir():
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

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
