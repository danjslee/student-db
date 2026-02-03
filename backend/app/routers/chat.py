from __future__ import annotations

import os
import re
import sqlite3

from fastapi import APIRouter, HTTPException

from app.database import DB_PATH
from app.schemas import ChatRequest, ChatResponse

router = APIRouter(prefix="/api/chat", tags=["chat"])

SCHEMA_DESCRIPTION = """
The SQLite database has three tables:

CREATE TABLE products (
    id INTEGER PRIMARY KEY,
    product_id TEXT UNIQUE NOT NULL,   -- e.g. "ccfb"
    product_name TEXT NOT NULL,        -- e.g. "Claude Code for Beginners"
    kit_tag TEXT
);

CREATE TABLE students (
    id INTEGER PRIMARY KEY,
    student_number INTEGER UNIQUE NOT NULL,
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    preferred_name TEXT,
    email TEXT UNIQUE NOT NULL,
    alternative_email TEXT,
    country TEXT,              -- e.g. "United States", "India", "Norway"
    timezone TEXT,             -- e.g. "Eastern Standard Time (-5) / Eastern Daylight Time (-4)"
    closest_city TEXT,         -- e.g. "New York, USA", "Chennai, IND"
    dob DATE,                 -- date of birth
    gender TEXT,               -- "Male", "Female", "Rather not say"
    learn_about_course TEXT,   -- how they heard about the course
    consent_images BOOLEAN,
    consent_photo_on_site BOOLEAN,
    what_made_you_join TEXT,   -- free text about motivation
    get_from TEXT,             -- what they want from the course
    here_for TEXT,             -- why they're here
    claude_confidence_level REAL,  -- 0-10 scale
    onboarding_date DATETIME
);

CREATE TABLE enrollments (
    id INTEGER PRIMARY KEY,
    enrollment_id TEXT UNIQUE NOT NULL,  -- pattern: email_productid
    status TEXT,  -- "Paying Customer (Full-fee)", "Paying Customer (Early-bird)",
                  -- "Paying Customer (Referral)", "Scholarship (paid)",
                  -- "Scholarship (free)", "Free place", "Refunded", "Deferred"
    student_id INTEGER REFERENCES students(id),
    product_id INTEGER REFERENCES products(id)
);
""".strip()


@router.post("/", response_model=ChatResponse)
async def chat(request: ChatRequest):
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key or api_key == "your-api-key-here":
        raise HTTPException(
            500,
            "ANTHROPIC_API_KEY not configured. Set it in backend/.env",
        )

    try:
        import anthropic
    except ImportError:
        raise HTTPException(500, "anthropic package not installed")

    client = anthropic.Anthropic(api_key=api_key)

    system_prompt = f"""You are a helpful data analyst assistant. You have access to a SQLite database with the following schema:

{SCHEMA_DESCRIPTION}

When the user asks a question about the data, respond with a JSON object containing:
- "sql": a single SELECT query that answers the question (READ-ONLY, no INSERT/UPDATE/DELETE)
- "explanation": a brief natural language explanation of what the query does

IMPORTANT RULES:
- Only generate SELECT statements. Never generate INSERT, UPDATE, DELETE, DROP, ALTER, or any DDL/DML.
- Always return valid JSON with "sql" and "explanation" keys.
- Use proper SQL syntax for SQLite.
- If the question cannot be answered with a SQL query, set "sql" to null and explain why in "explanation".
"""

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        system=system_prompt,
        messages=[{"role": "user", "content": request.message}],
    )

    response_text = message.content[0].text

    # Parse the JSON from Claude's response
    import json

    # Try to extract JSON from the response (it might be wrapped in markdown code blocks)
    json_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", response_text, re.DOTALL)
    if json_match:
        parsed = json.loads(json_match.group(1))
    else:
        try:
            parsed = json.loads(response_text)
        except json.JSONDecodeError:
            return ChatResponse(answer=response_text, sql=None, data=None)

    sql = parsed.get("sql")
    explanation = parsed.get("explanation", "")

    if not sql:
        return ChatResponse(answer=explanation, sql=None, data=None)

    # Safety check: only allow SELECT
    sql_stripped = sql.strip().upper()
    if not sql_stripped.startswith("SELECT"):
        return ChatResponse(
            answer="I can only run read-only SELECT queries.",
            sql=sql,
            data=None,
        )

    # Execute the query (read-only connection)
    try:
        conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
        cursor = conn.execute(sql)
        rows = [dict(row) for row in cursor.fetchall()]
        conn.close()
    except Exception as e:
        return ChatResponse(
            answer=f"Query failed: {e}",
            sql=sql,
            data=None,
        )

    # Generate a natural language summary
    if len(rows) == 1 and len(rows[0]) == 1:
        value = list(rows[0].values())[0]
        answer = f"{explanation}\n\nResult: **{value}**"
    elif len(rows) <= 20:
        answer = f"{explanation}\n\nFound {len(rows)} result(s)."
    else:
        answer = f"{explanation}\n\nFound {len(rows)} results (showing data in table)."

    return ChatResponse(answer=answer, sql=sql, data=rows)
