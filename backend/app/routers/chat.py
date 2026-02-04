from __future__ import annotations

import json
import os
import sqlite3

import anthropic
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
    product_id INTEGER REFERENCES products(id),
    -- Survey fields (populated from post-course survey CSV, nullable)
    response_hash TEXT,
    biggest_win TEXT,
    three_things_learned TEXT,
    confidence_after INTEGER,              -- 1-10 post-course confidence
    satisfaction TEXT,                      -- "Extremely satisfied", "Very satisfied", "Somewhat satisfied"
    recommend_score INTEGER,               -- 1-10 NPS score
    testimonial TEXT,
    improvement_suggestion TEXT,
    interest_longer_program TEXT,           -- "Definitely yes", "Probably yes", "Maybe"
    followup_topics TEXT,
    beginner_friendly_rating TEXT,          -- "Excellent", "Good", "Fair"
    expected_learning_not_covered TEXT,
    anything_else TEXT,
    survey_response_type TEXT,
    survey_start_date DATETIME,
    survey_stage_date DATETIME,
    survey_submit_date DATETIME,
    survey_network_id TEXT,
    survey_tags TEXT
);
""".strip()

SYSTEM_PROMPT = f"""You are an expert data analyst assistant for a student enrollment database.
You help users understand their student, enrollment, and course survey data.

DATABASE SCHEMA:
{SCHEMA_DESCRIPTION}

INSTRUCTIONS:
- When the user asks a data question, use the run_sql_query tool to query the database.
  You may call it zero, one, or multiple times per turn as needed.
- After receiving query results, write a clear, insightful analysis in markdown.
- Use markdown formatting: headers, bold, bullet lists, numbered lists, and tables where helpful.
- Be conversational and helpful. If the user asks a non-data question, respond normally without querying.
- If a query returns an error, explain the issue and try a corrected query.
- Only generate SELECT statements. Never attempt INSERT, UPDATE, DELETE, DROP, or ALTER.
- When presenting numbers, add context (percentages, comparisons, trends) to make the data meaningful.
- Keep responses focused and concise but thorough.
"""

TOOLS = [
    {
        "name": "run_sql_query",
        "description": "Execute a read-only SQL SELECT query against the student database. Returns rows as a list of dictionaries, or an error message if the query fails.",
        "input_schema": {
            "type": "object",
            "properties": {
                "sql": {
                    "type": "string",
                    "description": "A SQL SELECT query to execute against the SQLite database",
                }
            },
            "required": ["sql"],
        },
    }
]


def _execute_query(sql: str) -> str:
    sql_stripped = sql.strip().upper()
    if not sql_stripped.startswith("SELECT"):
        return json.dumps({"error": "Only SELECT queries are allowed."})
    try:
        conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
        cursor = conn.execute(sql)
        rows = [dict(row) for row in cursor.fetchall()]
        conn.close()
    except Exception as e:
        return json.dumps({"error": str(e)})
    if len(rows) > 100:
        return json.dumps({"rows": rows[:100], "total_count": len(rows),
            "note": f"Showing first 100 of {len(rows)} rows."})
    return json.dumps({"rows": rows, "total_count": len(rows)})


@router.post("/", response_model=ChatResponse)
async def chat(request: ChatRequest):
    if not request.messages:
        raise HTTPException(400, "Messages array cannot be empty")
    if request.messages[-1].role != "user":
        raise HTTPException(400, "Last message must be from user")

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key or api_key == "your-api-key-here":
        raise HTTPException(500, "ANTHROPIC_API_KEY not configured.")

    client = anthropic.Anthropic(api_key=api_key)
    messages = [{"role": m.role, "content": m.content} for m in request.messages]

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        tools=TOOLS,
        messages=messages,
    )

    rounds = 0
    while response.stop_reason == "tool_use" and rounds < 10:
        rounds += 1
        tool_results = []
        for block in response.content:
            if block.type == "tool_use":
                result_str = _execute_query(block.input["sql"])
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": result_str,
                })
        messages.append({"role": "assistant", "content": response.content})
        messages.append({"role": "user", "content": tool_results})
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            tools=TOOLS,
            messages=messages,
        )

    answer_parts = [block.text for block in response.content if hasattr(block, "text")]
    return ChatResponse(answer="\n\n".join(answer_parts))
