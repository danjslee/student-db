"""
Broadcast management routes — create, list, cancel, and trigger broadcasts.
"""

import json
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.database import get_db
from app.models import ScheduledBroadcast, Product
from app.broadcast_scheduler import execute_broadcast

router = APIRouter(prefix="/api/broadcasts", tags=["broadcasts"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class BroadcastCreate(BaseModel):
    name: str
    email_type: str
    product_id: int
    client: str = "every"
    scheduled_at: str  # ISO format in local time
    timezone: str = "America/New_York"
    dry_run: bool = True
    filter_tag: Optional[str] = None
    template_params: Optional[dict] = None


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------

@router.post("")
def create_broadcast(req: BroadcastCreate, db: Session = Depends(get_db)):
    """Create a scheduled broadcast. Accepts local time + timezone, converts to UTC."""
    product = db.query(Product).filter(Product.id == req.product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # Convert local time to UTC
    try:
        from zoneinfo import ZoneInfo
        from datetime import timezone
        local_tz = ZoneInfo(req.timezone)
        local_dt = datetime.fromisoformat(req.scheduled_at)
        if local_dt.tzinfo is None:
            local_dt = local_dt.replace(tzinfo=local_tz)
        utc_dt = local_dt.astimezone(timezone.utc).replace(tzinfo=None)
    except Exception:
        # Fallback: treat as UTC if parse fails
        utc_dt = datetime.fromisoformat(req.scheduled_at)

    broadcast = ScheduledBroadcast(
        name=req.name,
        email_type=req.email_type,
        product_id=req.product_id,
        client=req.client,
        scheduled_at=utc_dt,
        timezone=req.timezone,
        status="pending",
        dry_run=req.dry_run,
        filter_tag=req.filter_tag,
        template_params=json.dumps(req.template_params) if req.template_params else None,
        created_at=datetime.utcnow(),
    )
    db.add(broadcast)
    db.commit()
    db.refresh(broadcast)

    return _broadcast_to_dict(broadcast)


@router.get("")
def list_broadcasts(
    status: Optional[str] = None,
    limit: int = Query(50, le=200),
    db: Session = Depends(get_db),
):
    """List all broadcasts, newest first."""
    q = db.query(ScheduledBroadcast).order_by(ScheduledBroadcast.scheduled_at.desc())
    if status:
        q = q.filter(ScheduledBroadcast.status == status)
    return [_broadcast_to_dict(b) for b in q.limit(limit).all()]


@router.get("/{broadcast_id}")
def get_broadcast(broadcast_id: int, db: Session = Depends(get_db)):
    """Get broadcast details + send stats."""
    broadcast = db.query(ScheduledBroadcast).filter(ScheduledBroadcast.id == broadcast_id).first()
    if not broadcast:
        raise HTTPException(status_code=404, detail="Broadcast not found")
    return _broadcast_to_dict(broadcast)


@router.post("/{broadcast_id}/cancel")
def cancel_broadcast(broadcast_id: int, db: Session = Depends(get_db)):
    """Cancel a pending broadcast."""
    broadcast = db.query(ScheduledBroadcast).filter(ScheduledBroadcast.id == broadcast_id).first()
    if not broadcast:
        raise HTTPException(status_code=404, detail="Broadcast not found")
    if broadcast.status != "pending":
        raise HTTPException(status_code=400, detail=f"Cannot cancel broadcast with status '{broadcast.status}'")

    broadcast.status = "cancelled"
    db.commit()
    return _broadcast_to_dict(broadcast)


@router.post("/{broadcast_id}/send-now")
def send_now(broadcast_id: int, db: Session = Depends(get_db)):
    """Immediately execute a pending broadcast (skip scheduler wait)."""
    broadcast = db.query(ScheduledBroadcast).filter(ScheduledBroadcast.id == broadcast_id).first()
    if not broadcast:
        raise HTTPException(status_code=404, detail="Broadcast not found")
    if broadcast.status not in ("pending",):
        raise HTTPException(status_code=400, detail=f"Cannot send broadcast with status '{broadcast.status}'")

    execute_broadcast(db, broadcast)
    db.refresh(broadcast)
    return _broadcast_to_dict(broadcast)


# ---------------------------------------------------------------------------
# Manual trigger — process all due broadcasts now
# ---------------------------------------------------------------------------

@router.post("/admin/trigger")
def trigger_broadcasts(db: Session = Depends(get_db)):
    """Process all due broadcasts now (manual catch-up)."""
    now = datetime.utcnow()
    due = (
        db.query(ScheduledBroadcast)
        .filter(
            ScheduledBroadcast.status == "pending",
            ScheduledBroadcast.scheduled_at <= now,
        )
        .all()
    )

    results = []
    for broadcast in due:
        try:
            execute_broadcast(db, broadcast)
            db.refresh(broadcast)
            results.append({"id": broadcast.id, "name": broadcast.name, "status": broadcast.status})
        except Exception as e:
            results.append({"id": broadcast.id, "name": broadcast.name, "status": "error", "error": str(e)[:200]})

    return {"processed": len(results), "results": results}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _broadcast_to_dict(b: ScheduledBroadcast) -> dict:
    return {
        "id": b.id,
        "name": b.name,
        "email_type": b.email_type,
        "product_id": b.product_id,
        "client": b.client,
        "scheduled_at": b.scheduled_at.isoformat() if b.scheduled_at else None,
        "timezone": b.timezone,
        "status": b.status,
        "total_recipients": b.total_recipients,
        "sent_count": b.sent_count,
        "error_count": b.error_count,
        "created_at": b.created_at.isoformat() if b.created_at else None,
        "started_at": b.started_at.isoformat() if b.started_at else None,
        "completed_at": b.completed_at.isoformat() if b.completed_at else None,
        "dry_run": b.dry_run,
        "filter_tag": b.filter_tag,
        "error_summary": b.error_summary,
    }
