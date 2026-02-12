from __future__ import annotations

import json
import logging
import os
import time
from typing import Optional, List, Dict

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Student, Enrollment

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/analytics", tags=["qualitative"])

# In-memory cache: key -> (timestamp, result)
_cache: Dict[str, tuple] = {}
CACHE_TTL = 300  # 5 minutes

# Valid fields for qualitative analysis
VALID_FIELDS = {
    "what_made_you_join": ("Student", "what_made_you_join"),
    "three_things_learned": ("Enrollment", "three_things_learned"),
    "improvement_suggestion": ("Enrollment", "improvement_suggestion"),
    "biggest_win": ("Enrollment", "biggest_win"),
    "expected_learning_not_covered": ("Enrollment", "expected_learning_not_covered"),
    "anything_else": ("Enrollment", "anything_else"),
}


class QualitativeRequest(BaseModel):
    product_ids: Optional[str] = None
    field: str


class ThemeItem(BaseModel):
    title: str
    count: int
    weight: float
    quotes: List[str] = []


class QualitativeResponse(BaseModel):
    themes: List[ThemeItem]


def _get_responses(field: str, product_ids: Optional[str], db: Session) -> List[str]:
    """Extract all non-empty text responses for the given field."""
    if field not in VALID_FIELDS:
        return []

    table_type, col_name = VALID_FIELDS[field]

    ids = None
    if product_ids:
        try:
            ids = [int(x.strip()) for x in product_ids.split(",") if x.strip()]
        except ValueError:
            ids = None

    if table_type == "Student":
        col = getattr(Student, col_name)
        q = db.query(col).filter(col.isnot(None), col != "")
        if ids:
            q = q.join(Enrollment, Enrollment.student_id == Student.id).filter(
                Enrollment.product_id.in_(ids)
            )
        return [row[0] for row in q.all()]
    else:
        col = getattr(Enrollment, col_name)
        q = db.query(col).filter(col.isnot(None), col != "")
        if ids:
            q = q.filter(Enrollment.product_id.in_(ids))
        return [row[0] for row in q.all()]


@router.post("/qualitative", response_model=QualitativeResponse)
def qualitative_analysis(
    req: QualitativeRequest,
    db: Session = Depends(get_db),
):
    if req.field not in VALID_FIELDS:
        raise HTTPException(400, f"Invalid field: {req.field}. Valid: {list(VALID_FIELDS.keys())}")

    # Check cache
    cache_key = f"{req.field}:{req.product_ids or 'all'}"
    if cache_key in _cache:
        ts, result = _cache[cache_key]
        if time.time() - ts < CACHE_TTL:
            return result

    responses = _get_responses(req.field, req.product_ids, db)
    if not responses:
        return QualitativeResponse(themes=[])

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise HTTPException(500, "ANTHROPIC_API_KEY not configured")

    # Call Anthropic API
    try:
        import httpx

        prompt = f"""Analyze these {len(responses)} student responses and identify the top 5 themes.
For each theme, provide:
- A short title (3-6 words)
- How many responses match this theme (count)
- A weight from 0 to 1 (proportion of responses)
- 2-3 representative quotes (exact text from the responses)

Respond in JSON format only:
{{"themes": [{{"title": "...", "count": N, "weight": 0.X, "quotes": ["...", "..."]}}]}}

Student responses:
{chr(10).join(f'- {r[:300]}' for r in responses[:100])}"""

        resp = httpx.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": "claude-haiku-4-5-20251001",
                "max_tokens": 1024,
                "messages": [{"role": "user", "content": prompt}],
            },
            timeout=30.0,
        )
        resp.raise_for_status()
        data = resp.json()

        # Extract text content and strip markdown fences
        text = data["content"][0]["text"].strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        if text.endswith("```"):
            text = text[:-3].strip()
        parsed = json.loads(text)
        themes = [ThemeItem(**t) for t in parsed.get("themes", [])]
        result = QualitativeResponse(themes=themes)

        # Cache result
        _cache[cache_key] = (time.time(), result)
        return result

    except json.JSONDecodeError as e:
        logger.error("Failed to parse AI response: %s", e)
        raise HTTPException(500, "Failed to parse AI analysis")
    except Exception as e:
        logger.error("Qualitative analysis failed: %s", e)
        raise HTTPException(500, f"Analysis failed: {str(e)}")
