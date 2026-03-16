"""
Circle access group reconciler — ensures DB enrollment state is synced to Circle.

Runs nightly at ~4am ET as a background task. Can also be triggered manually
via POST /api/admin/reconcile-circle.
"""

import asyncio
import logging
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional

from app.database import SessionLocal
from app.routers.webhooks import circle_invite_member, circle_add_to_access_group

logger = logging.getLogger(__name__)

# US Eastern offset (ET) — UTC-5 (EST) or UTC-4 (EDT)
# We approximate with UTC-4 to target ~4am ET year-round
_TARGET_HOUR_UTC = 8  # 4am ET (UTC-4)


def reconcile_circle_access(db) -> Dict[str, Any]:
    """Sync enrolled students → Circle access groups for all products.

    Safe to re-run: Circle API is idempotent for invite + access group add.
    Returns summary dict keyed by product name.
    """
    from app.models import Product, Enrollment, Student

    # Only reconcile active courses — started within the last 6 weeks
    cutoff = datetime.utcnow() - timedelta(days=42)
    products = (
        db.query(Product)
        .filter(
            Product.circle_access_group_id.isnot(None),
            Product.course_start_date >= cutoff.date(),
        )
        .all()
    )

    summary = {}

    for product in products:
        product_summary = {"enrolled_added": 0, "onboarded_added": 0, "errors": []}

        # All enrolled students for this product
        enrolled = (
            db.query(Student.email)
            .join(Enrollment, Enrollment.student_id == Student.id)
            .filter(Enrollment.product_id == product.id)
            .all()
        )

        for (email,) in enrolled:
            try:
                circle_invite_member(email)
                circle_add_to_access_group(email, product.circle_access_group_id)
                product_summary["enrolled_added"] += 1
                time.sleep(0.5)
            except Exception as e:
                product_summary["errors"].append(f"{email}: {str(e)[:100]}")
                logger.error("Circle reconcile error for %s: %s", email, e)

        # Onboarded access group — students who completed onboarding
        if product.circle_onboarded_access_group_id:
            onboarded = (
                db.query(Student.email)
                .join(Enrollment, Enrollment.student_id == Student.id)
                .filter(
                    Enrollment.product_id == product.id,
                    Student.onboarding_date.isnot(None),
                    Student.country.isnot(None),
                )
                .all()
            )

            for (email,) in onboarded:
                try:
                    circle_add_to_access_group(email, product.circle_onboarded_access_group_id)
                    product_summary["onboarded_added"] += 1
                    time.sleep(0.5)
                except Exception as e:
                    product_summary["errors"].append(f"{email} (onboarded): {str(e)[:100]}")
                    logger.error("Circle reconcile onboarded error for %s: %s", email, e)

        summary[product.product_name or f"product_{product.id}"] = product_summary

    return summary


async def reconcile_loop():
    """Background loop — runs reconciliation once daily at ~4am ET."""
    logger.info("Circle reconciler started — will run daily at ~4am ET")
    while True:
        try:
            # Sleep until next 4am ET window
            now = datetime.now(timezone.utc)
            target = now.replace(hour=_TARGET_HOUR_UTC, minute=0, second=0, microsecond=0)
            if target <= now:
                target += timedelta(days=1)
            wait_seconds = (target - now).total_seconds()
            logger.info("Circle reconciler sleeping %.0f seconds until next run", wait_seconds)
            await asyncio.sleep(wait_seconds)

            # Run reconciliation
            logger.info("Circle reconciler starting daily run")
            db = SessionLocal()
            try:
                result = await asyncio.to_thread(reconcile_circle_access, db)
                logger.info("Circle reconciler complete: %s", result)
            finally:
                db.close()

        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.error("Circle reconciler error: %s", e)
            # On error, wait 1 hour before retrying
            await asyncio.sleep(3600)
