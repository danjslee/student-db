from __future__ import annotations

import logging
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Product, ScholarshipApplication
from app.schemas import (
    ScholarshipAIAssessment,
    ScholarshipApplicationCreate,
    ScholarshipApplicationRead,
    ScholarshipDecision,
    ScholarshipListFilter,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["scholarships"])


def _app_to_read(app: ScholarshipApplication) -> ScholarshipApplicationRead:
    """Convert ORM model to read schema, joining product name."""
    data = ScholarshipApplicationRead.model_validate(app)
    if app.product:
        data.product_name = app.product.product_name
    return data


@router.post("/scholarship-applications", response_model=List[ScholarshipApplicationRead])
def list_scholarship_applications(
    filters: ScholarshipListFilter = None,
    db: Session = Depends(get_db),
):
    """List scholarship applications with optional filters. POST to avoid SPA catch-all."""
    query = db.query(ScholarshipApplication)
    if filters:
        if filters.status:
            query = query.filter(ScholarshipApplication.status == filters.status)
        if filters.product_id:
            query = query.filter(ScholarshipApplication.product_id == filters.product_id)
    apps = query.order_by(ScholarshipApplication.applied_at.desc()).all()
    return [_app_to_read(a) for a in apps]


@router.post("/scholarship-applications/bulk-import")
def bulk_import_scholarships(
    applications: List[ScholarshipApplicationCreate],
    db: Session = Depends(get_db),
):
    """Bulk import scholarship applications (e.g. from CSV backfill)."""
    created = []
    skipped = []
    for app_data in applications:
        email = (app_data.email or "").lower().strip()
        if not email:
            continue
        # Dedup: skip if same email+product already exists
        existing = db.query(ScholarshipApplication).filter(
            ScholarshipApplication.email == email,
            ScholarshipApplication.product_id == app_data.product_id,
        ).first()
        if existing:
            skipped.append(email)
            continue

        applied_at = datetime.utcnow()
        if app_data.applied_at:
            try:
                applied_at = datetime.fromisoformat(app_data.applied_at)
            except (ValueError, TypeError):
                pass

        app = ScholarshipApplication(
            email=email,
            first_name=app_data.first_name or "",
            last_name=app_data.last_name or "",
            product_id=app_data.product_id,
            is_subscriber=app_data.is_subscriber,
            amount_willing_to_pay=app_data.amount_willing_to_pay,
            circumstances=app_data.circumstances,
            hopes=app_data.hopes,
            best_case_impact=app_data.best_case_impact,
            status="pending",
            applied_at=applied_at,
        )
        db.add(app)
        created.append(email)

    db.commit()
    logger.info("Bulk imported %d scholarship applications, skipped %d", len(created), len(skipped))
    return {"created": len(created), "skipped": len(skipped), "skipped_emails": skipped}


@router.post("/scholarship-applications/{app_id}/decide")
def decide_scholarship(
    app_id: int,
    decision: ScholarshipDecision,
    db: Session = Depends(get_db),
):
    """Accept or reject a scholarship application."""
    app = db.query(ScholarshipApplication).get(app_id)
    if not app:
        raise HTTPException(404, "Scholarship application not found")

    app.status = decision.status
    app.decision_tier = decision.decision_tier
    app.discount_code = decision.discount_code
    app.decision_notes = decision.decision_notes
    app.decided_at = datetime.utcnow()
    db.commit()

    logger.info("Scholarship #%d decided: %s tier=%s", app_id, decision.status, decision.decision_tier)
    return {"status": "ok", "id": app_id, "decision": decision.status}


@router.post("/scholarship-applications/{app_id}/ai-assess")
def ai_assess_scholarship(
    app_id: int,
    assessment: ScholarshipAIAssessment,
    db: Session = Depends(get_db),
):
    """Store AI recommendation for a scholarship application."""
    app = db.query(ScholarshipApplication).get(app_id)
    if not app:
        raise HTTPException(404, "Scholarship application not found")

    app.ai_recommendation = assessment.ai_recommendation
    app.ai_recommended_tier = assessment.ai_recommended_tier
    db.commit()

    logger.info("Scholarship #%d AI assessed: tier=%d", app_id, assessment.ai_recommended_tier)
    return {"status": "ok", "id": app_id, "ai_recommended_tier": assessment.ai_recommended_tier}


@router.post("/scholarship-applications/{app_id}/kit-delivered")
def mark_kit_delivered(
    app_id: int,
    db: Session = Depends(get_db),
):
    """Mark a scholarship application as delivered via Kit."""
    app = db.query(ScholarshipApplication).get(app_id)
    if not app:
        raise HTTPException(404, "Scholarship application not found")

    app.kit_delivered = True
    app.kit_delivered_at = datetime.utcnow()
    app.processing_status = "processed"
    db.commit()

    logger.info("Scholarship #%d Kit delivered", app_id)
    return {"status": "ok", "id": app_id}
