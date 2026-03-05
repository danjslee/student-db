"""
Email management routes — preview, send, view send history, unsubscribe, webhooks.
"""

from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse
from sqlalchemy import func
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.database import get_db
from app.models import EmailSend, Student, Enrollment, Product, EmailUnsubscribe
from app.email_service import send_email, verify_unsubscribe_token
from app.email_templates import every as every_templates

router = APIRouter(prefix="/api/emails", tags=["emails"])


# ---------------------------------------------------------------------------
# Send history
# ---------------------------------------------------------------------------

@router.get("/sends")
def list_sends(
    client: Optional[str] = None,
    email_type: Optional[str] = None,
    status: Optional[str] = None,
    broadcast_id: Optional[int] = None,
    triggered_only: Optional[str] = None,
    to_email: Optional[str] = None,
    product_id: Optional[int] = None,
    student_id: Optional[int] = None,
    limit: int = Query(50, le=200),
    db: Session = Depends(get_db),
):
    """List email sends with optional filters."""
    q = db.query(EmailSend).order_by(EmailSend.timestamp.desc())
    if client:
        q = q.filter(EmailSend.client == client)
    if email_type:
        q = q.filter(EmailSend.email_type == email_type)
    if status:
        q = q.filter(EmailSend.status == status)
    if broadcast_id:
        q = q.filter(EmailSend.broadcast_id == broadcast_id)
    if triggered_only == "true":
        q = q.filter(EmailSend.broadcast_id.is_(None))
    if to_email:
        q = q.filter(EmailSend.to_email.ilike(f"%{to_email}%"))
    if product_id:
        q = q.filter(EmailSend.product_id == product_id)
    if student_id:
        q = q.filter(EmailSend.student_id == student_id)

    sends = q.limit(limit).all()
    return [
        {
            "id": s.id,
            "timestamp": s.timestamp.isoformat() if s.timestamp else None,
            "to_email": s.to_email,
            "subject": s.subject,
            "client": s.client,
            "email_type": s.email_type,
            "status": s.status,
            "dry_run": s.dry_run,
            "broadcast_id": s.broadcast_id,
            "product_id": s.product_id,
            "resend_id": s.resend_id,
            "sent_at": s.sent_at.isoformat() if s.sent_at else None,
            "error_message": s.error_message,
        }
        for s in sends
    ]


@router.get("/sends/{send_id}")
def get_send(send_id: int, db: Session = Depends(get_db)):
    """Get full details of a single email send, including rendered HTML."""
    s = db.query(EmailSend).filter(EmailSend.id == send_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Email send not found")
    return {
        "id": s.id,
        "timestamp": s.timestamp.isoformat() if s.timestamp else None,
        "to_email": s.to_email,
        "from_address": s.from_address,
        "reply_to": s.reply_to,
        "subject": s.subject,
        "html_body": s.html_body,
        "client": s.client,
        "email_type": s.email_type,
        "student_id": s.student_id,
        "product_id": s.product_id,
        "broadcast_id": s.broadcast_id,
        "dry_run": s.dry_run,
        "status": s.status,
        "resend_id": s.resend_id,
        "sent_at": s.sent_at.isoformat() if s.sent_at else None,
        "error_message": s.error_message,
    }


# ---------------------------------------------------------------------------
# Preview + Send
# ---------------------------------------------------------------------------

class EnrollmentEmailRequest(BaseModel):
    student_id: int
    product_id: int
    dry_run: bool = True


@router.post("/send/enrollment-confirmation")
def send_enrollment_confirmation(req: EnrollmentEmailRequest, db: Session = Depends(get_db)):
    """
    Preview or send an enrollment confirmation email.
    Set dry_run=false to actually send via Resend.
    """
    student = db.query(Student).filter(Student.id == req.student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    product = db.query(Product).filter(Product.id == req.product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # Verify student is actually enrolled in this product
    enrollment = (
        db.query(Enrollment)
        .filter(Enrollment.student_id == req.student_id, Enrollment.product_id == req.product_id)
        .first()
    )
    if not enrollment:
        raise HTTPException(
            status_code=400,
            detail=f"Student {student.email} is not enrolled in {product.product_name}. Email blocked.",
        )

    # Build onboarding form URL
    onboarding_url = f"https://form.typeform.com/to/{product.typeform_form_id}" if product.typeform_form_id else ""
    if not onboarding_url:
        raise HTTPException(status_code=400, detail="Product has no onboarding form configured")

    # Render template
    display_name = student.preferred_name or student.first_name
    rendered = every_templates.enrollment_confirmation(
        first_name=display_name,
        course_name=product.product_name,
        course_dates=str(product.course_start_date) if product.course_start_date else "TBD",
        course_time="See calendar invite",
        onboarding_form_url=onboarding_url,
    )

    # Send (or dry run)
    result = send_email(
        db=db,
        to_email=student.email,
        subject=rendered["subject"],
        html=rendered["html"],
        client="every",
        email_type="enrollment_confirmation",
        student_id=student.id,
        product_id=product.id,
        dry_run=req.dry_run,
    )

    result["preview"] = {
        "to": student.email,
        "subject": rendered["subject"],
        "html": rendered["html"],
    }

    return result


# ---------------------------------------------------------------------------
# Unsubscribe (public — no auth)
# ---------------------------------------------------------------------------

@router.get("/unsubscribe")
def unsubscribe(
    email: str,
    token: str,
    product_id: Optional[int] = None,
    db: Session = Depends(get_db),
):
    """Public unsubscribe endpoint. HMAC-verified. Returns HTML confirmation."""
    if not verify_unsubscribe_token(email, token):
        return HTMLResponse(
            content="<html><body><h2>Invalid unsubscribe link</h2>"
            "<p>This link may have expired or is invalid. "
            "Please reply to any course email to request removal.</p></body></html>",
            status_code=400,
        )

    email_lower = email.lower()

    # Check if already unsubscribed
    existing = (
        db.query(EmailUnsubscribe)
        .filter(
            EmailUnsubscribe.email == email_lower,
            EmailUnsubscribe.product_id == product_id,
        )
        .first()
    )

    if not existing:
        unsub = EmailUnsubscribe(
            email=email_lower,
            product_id=product_id,
            reason="link_click",
            unsubscribed_at=datetime.utcnow(),
        )
        db.add(unsub)
        db.commit()

    return HTMLResponse(
        content="<html><body style='font-family: Georgia, serif; max-width: 480px; margin: 40px auto; padding: 20px;'>"
        "<h2>You've been unsubscribed</h2>"
        "<p>You won't receive any more course emails from us. "
        "If you change your mind, just reply to any previous email.</p>"
        "</body></html>",
        status_code=200,
    )


# ---------------------------------------------------------------------------
# Admin — unsubscribes list
# ---------------------------------------------------------------------------

@router.get("/admin/unsubscribes")
def list_unsubscribes(
    limit: int = Query(100, le=500),
    db: Session = Depends(get_db),
):
    """List all unsubscribes."""
    unsubs = (
        db.query(EmailUnsubscribe)
        .order_by(EmailUnsubscribe.unsubscribed_at.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": u.id,
            "email": u.email,
            "product_id": u.product_id,
            "reason": u.reason,
            "unsubscribed_at": u.unsubscribed_at.isoformat() if u.unsubscribed_at else None,
        }
        for u in unsubs
    ]


# ---------------------------------------------------------------------------
# Admin dashboard — summary stats
# ---------------------------------------------------------------------------

@router.get("/summary")
def email_summary(db: Session = Depends(get_db)):
    """Summary stats for the email sends dashboard."""
    now = datetime.utcnow()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=today_start.weekday())

    total_today = db.query(func.count(EmailSend.id)).filter(
        EmailSend.timestamp >= today_start
    ).scalar() or 0

    total_week = db.query(func.count(EmailSend.id)).filter(
        EmailSend.timestamp >= week_start
    ).scalar() or 0

    by_status = dict(
        db.query(EmailSend.status, func.count(EmailSend.id))
        .group_by(EmailSend.status)
        .all()
    )

    # Distinct values for filter dropdowns
    clients = [r[0] for r in db.query(EmailSend.client).distinct().all() if r[0]]
    email_types = [r[0] for r in db.query(EmailSend.email_type).distinct().all() if r[0]]
    statuses = [r[0] for r in db.query(EmailSend.status).distinct().all() if r[0]]

    return {
        "today": total_today,
        "this_week": total_week,
        "by_status": by_status,
        "filter_options": {
            "clients": sorted(clients),
            "email_types": sorted(email_types),
            "statuses": sorted(statuses),
        },
    }
