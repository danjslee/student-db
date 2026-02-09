from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy import func, desc
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Product, Student, Enrollment

router = APIRouter(tags=["admin"])


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

    return {
        "total_students": total_students,
        "total_enrollments": total_enrollments,
        "total_products": len(flows),
        "flows": flows,
        "archived_flows": archived_flows,
        "recent_enrollments": recent_list,
    }


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
  .subtitle { color: #888; font-size: 0.85rem; margin-bottom: 2rem; }
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
</style>
</head>
<body>
<h1>Every Student DB</h1>
<p class="subtitle">Enrollment flows & webhook status</p>

<div id="app"><div class="loading">Loading...</div></div>

<script>
async function load() {
  const res = await fetch('/api/admin/overview');
  const d = await res.json();
  const app = document.getElementById('app');

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

    const flowClass = f.flow_type === 'Onboarding Form Complete' ? 'flow onboarding' : 'flow';
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
        <td><span class="status">${e.status || '—'}</span></td>
      </tr>`;
    }
    html += '</tbody></table>';
  }

  app.innerHTML = html;
}
load();
</script>
</body>
</html>"""


@router.get("/admin", response_class=HTMLResponse)
def admin_dashboard():
    return ADMIN_HTML
