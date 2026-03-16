from __future__ import annotations

import json
import logging
import os
import time
from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy import func, desc, case, and_
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Enrollment, Product, Student, WebhookEvent

logger = logging.getLogger(__name__)

router = APIRouter(tags=["admin"])


@router.post("/api/admin/reconcile-circle")
def reconcile_circle(db: Session = Depends(get_db)):
    """Manually trigger Circle access group reconciliation."""
    from app.circle_reconciler import reconcile_circle_access
    result = reconcile_circle_access(db)
    return {"status": "ok", "summary": result}


@router.get("/api/admin/overview")
def admin_overview(db: Session = Depends(get_db)):
    """Aggregated view of all products, triggers, and enrollment stats."""
    products = (
        db.query(
            Product,
            func.count(Enrollment.id).label("enrollment_count"),
        )
        .outerjoin(Enrollment)
        .group_by(Product.id)
        .order_by(desc(func.count(Enrollment.id)))
        .all()
    )

    total_students = db.query(func.count(Student.id)).scalar()
    total_enrollments = db.query(func.count(Enrollment.id)).scalar()

    # Recent enrollments (last 20)
    recent = (
        db.query(Enrollment)
        .order_by(desc(Enrollment.id))
        .limit(20)
        .all()
    )

    flows = []
    archived_flows = []
    for product, count in products:
        # Enrollment flow — triggers that create student + enrollment
        triggers = []
        has_active_trigger = False
        if product.kit_tag:
            triggers.append({"type": "Kit", "identifier": product.kit_tag,
                             "url": f"/api/webhook/kit/{product.kit_tag}"})
            has_active_trigger = True
        if product.stripe_price_id:
            triggers.append({"type": "Stripe", "identifier": product.stripe_price_id,
                             "url": "/api/webhook/stripe"})
            has_active_trigger = True
        # Only show Form as a trigger if no other triggers are configured
        if not has_active_trigger:
            triggers.append({"type": "Form", "identifier": product.product_id,
                             "url": f"/api/webhook/form/{product.product_id}"})

        # Count enrollments from enrollment sources (exclude typeform-created ones)
        from sqlalchemy import or_
        enrollment_count = (
            db.query(func.count(Enrollment.id))
            .filter(
                Enrollment.product_id == product.id,
                or_(Enrollment.source != "typeform", Enrollment.source.is_(None)),
            )
            .scalar()
        )
        enrollment_flow = {
            "product_id": product.product_id,
            "product_name": product.product_name,
            "flow_type": "Enrollment Flow",
            "description": f"When a new student signs up for {product.product_name}, "
                           f"auto-create their student record and enrollment.",
            "enrollment_count": enrollment_count,
            "triggers": triggers,
        }

        if has_active_trigger:
            flows.append(enrollment_flow)
        else:
            archived_flows.append(enrollment_flow)

        # Deferred opt-in — lets deferred students opt into a new cohort
        if product.deferred_optin_form_id:
            optin_count = (
                db.query(func.count(Enrollment.id))
                .filter(
                    Enrollment.product_id == product.id,
                    Enrollment.source == "typeform",
                )
                .scalar()
            )
            flows.append({
                "product_id": product.product_id,
                "product_name": product.product_name,
                "flow_type": "Deferred Opt-In",
                "description": f"Deferred students can opt in to {product.product_name} "
                               f"via a Typeform — auto-enrolls on submission.",
                "enrollment_count": optin_count,
                "triggers": [{"type": "Typeform", "identifier": product.deferred_optin_form_id,
                              "url": f"/api/webhook/typeform/{product.product_id}"}],
            })

        # Onboarding form — post-enrollment enrichment via Typeform
        if product.typeform_form_id:
            # Count students who have completed onboarding for this product
            onboarded_count = (
                db.query(func.count(Student.id))
                .join(Enrollment, Enrollment.student_id == Student.id)
                .filter(
                    Enrollment.product_id == product.id,
                    Student.onboarding_date.isnot(None),
                )
                .scalar()
            )
            flows.append({
                "product_id": product.product_id,
                "product_name": product.product_name,
                "flow_type": "Onboarding Form Complete",
                "description": f"After enrolling in {product.product_name}, "
                               f"students complete the onboarding form to provide "
                               f"personal details, preferences, and consents.",
                "enrollment_count": onboarded_count,
                "triggers": [{"type": "Typeform", "identifier": product.typeform_form_id,
                              "url": f"/api/webhook/typeform/{product.product_id}"}],
            })

    recent_list = []
    for e in recent:
        student = db.query(Student).filter(Student.id == e.student_id).first()
        prod = db.query(Product).filter(Product.id == e.product_id).first()
        recent_list.append({
            "enrollment_id": e.enrollment_id,
            "student_email": student.email if student else "?",
            "student_name": f"{student.first_name} {student.last_name}".strip() if student else "?",
            "product": prod.product_name if prod else "?",
            "status": e.status,
        })

    # Per-product course metrics (students + NPS)
    all_products = db.query(Product).all()
    course_metrics = []
    for p in all_products:
        student_count = (
            db.query(func.count(func.distinct(Enrollment.student_id)))
            .filter(Enrollment.product_id == p.id)
            .scalar()
        )
        # NPS: promoters (9-10) minus detractors (0-6), as % of responses
        nps_rows = (
            db.query(
                func.count(Enrollment.id).label("total"),
                func.sum(case(
                    (Enrollment.recommend_score >= 9, 1), else_=0
                )).label("promoters"),
                func.sum(case(
                    (Enrollment.recommend_score <= 6, 1), else_=0
                )).label("detractors"),
            )
            .filter(
                Enrollment.product_id == p.id,
                Enrollment.recommend_score.isnot(None),
            )
            .first()
        )
        nps = None
        nps_responses = 0
        if nps_rows and nps_rows.total and nps_rows.total > 0:
            nps_responses = nps_rows.total
            promoter_pct = (nps_rows.promoters or 0) / nps_rows.total * 100
            detractor_pct = (nps_rows.detractors or 0) / nps_rows.total * 100
            nps = round(promoter_pct - detractor_pct)

        has_trigger = bool(p.kit_tag or p.stripe_price_id)
        course_metrics.append({
            "product_id": p.product_id,
            "product_name": p.product_name,
            "students": student_count,
            "nps": nps,
            "nps_responses": nps_responses,
            "status": "active" if has_trigger else "archived",
        })

    return {
        "total_students": total_students,
        "total_enrollments": total_enrollments,
        "total_products": len(flows),
        "flows": flows,
        "archived_flows": archived_flows,
        "recent_enrollments": recent_list,
        "course_metrics": course_metrics,
    }


@router.post("/api/admin/retry-kit-tags")
def retry_kit_tags(db: Session = Depends(get_db)):
    """Retry Kit tagging for all enrollments where kit_tag_pending=True."""
    from app.routers.webhooks import kit_tag_subscriber_by_email

    pending = (
        db.query(Enrollment)
        .filter(Enrollment.kit_tag_pending == True)
        .all()
    )

    if not pending:
        return {"status": "nothing_to_retry", "pending_count": 0}

    results = []  # type: List[dict]
    succeeded = 0
    failed = 0

    for enrollment in pending:
        student = db.query(Student).filter(Student.id == enrollment.student_id).first()
        product = db.query(Product).filter(Product.id == enrollment.product_id).first()

        if not student or not product or not product.kit_rsvp_tag:
            # No tag configured (product changed?) — clear the flag
            enrollment.kit_tag_pending = False
            db.commit()
            results.append({
                "enrollment_id": enrollment.enrollment_id,
                "status": "cleared",
                "reason": "no kit_rsvp_tag configured on product",
            })
            succeeded += 1
            continue

        tagged = kit_tag_subscriber_by_email(student.email, product.kit_rsvp_tag)
        if tagged:
            enrollment.kit_tag_pending = False
            db.commit()
            logger.info("Retry succeeded: %s tagged with '%s'", student.email, product.kit_rsvp_tag)
            results.append({
                "enrollment_id": enrollment.enrollment_id,
                "email": student.email,
                "tag": product.kit_rsvp_tag,
                "status": "success",
            })
            succeeded += 1
        else:
            logger.error("Retry failed: %s tag '%s'", student.email, product.kit_rsvp_tag)
            results.append({
                "enrollment_id": enrollment.enrollment_id,
                "email": student.email,
                "tag": product.kit_rsvp_tag,
                "status": "failed",
            })
            failed += 1

    return {
        "status": "completed",
        "total": len(pending),
        "succeeded": succeeded,
        "failed": failed,
        "details": results,
    }


@router.get("/api/admin/pending-kit-tags")
def pending_kit_tags(db: Session = Depends(get_db)):
    """List all enrollments with kit_tag_pending=True (for visibility before retrying)."""
    pending = (
        db.query(Enrollment)
        .filter(Enrollment.kit_tag_pending == True)
        .all()
    )

    items = []
    for enrollment in pending:
        student = db.query(Student).filter(Student.id == enrollment.student_id).first()
        product = db.query(Product).filter(Product.id == enrollment.product_id).first()
        items.append({
            "enrollment_id": enrollment.enrollment_id,
            "email": student.email if student else "?",
            "product": product.product_name if product else "?",
            "kit_rsvp_tag": product.kit_rsvp_tag if product else None,
            "source": enrollment.source,
        })

    return {"count": len(items), "enrollments": items}


@router.get("/api/admin/webhook-health")
def webhook_health(db: Session = Depends(get_db)):
    """Webhook event stats, staleness detection, and recent errors."""
    now = datetime.utcnow()
    cutoff_24h = now - timedelta(hours=24)
    cutoff_7d = now - timedelta(days=7)

    all_endpoints = [
        "kit", "stripe", "form",
        "typeform_scholarship", "typeform_onboarding", "typeform_completion",
    ]

    # Per-endpoint stats
    endpoint_stats = {}
    for ep in all_endpoints:
        stats_24h = (
            db.query(
                WebhookEvent.status,
                func.count(WebhookEvent.id),
            )
            .filter(WebhookEvent.endpoint == ep, WebhookEvent.timestamp >= cutoff_24h)
            .group_by(WebhookEvent.status)
            .all()
        )
        stats_7d = (
            db.query(
                WebhookEvent.status,
                func.count(WebhookEvent.id),
            )
            .filter(WebhookEvent.endpoint == ep, WebhookEvent.timestamp >= cutoff_7d)
            .group_by(WebhookEvent.status)
            .all()
        )
        last_event = (
            db.query(WebhookEvent.timestamp)
            .filter(WebhookEvent.endpoint == ep)
            .order_by(desc(WebhookEvent.timestamp))
            .first()
        )

        # Downstream success rates (7d)
        downstream_7d = (
            db.query(
                func.count(WebhookEvent.id).label("total"),
                func.sum(case((WebhookEvent.kit_tagged == True, 1), else_=0)).label("kit_tagged"),
                func.sum(case((WebhookEvent.circle_invited == True, 1), else_=0)).label("circle_invited"),
                func.sum(case((WebhookEvent.circle_access_group_added == True, 1), else_=0)).label("circle_ag"),
                func.sum(case((WebhookEvent.enrollment_created == True, 1), else_=0)).label("enrolled"),
            )
            .filter(
                WebhookEvent.endpoint == ep,
                WebhookEvent.timestamp >= cutoff_7d,
                WebhookEvent.status == "success",
            )
            .first()
        )

        endpoint_stats[ep] = {
            "counts_24h": {s: c for s, c in stats_24h},
            "counts_7d": {s: c for s, c in stats_7d},
            "last_fired": last_event[0].isoformat() if last_event and last_event[0] else None,
            "downstream_7d": {
                "total": downstream_7d.total if downstream_7d else 0,
                "kit_tagged": downstream_7d.kit_tagged if downstream_7d else 0,
                "circle_invited": downstream_7d.circle_invited if downstream_7d else 0,
                "circle_access_group": downstream_7d.circle_ag if downstream_7d else 0,
                "enrollment_created": downstream_7d.enrolled if downstream_7d else 0,
            },
        }

    # Staleness detection per active product
    staleness_alerts = []
    products = db.query(Product).all()
    for p in products:
        has_trigger = bool(p.kit_tag or p.stripe_price_id)
        if not has_trigger:
            continue

        has_enrollments = db.query(Enrollment.id).filter(Enrollment.product_id == p.id).first() is not None
        if not has_enrollments:
            continue

        # Determine phase
        start = p.course_start_date
        today = now.date()
        if start and today >= start and today <= start + timedelta(days=30):
            phase = "active"
            enrollment_threshold = timedelta(days=7)
            onboarding_threshold = timedelta(days=2)
        elif start and today < start:
            phase = "pre_course"
            enrollment_threshold = timedelta(days=7)
            onboarding_threshold = None
        else:
            continue  # post-course / idle — suppress

        # Check enrollment endpoints (kit, stripe, form)
        last_enrollment = (
            db.query(func.max(WebhookEvent.timestamp))
            .filter(
                WebhookEvent.endpoint.in_(["kit", "stripe", "form"]),
                WebhookEvent.product_id == p.product_id,
                WebhookEvent.status == "success",
            )
            .scalar()
        )
        if last_enrollment and now - last_enrollment > enrollment_threshold:
            staleness_alerts.append({
                "product": p.product_name,
                "product_id": p.product_id,
                "flow": "enrollment",
                "last_seen": last_enrollment.isoformat(),
                "threshold_hours": int(enrollment_threshold.total_seconds() / 3600),
                "severity": "red" if now - last_enrollment > enrollment_threshold * 2 else "amber",
            })
        elif not last_enrollment and phase == "active":
            staleness_alerts.append({
                "product": p.product_name,
                "product_id": p.product_id,
                "flow": "enrollment",
                "last_seen": None,
                "threshold_hours": int(enrollment_threshold.total_seconds() / 3600),
                "severity": "red",
            })

        # Check onboarding/completion (active phase only)
        if onboarding_threshold:
            for ep_name, ep_label in [("typeform_onboarding", "onboarding"), ("typeform_completion", "completion")]:
                last_tf = (
                    db.query(func.max(WebhookEvent.timestamp))
                    .filter(
                        WebhookEvent.endpoint == ep_name,
                        WebhookEvent.product_id == p.product_id,
                        WebhookEvent.status == "success",
                    )
                    .scalar()
                )
                if last_tf and now - last_tf > onboarding_threshold:
                    staleness_alerts.append({
                        "product": p.product_name,
                        "product_id": p.product_id,
                        "flow": ep_label,
                        "last_seen": last_tf.isoformat(),
                        "threshold_hours": int(onboarding_threshold.total_seconds() / 3600),
                        "severity": "red" if now - last_tf > onboarding_threshold * 2 else "amber",
                    })

    # Recent errors (last 10)
    recent_errors = (
        db.query(WebhookEvent)
        .filter(WebhookEvent.status == "error")
        .order_by(desc(WebhookEvent.timestamp))
        .limit(10)
        .all()
    )

    return {
        "generated_at": now.isoformat(),
        "endpoints": endpoint_stats,
        "staleness_alerts": staleness_alerts,
        "recent_errors": [
            {
                "id": e.id,
                "timestamp": e.timestamp.isoformat(),
                "endpoint": e.endpoint,
                "product_id": e.product_id,
                "email": e.email,
                "error_message": e.error_message,
                "duration_ms": e.duration_ms,
            }
            for e in recent_errors
        ],
    }


@router.get("/api/admin/api-status")
def api_status():
    """Live-test external API connections (Kit, Circle) and report config status."""
    import urllib.request
    import urllib.error

    results = {}

    # Kit: test with a lightweight GET
    kit_key = os.getenv("KIT_API_KEY", "")
    if kit_key:
        try:
            start = time.time()
            req = urllib.request.Request(
                "https://api.kit.com/v4/tags?per_page=1",
                method="GET",
            )
            req.add_header("X-Kit-Api-Key", kit_key)
            req.add_header("Content-Type", "application/json")
            with urllib.request.urlopen(req, timeout=10) as resp:
                resp.read()
                latency_ms = int((time.time() - start) * 1000)
                results["kit"] = {"status": "ok", "latency_ms": latency_ms}
        except Exception as e:
            latency_ms = int((time.time() - start) * 1000)
            results["kit"] = {"status": "error", "error": str(e)[:200], "latency_ms": latency_ms}
    else:
        results["kit"] = {"status": "not_configured"}

    # Circle: test with a lightweight GET
    circle_token = os.getenv("CIRCLE_API_TOKEN", "")
    if circle_token:
        try:
            start = time.time()
            req = urllib.request.Request(
                "https://app.circle.so/api/admin/v2/community",
                method="GET",
            )
            req.add_header("Authorization", f"Bearer {circle_token}")
            req.add_header("Content-Type", "application/json")
            req.add_header("User-Agent", "EveryStudentDB/1.0")
            with urllib.request.urlopen(req, timeout=10) as resp:
                resp.read()
                latency_ms = int((time.time() - start) * 1000)
                results["circle"] = {"status": "ok", "latency_ms": latency_ms}
        except Exception as e:
            latency_ms = int((time.time() - start) * 1000)
            results["circle"] = {"status": "error", "error": str(e)[:200], "latency_ms": latency_ms}
    else:
        results["circle"] = {"status": "not_configured"}

    # Stripe: config check only (no outbound test)
    results["stripe"] = {
        "status": "configured" if os.getenv("STRIPE_WEBHOOK_SECRET", "") else "not_configured",
    }

    # Typeform: config check only
    results["typeform"] = {
        "status": "configured" if os.getenv("TYPEFORM_WEBHOOK_SECRET", "") else "not_configured",
    }

    return {"checked_at": datetime.utcnow().isoformat(), "services": results}


ADMIN_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Student DB — Admin</title>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
         background: #0f1117; color: #e0e0e0; padding: 2rem; }
  h1 { font-size: 1.4rem; color: #fff; margin-bottom: 0.5rem; }
  .subtitle { color: #888; font-size: 0.85rem; margin-bottom: 1rem; }
  .tabs { display: flex; gap: 0; border-bottom: 1px solid #2a2d37; margin-bottom: 1.5rem; }
  .tab-btn { padding: 0.6rem 1.2rem; border: none; border-bottom: 3px solid transparent;
             background: none; font-size: 0.85rem; font-weight: 500; color: #888;
             cursor: pointer; transition: color 0.15s, border-color 0.15s; }
  .tab-btn:hover { color: #ccc; }
  .tab-btn.active { color: #fff; border-bottom-color: #fff; }
  .tab-panel { display: none; }
  .tab-panel.active { display: block; }
  .stats { display: flex; gap: 1rem; margin-bottom: 2rem; flex-wrap: wrap; }
  .stat { background: #1a1d27; border: 1px solid #2a2d37; border-radius: 8px;
          padding: 1.2rem 1.5rem; min-width: 140px; }
  .stat-num { font-size: 1.8rem; font-weight: 700; color: #fff; }
  .stat-label { font-size: 0.75rem; color: #888; text-transform: uppercase;
                letter-spacing: 0.05em; margin-top: 0.25rem; }
  h2 { font-size: 1rem; color: #fff; margin: 1.5rem 0 0.75rem; }
  .flow { background: #1a1d27; border: 1px solid #2a2d37; border-radius: 8px;
          padding: 1.2rem; margin-bottom: 0.75rem; }
  .flow-header { display: flex; justify-content: space-between; align-items: center; }
  .flow-name { font-weight: 600; color: #fff; }
  .flow-type { font-size: 0.7rem; color: #888; text-transform: uppercase;
               letter-spacing: 0.05em; margin-right: 0.5rem; }
  .flow.onboarding { border-left: 3px solid #fbbf24; }
  .flow.deferred { border-left: 3px solid #a78bfa; }
  .flow-count { background: #2a2d37; padding: 0.2rem 0.6rem; border-radius: 12px;
                font-size: 0.8rem; color: #aaa; }
  .triggers { display: flex; gap: 0.5rem; margin-top: 0.6rem; flex-wrap: wrap; }
  .trigger { font-size: 0.75rem; padding: 0.25rem 0.6rem; border-radius: 4px;
             display: inline-flex; align-items: center; gap: 0.3rem; }
  .trigger.kit { background: #1e3a2f; color: #4ade80; border: 1px solid #2d5a43; }
  .trigger.stripe { background: #2a1e3a; color: #a78bfa; border: 1px solid #3d2d5a; }
  .trigger.form { background: #1e2a3a; color: #60a5fa; border: 1px solid #2d3d5a; }
  .trigger.typeform { background: #3a2e1e; color: #fbbf24; border: 1px solid #5a4a2d; }
  .url { font-family: monospace; font-size: 0.7rem; color: #666; margin-top: 0.4rem;
         word-break: break-all; }
  table { width: 100%; border-collapse: collapse; margin-top: 0.5rem; }
  th { text-align: left; font-size: 0.7rem; color: #666; text-transform: uppercase;
       letter-spacing: 0.05em; padding: 0.5rem 0.75rem; border-bottom: 1px solid #2a2d37; }
  td { padding: 0.5rem 0.75rem; font-size: 0.85rem; border-bottom: 1px solid #1a1d27; }
  .status { font-size: 0.75rem; padding: 0.15rem 0.5rem; border-radius: 4px;
            background: #1e3a2f; color: #4ade80; display: inline-block; }
  .loading { color: #666; padding: 2rem; text-align: center; }
  a { color: #60a5fa; text-decoration: none; }
  a:hover { text-decoration: underline; }
  /* System Health styles */
  .health-cards { display: grid; grid-template-columns: repeat(4, 1fr); gap: 0.75rem; margin-bottom: 1.5rem; }
  .health-card { background: #1a1d27; border: 1px solid #2a2d37; border-radius: 8px; padding: 1rem; }
  .health-card-hdr { display: flex; align-items: center; gap: 0.4rem; }
  .health-dot { width: 8px; height: 8px; border-radius: 50%; display: inline-block; }
  .health-dot.ok { background: #4ade80; }
  .health-dot.configured { background: #fbbf24; }
  .health-dot.not_configured { background: #555; }
  .health-dot.error { background: #ef4444; }
  .health-name { font-weight: 600; color: #fff; font-size: 0.9rem; flex: 1; }
  .health-latency { font-size: 0.75rem; color: #666; font-family: monospace; }
  .health-status-txt { font-size: 0.8rem; color: #aaa; margin-top: 0.3rem; }
  .health-error-txt { font-size: 0.75rem; color: #ef4444; margin-top: 0.25rem; word-break: break-all; }
  .alert-card { border-radius: 8px; padding: 0.8rem 1rem; margin-bottom: 0.5rem; }
  .alert-amber { background: #2d2215; border: 1px solid #5a4a2d; }
  .alert-red { background: #2d1215; border: 1px solid #5a2028; }
  .alert-title { font-weight: 600; font-size: 0.85rem; }
  .alert-amber .alert-title { color: #fbbf24; }
  .alert-red .alert-title { color: #ef4444; }
  .alert-detail { font-size: 0.8rem; color: #aaa; margin-top: 0.25rem; }
  .refresh-btn { padding: 0.4rem 1rem; font-size: 0.8rem; color: #ccc; background: transparent;
                 border: 1px solid #2a2d37; border-radius: 6px; cursor: pointer; margin-left: auto; }
  .refresh-btn:hover { border-color: #555; color: #fff; }
  .section-hdr { display: flex; align-items: center; gap: 0.5rem; }
  .no-errors { color: #4ade80; font-size: 0.85rem; padding: 0.5rem 0; }
  @media (max-width: 700px) { .health-cards { grid-template-columns: repeat(2, 1fr); } }
</style>
</head>
<body>
<h1>Every Student DB</h1>
<p class="subtitle">Admin Dashboard</p>

<div class="tabs">
  <button class="tab-btn active" onclick="showTab('flows')">Flows</button>
  <button class="tab-btn" onclick="showTab('health')">System Health</button>
</div>

<div id="tab-flows" class="tab-panel active"><div class="loading">Loading...</div></div>
<div id="tab-health" class="tab-panel"><div class="loading">Loading...</div></div>

<script>
function showTab(name) {
  document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
  document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
  event.target.classList.add('active');
  document.getElementById('tab-' + name).classList.add('active');
  if (name === 'health' && !window._healthLoaded) loadHealth();
}

async function load() {
  const res = await fetch('/api/admin/overview');
  const d = await res.json();
  const el = document.getElementById('tab-flows');

  const BASE = window.location.origin;

  let html = `
    <div class="stats">
      <div class="stat"><div class="stat-num">${d.total_products}</div><div class="stat-label">Products</div></div>
      <div class="stat"><div class="stat-num">${d.total_students}</div><div class="stat-label">Students</div></div>
      <div class="stat"><div class="stat-num">${d.total_enrollments}</div><div class="stat-label">Enrollments</div></div>
    </div>
    <h2>Active Flows</h2>
  `;

  for (const f of d.flows) {
    const triggers = f.triggers.map(t => {
      const cls = t.type.toLowerCase();
      return `<span class="trigger ${cls}">${t.type}: ${t.identifier}</span>`;
    }).join('');

    const urls = f.triggers.filter(t => t.type !== 'Form').map(t =>
      `<div class="url">${BASE}${t.url}</div>`
    ).join('');

    const flowClass = f.flow_type === 'Onboarding Form Complete' ? 'flow onboarding'
                     : f.flow_type === 'Deferred Opt-In' ? 'flow deferred' : 'flow';
    html += `
      <div class="${flowClass}">
        <div class="flow-header">
          <span class="flow-name">${f.product_name}</span>
          <div>
            <span class="flow-type">${f.flow_type}</span>
            <span class="flow-count">${f.enrollment_count} enrolled</span>
          </div>
        </div>
        <div class="triggers">${triggers}</div>
        ${urls}
      </div>
    `;
  }

  html += '<h2>Recent Enrollments</h2>';
  if (d.recent_enrollments.length === 0) {
    html += '<p style="color:#666;font-size:0.85rem">No enrollments yet.</p>';
  } else {
    html += `<table><thead><tr>
      <th>Student</th><th>Email</th><th>Product</th><th>Status</th>
    </tr></thead><tbody>`;
    for (const e of d.recent_enrollments) {
      html += `<tr>
        <td>${e.student_name}</td>
        <td style="color:#888">${e.student_email}</td>
        <td>${e.product}</td>
        <td><span class="status">${e.status || '\\u2014'}</span></td>
      </tr>`;
    }
    html += '</tbody></table>';
  }

  el.innerHTML = html;
}

async function loadHealth() {
  window._healthLoaded = true;
  const el = document.getElementById('tab-health');
  el.innerHTML = '<div class="loading">Loading health data...</div>';

  try {
    const [healthRes, statusRes] = await Promise.all([
      fetch('/api/admin/webhook-health'),
      fetch('/api/admin/api-status'),
    ]);
    const health = await healthRes.json();
    const apiStatus = await statusRes.json();
    renderHealth(el, health, apiStatus);
  } catch (e) {
    el.innerHTML = '<p style="color:#ef4444">Failed to load health data: ' + e.message + '</p>';
  }
}

function renderHealth(el, health, apiStatus) {
  const svc = apiStatus.services || {};
  let html = '<div class="section-hdr"><h2 style="margin:0">API Connections</h2>'
    + '<button class="refresh-btn" onclick="window._healthLoaded=false;loadHealth()">Refresh</button></div>';
  html += '<div class="health-cards">';
  for (const [name, data] of Object.entries(svc)) {
    const label = name.charAt(0).toUpperCase() + name.slice(1);
    html += `<div class="health-card">
      <div class="health-card-hdr">
        <span class="health-dot ${data.status}"></span>
        <span class="health-name">${label}</span>
        ${data.latency_ms != null ? '<span class="health-latency">' + data.latency_ms + 'ms</span>' : ''}
      </div>
      <div class="health-status-txt">${data.status}</div>
      ${data.error ? '<div class="health-error-txt">' + data.error + '</div>' : ''}
    </div>`;
  }
  html += '</div>';

  // Staleness alerts
  const alerts = health.staleness_alerts || [];
  if (alerts.length > 0) {
    html += '<h2>Staleness Alerts</h2>';
    for (const a of alerts) {
      const cls = a.severity === 'red' ? 'alert-red' : 'alert-amber';
      const lastSeen = a.last_seen ? new Date(a.last_seen).toLocaleString() : 'Never';
      html += `<div class="alert-card ${cls}">
        <div class="alert-title">${a.product} \\u2014 ${a.flow}</div>
        <div class="alert-detail">Last seen: ${lastSeen} | Expected every ${a.threshold_hours}h</div>
      </div>`;
    }
  }

  // Webhook activity table
  html += '<h2>Webhook Activity</h2>';
  html += `<table><thead><tr>
    <th>Endpoint</th><th style="text-align:right">24h Total</th>
    <th style="text-align:right">24h Errors</th><th style="text-align:right">7d Total</th>
    <th>Last Fired</th></tr></thead><tbody>`;
  const eps = health.endpoints || {};
  for (const [name, s] of Object.entries(eps)) {
    const c24 = s.counts_24h || {};
    const c7 = s.counts_7d || {};
    const t24 = Object.values(c24).reduce((a,b) => a+b, 0);
    const t7 = Object.values(c7).reduce((a,b) => a+b, 0);
    const e24 = c24.error || 0;
    const last = s.last_fired ? new Date(s.last_fired).toLocaleString() : 'Never';
    html += `<tr>
      <td><code>${name}</code></td>
      <td style="text-align:right">${t24}</td>
      <td style="text-align:right;${e24 > 0 ? 'color:#ef4444' : ''}">${e24}</td>
      <td style="text-align:right">${t7}</td>
      <td style="color:#aaa;font-size:0.8rem">${last}</td>
    </tr>`;
  }
  html += '</tbody></table>';

  // Downstream actions (7d)
  html += '<h2>Downstream Actions (7d)</h2>';
  html += `<table><thead><tr>
    <th>Endpoint</th><th style="text-align:right">Success Events</th>
    <th style="text-align:right">Kit Tagged</th><th style="text-align:right">Circle Invited</th>
    <th style="text-align:right">Circle AG</th><th style="text-align:right">Enrolled</th>
    </tr></thead><tbody>`;
  for (const [name, s] of Object.entries(eps)) {
    const d = s.downstream_7d || {};
    if (!d.total) continue;
    html += `<tr>
      <td><code>${name}</code></td>
      <td style="text-align:right">${d.total}</td>
      <td style="text-align:right">${d.kit_tagged || 0}</td>
      <td style="text-align:right">${d.circle_invited || 0}</td>
      <td style="text-align:right">${d.circle_access_group || 0}</td>
      <td style="text-align:right">${d.enrollment_created || 0}</td>
    </tr>`;
  }
  html += '</tbody></table>';

  // Recent errors
  html += '<h2>Recent Errors</h2>';
  const errors = health.recent_errors || [];
  if (errors.length === 0) {
    html += '<div class="no-errors">No recent errors</div>';
  } else {
    html += `<table><thead><tr>
      <th>Time</th><th>Endpoint</th><th>Product</th><th>Error</th>
      </tr></thead><tbody>`;
    for (const e of errors) {
      html += `<tr>
        <td style="color:#aaa;font-size:0.8rem">${new Date(e.timestamp).toLocaleString()}</td>
        <td><code>${e.endpoint}</code></td>
        <td>${e.product_id || '\\u2014'}</td>
        <td style="color:#ef4444;font-size:0.8rem;max-width:300px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${e.error_message}</td>
      </tr>`;
    }
    html += '</tbody></table>';
  }

  el.innerHTML = html;
}

load();
</script>
</body>
</html>"""


@router.get("/admin", response_class=HTMLResponse)
def admin_dashboard():
    return ADMIN_HTML
