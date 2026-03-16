"""
Broadcast scheduler — asyncio loop that checks for due broadcasts every 60s.

Runs as a background task in the FastAPI lifespan. If the Fly machine is
asleep and misses a window, it catches up on next wake.
"""

import asyncio
import json
import logging
import time
from datetime import datetime

from app.database import SessionLocal
from app.email_service import (
    get_broadcast_recipients,
    send_email,
    get_unsubscribe_url,
    inject_unsubscribe_footer,
)
from app.email_templates.every import TEMPLATE_REGISTRY

logger = logging.getLogger(__name__)


async def broadcast_loop():
    """Check for due broadcasts every 60 seconds."""
    while True:
        try:
            await asyncio.to_thread(process_due_broadcasts)
        except Exception as e:
            logger.error(f"Broadcast loop error: {e}")
        await asyncio.sleep(60)


def process_due_broadcasts():
    """Find and execute all pending broadcasts that are due."""
    from app.models import ScheduledBroadcast

    db = SessionLocal()
    try:
        now = datetime.utcnow()
        due = (
            db.query(ScheduledBroadcast)
            .filter(
                ScheduledBroadcast.status == "pending",
                ScheduledBroadcast.scheduled_at <= now,
            )
            .all()
        )

        for broadcast in due:
            try:
                execute_broadcast(db, broadcast)
            except Exception as e:
                logger.error(f"Broadcast {broadcast.id} ({broadcast.name}) failed: {e}")
                broadcast.status = "partial_error"
                broadcast.error_summary = str(e)[:500]
                db.commit()
    finally:
        db.close()


def execute_broadcast(db, broadcast):
    """Execute a single broadcast — render + send to all recipients."""
    from app.models import EmailSend

    logger.info(f"Starting broadcast {broadcast.id}: {broadcast.name} (dry_run={broadcast.dry_run})")

    broadcast.status = "sending"
    broadcast.started_at = datetime.utcnow()
    db.commit()

    # Get template function
    template_fn = TEMPLATE_REGISTRY.get(broadcast.email_type)
    if not template_fn:
        broadcast.status = "partial_error"
        broadcast.error_summary = f"Unknown email_type: {broadcast.email_type}"
        db.commit()
        logger.error(f"Broadcast {broadcast.id}: unknown email_type '{broadcast.email_type}'")
        return

    # Get recipients
    recipients = get_broadcast_recipients(db, broadcast.product_id, broadcast.filter_tag)
    broadcast.total_recipients = len(recipients)
    db.commit()

    # Parse template params
    template_params = {}
    if broadcast.template_params:
        try:
            template_params = json.loads(broadcast.template_params)
        except json.JSONDecodeError:
            pass

    sent = 0
    errors = 0
    error_msgs = []

    for student_id, email, display_name in recipients:
        # Idempotency: skip if already sent for this broadcast
        existing = (
            db.query(EmailSend)
            .filter(
                EmailSend.broadcast_id == broadcast.id,
                EmailSend.to_email == email,
                EmailSend.status.in_(["sent", "delivered", "dry_run"]),
            )
            .first()
        )
        if existing:
            sent += 1  # Count as already sent
            continue

        try:
            # Render template
            rendered = template_fn(display_name, broadcast.product, **template_params)

            # Inject unsubscribe footer
            unsub_url = get_unsubscribe_url(email, broadcast.product_id)
            html = inject_unsubscribe_footer(rendered["html"], unsub_url)

            # Send
            send_email(
                db=db,
                to_email=email,
                subject=rendered["subject"],
                html=html,
                client=broadcast.client,
                email_type=broadcast.email_type,
                student_id=student_id,
                product_id=broadcast.product_id,
                broadcast_id=broadcast.id,
                dry_run=broadcast.dry_run,
            )
            sent += 1

            # Rate limit: Resend allows 2 req/sec, pause 0.6s between live sends
            if not broadcast.dry_run:
                time.sleep(0.6)

        except Exception as e:
            errors += 1
            msg = f"{email}: {str(e)[:100]}"
            error_msgs.append(msg)
            logger.error(f"Broadcast {broadcast.id} send error: {msg}")

    # Update broadcast status
    broadcast.sent_count = sent
    broadcast.error_count = errors
    broadcast.completed_at = datetime.utcnow()

    if errors == 0:
        broadcast.status = "sent"
    elif sent > 0:
        broadcast.status = "partial_error"
    else:
        broadcast.status = "partial_error"

    if error_msgs:
        broadcast.error_summary = "\n".join(error_msgs[:20])  # Cap at 20

    db.commit()
    logger.info(
        f"Broadcast {broadcast.id} complete: {sent} sent, {errors} errors "
        f"(dry_run={broadcast.dry_run})"
    )
