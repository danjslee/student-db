"""
Email service — Resend integration with safety guardrails.

All emails go through send_email(), which enforces:
- dry_run mode (default True — logs but doesn't send)
- Recipient validation against student DB
- Full send logging to email_sends table
"""

import hashlib
import hmac
import os
import logging
from datetime import datetime
from typing import Optional, List, Tuple
from urllib.parse import quote

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

RESEND_API_KEY = os.getenv("RESEND_API_KEY", "")
DASHBOARD_PASSWORD = os.getenv("DASHBOARD_PASSWORD", "")
BASE_URL = os.getenv("BASE_URL", "https://every-student-db.fly.dev")


# ---------------------------------------------------------------------------
# Client email configs — add new clients here
# ---------------------------------------------------------------------------

CLIENT_CONFIGS = {
    "every": {
        "from_address": "Every Courses <courses@events.every.to>",
        "reply_to": "courses@every.to",
    },
}


# ---------------------------------------------------------------------------
# Unsubscribe token helpers (HMAC-signed)
# ---------------------------------------------------------------------------

def generate_unsubscribe_token(email: str) -> str:
    """Generate HMAC token for unsubscribe link verification."""
    key = (DASHBOARD_PASSWORD or "fallback-key").encode()
    return hmac.new(key, email.lower().encode(), hashlib.sha256).hexdigest()[:32]


def verify_unsubscribe_token(email: str, token: str) -> bool:
    """Verify an unsubscribe token matches the email."""
    expected = generate_unsubscribe_token(email)
    return hmac.compare_digest(expected, token)


def get_unsubscribe_url(email: str, product_id: Optional[int] = None) -> str:
    """Build a signed unsubscribe URL."""
    token = generate_unsubscribe_token(email)
    url = f"{BASE_URL}/api/emails/unsubscribe?email={quote(email)}&token={token}"
    if product_id:
        url += f"&product_id={product_id}"
    return url


def inject_unsubscribe_footer(html: str, unsubscribe_url: str) -> str:
    """Inject unsubscribe link into the email footer, before closing </body>."""
    unsub_html = (
        '<table role="presentation" width="100%" cellpadding="0" cellspacing="0">'
        '<tr><td align="center" style="padding: 0 20px 20px 20px;">'
        '<p style="margin:0; color:#aaaaaa; font-size:11px; font-family: Georgia, serif;">'
        f'<a href="{unsubscribe_url}" style="color:#aaaaaa; text-decoration:underline;">Unsubscribe</a>'
        '</p></td></tr></table>'
    )
    if "</body>" in html:
        return html.replace("</body>", unsub_html + "</body>")
    return html + unsub_html


# ---------------------------------------------------------------------------
# Unsubscribe check
# ---------------------------------------------------------------------------

def is_unsubscribed(db: Session, email: str, product_id: Optional[int] = None) -> bool:
    """Check if email is unsubscribed (globally or for a specific product)."""
    from app.models import EmailUnsubscribe
    q = db.query(EmailUnsubscribe).filter(EmailUnsubscribe.email == email.lower())
    if product_id:
        # Unsubscribed globally OR from this specific product
        from sqlalchemy import or_
        q = q.filter(or_(
            EmailUnsubscribe.product_id == product_id,
            EmailUnsubscribe.product_id.is_(None),
        ))
    else:
        q = q.filter(EmailUnsubscribe.product_id.is_(None))
    return q.first() is not None


# ---------------------------------------------------------------------------
# Bounce/complaint suppression check
# ---------------------------------------------------------------------------

def is_suppressed(db: Session, email: str) -> bool:
    """Check if email has bounced or complained — should not receive mail."""
    from app.models import EmailSend
    return db.query(EmailSend).filter(
        EmailSend.to_email == email,
        EmailSend.status.in_(["bounced", "complained"]),
    ).first() is not None


# ---------------------------------------------------------------------------
# Broadcast recipient query
# ---------------------------------------------------------------------------

def get_broadcast_recipients(
    db: Session, product_id: int, filter_tag: Optional[str] = None,
) -> List[Tuple]:
    """
    Get enrolled students for a broadcast, excluding unsubscribed/suppressed.

    Returns list of (student_id, email, display_name) tuples.
    """
    from app.models import Student, Enrollment, EmailUnsubscribe, EmailSend
    from sqlalchemy import or_

    # Base: enrolled students for this product
    query = (
        db.query(Student.id, Student.email, Student.preferred_name, Student.first_name)
        .join(Enrollment, Enrollment.student_id == Student.id)
        .filter(Enrollment.product_id == product_id)
        .filter(Enrollment.status != "cancelled")
    )

    # Optional: filter to students who have NOT completed the reflection survey
    if filter_tag == "not_completed_survey":
        query = query.filter(Enrollment.recommend_score.is_(None))

    rows = query.all()

    recipients = []
    for student_id, email, preferred_name, first_name in rows:
        if is_unsubscribed(db, email, product_id):
            continue
        if is_suppressed(db, email):
            continue
        display_name = preferred_name or first_name
        recipients.append((student_id, email, display_name))

    return recipients


# ---------------------------------------------------------------------------
# Send email
# ---------------------------------------------------------------------------

def send_email(
    db: Session,
    to_email: str,
    subject: str,
    html: str,
    client: str = "every",
    email_type: str = "unknown",
    student_id: Optional[int] = None,
    product_id: Optional[int] = None,
    broadcast_id: Optional[int] = None,
    dry_run: bool = True,
) -> dict:
    """
    Send an email via Resend with full logging and safety checks.

    Args:
        db: Database session for logging
        to_email: Recipient email address
        subject: Email subject line
        html: Rendered HTML body
        client: Client key (must exist in CLIENT_CONFIGS)
        email_type: Type label (e.g. "enrollment_confirmation", "session_reminder")
        student_id: Optional student DB ID for audit trail
        product_id: Optional product DB ID for audit trail
        broadcast_id: Optional broadcast ID for broadcast sends
        dry_run: If True (default), logs everything but doesn't actually send

    Returns:
        dict with status, resend_id (if sent), and any error
    """
    from app.models import EmailSend

    config = CLIENT_CONFIGS.get(client)
    if not config:
        raise ValueError(f"Unknown client '{client}'. Available: {list(CLIENT_CONFIGS.keys())}")

    # Create log entry
    log_entry = EmailSend(
        timestamp=datetime.utcnow(),
        to_email=to_email,
        from_address=config["from_address"],
        reply_to=config["reply_to"],
        subject=subject,
        html_body=html,
        client=client,
        email_type=email_type,
        student_id=student_id,
        product_id=product_id,
        broadcast_id=broadcast_id,
        dry_run=dry_run,
        status="dry_run" if dry_run else "pending",
    )
    db.add(log_entry)
    db.flush()  # Get the ID

    if dry_run:
        logger.info(f"[DRY RUN] Email '{email_type}' to {to_email} — subject: {subject}")
        db.commit()
        return {"status": "dry_run", "email_send_id": log_entry.id}

    if not RESEND_API_KEY:
        log_entry.status = "error"
        log_entry.error_message = "RESEND_API_KEY not set"
        db.commit()
        raise RuntimeError("RESEND_API_KEY not configured")

    try:
        import resend
        resend.api_key = RESEND_API_KEY

        result = resend.Emails.send({
            "from": config["from_address"],
            "to": [to_email],
            "reply_to": config["reply_to"],
            "subject": subject,
            "html": html,
        })

        resend_id = result.get("id") if isinstance(result, dict) else getattr(result, "id", None)
        log_entry.status = "sent"
        log_entry.resend_id = str(resend_id) if resend_id else None
        log_entry.sent_at = datetime.utcnow()
        db.commit()

        logger.info(f"Email '{email_type}' sent to {to_email} — resend_id: {resend_id}")
        return {"status": "sent", "resend_id": resend_id, "email_send_id": log_entry.id}

    except Exception as e:
        log_entry.status = "error"
        log_entry.error_message = str(e)[:500]
        db.commit()
        logger.error(f"Email send failed for {to_email}: {e}")
        raise
