from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Enrollment, Product, Student

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/webhook", tags=["webhooks"])

KIT_WEBHOOK_SECRET = os.getenv("KIT_WEBHOOK_SECRET", "")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")
TYPEFORM_WEBHOOK_SECRET = os.getenv("TYPEFORM_WEBHOOK_SECRET", "")


# ---------------------------------------------------------------------------
# Shared: find-or-create student + create enrollment
# ---------------------------------------------------------------------------

def _find_or_create_student(
    db: Session,
    email: str,
    first_name: str = "Unknown",
    last_name: str = "",
) -> Student:
    """Find existing student by email, or create a new one."""
    clean_email = email.lower().strip()
    student = db.query(Student).filter(func.lower(Student.email) == clean_email).first()

    if not student:
        max_num = db.query(func.max(Student.student_number)).scalar() or 0
        student = Student(
            student_number=max_num + 1,
            first_name=first_name,
            last_name=last_name,
            email=clean_email,
        )
        db.add(student)
        db.flush()
        logger.info("Created student #%d: %s", student.student_number, clean_email)

    return student


def _create_enrollment(
    db: Session,
    student: Student,
    product: Product,
    status: str = "Paying Customer (Full-fee)",
) -> dict:
    """Create an enrollment (idempotent — returns existing if duplicate)."""
    enrollment_id = f"{student.email}_{product.product_id}"
    existing = db.query(Enrollment).filter(Enrollment.enrollment_id == enrollment_id).first()

    if existing:
        logger.info("Enrollment already exists: %s", enrollment_id)
        return {"status": "already_enrolled", "enrollment_id": enrollment_id}

    enrollment = Enrollment(
        enrollment_id=enrollment_id,
        status=status,
        student_id=student.id,
        product_id=product.id,
    )
    db.add(enrollment)
    db.commit()

    logger.info("Created enrollment: %s", enrollment_id)
    return {
        "status": "enrolled",
        "enrollment_id": enrollment_id,
        "student_id": student.id,
        "product_id": product.id,
    }


def _split_name(full_name: str) -> tuple:
    """Split a name string into (first, last)."""
    parts = full_name.strip().split(None, 1)
    first = parts[0] if parts else "Unknown"
    last = parts[1] if len(parts) > 1 else ""
    return first, last


# ---------------------------------------------------------------------------
# 1. Kit (ConvertKit) — subscriber.tag_add
# ---------------------------------------------------------------------------

class KitSubscriber(BaseModel):
    id: int
    first_name: Optional[str] = None
    email_address: str
    state: Optional[str] = None
    created_at: Optional[str] = None

    class Config:
        extra = "allow"


class KitWebhookPayload(BaseModel):
    subscriber: KitSubscriber


@router.post("/kit/{kit_tag}")
def kit_tag_added(kit_tag: str, payload: KitWebhookPayload, request: Request, db: Session = Depends(get_db)):
    """
    Kit webhook: subscriber added to tag.
    URL pattern: /api/webhook/kit/{kit_tag}
    """
    if KIT_WEBHOOK_SECRET:
        secret = request.headers.get("X-Kit-Webhook-Secret", "")
        if secret != KIT_WEBHOOK_SECRET:
            raise HTTPException(401, "Invalid webhook secret")

    sub = payload.subscriber
    logger.info("Kit webhook: tag=%s email=%s", kit_tag, sub.email_address)

    product = db.query(Product).filter(Product.kit_tag == kit_tag).first()
    if not product:
        raise HTTPException(404, f"No product with kit_tag '{kit_tag}'")

    first, last = _split_name(sub.first_name or "")
    student = _find_or_create_student(db, sub.email_address, first, last)
    return _create_enrollment(db, student, product)


# ---------------------------------------------------------------------------
# 2. Stripe — checkout.session.completed
# ---------------------------------------------------------------------------

@router.post("/stripe")
async def stripe_checkout(request: Request, db: Session = Depends(get_db)):
    """
    Stripe webhook: checkout.session.completed.
    Matches product via stripe_price_id on the Product record.
    """
    body = await request.body()

    # Verify Stripe signature
    if STRIPE_WEBHOOK_SECRET:
        sig_header = request.headers.get("Stripe-Signature", "")
        if not _verify_stripe_signature(body, sig_header, STRIPE_WEBHOOK_SECRET):
            raise HTTPException(401, "Invalid Stripe signature")

    event = json.loads(body)

    if event.get("type") != "checkout.session.completed":
        return {"status": "ignored", "event_type": event.get("type")}

    session = event["data"]["object"]
    email = session.get("customer_email") or session.get("customer_details", {}).get("email")
    name = session.get("customer_details", {}).get("name", "")

    if not email:
        raise HTTPException(400, "No customer email in checkout session")

    # Get the price ID from line items (Stripe includes it in the session)
    # For expanded sessions, line_items may be nested; we also check metadata
    price_id = session.get("metadata", {}).get("price_id")
    if not price_id:
        line_items = session.get("line_items", {}).get("data", [])
        if line_items:
            price_id = line_items[0].get("price", {}).get("id")

    # Also try to match by metadata product_id directly
    product = None
    meta_product_id = session.get("metadata", {}).get("product_id")
    if meta_product_id:
        product = db.query(Product).filter(Product.product_id == meta_product_id).first()

    if not product and price_id:
        product = db.query(Product).filter(Product.stripe_price_id == price_id).first()

    if not product:
        logger.warning("Stripe webhook: no matching product. price_id=%s metadata=%s", price_id, session.get("metadata"))
        raise HTTPException(404, "No matching product for this checkout session")

    logger.info("Stripe webhook: email=%s product=%s", email, product.product_id)
    first, last = _split_name(name)
    student = _find_or_create_student(db, email, first, last)
    return _create_enrollment(db, student, product)


def _verify_stripe_signature(payload: bytes, sig_header: str, secret: str) -> bool:
    """Verify Stripe webhook signature (v1)."""
    try:
        parts = dict(item.split("=", 1) for item in sig_header.split(","))
        timestamp = parts.get("t", "")
        signature = parts.get("v1", "")
        signed_payload = f"{timestamp}.".encode() + payload
        expected = hmac.new(secret.encode(), signed_payload, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, signature)
    except Exception:
        return False


# ---------------------------------------------------------------------------
# 3. Generic form — any form tool (Tally, Typeform, custom)
# ---------------------------------------------------------------------------

class FormWebhookPayload(BaseModel):
    email: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    name: Optional[str] = None  # full name fallback

    class Config:
        extra = "allow"


@router.post("/form/{product_id}")
def form_submission(product_id: str, payload: FormWebhookPayload, request: Request, db: Session = Depends(get_db)):
    """
    Generic form webhook.
    URL pattern: /api/webhook/form/{product_id}
    Accepts JSON with at minimum: email. Optionally: first_name, last_name, or name.
    """
    if KIT_WEBHOOK_SECRET:
        secret = request.headers.get("X-Webhook-Secret", "")
        if secret != KIT_WEBHOOK_SECRET:
            raise HTTPException(401, "Invalid webhook secret")

    product = db.query(Product).filter(Product.product_id == product_id).first()
    if not product:
        raise HTTPException(404, f"No product with product_id '{product_id}'")

    # Resolve name fields
    if payload.first_name:
        first = payload.first_name
        last = payload.last_name or ""
    elif payload.name:
        first, last = _split_name(payload.name)
    else:
        first, last = "Unknown", ""

    logger.info("Form webhook: product=%s email=%s", product_id, payload.email)
    student = _find_or_create_student(db, payload.email, first, last)
    return _create_enrollment(db, student, product)


# ---------------------------------------------------------------------------
# 4. Typeform — form_response submitted
# ---------------------------------------------------------------------------

# Student model fields that can be enriched via Typeform
_STUDENT_FIELDS = {
    "first_name", "last_name", "preferred_name", "email", "alternative_email",
    "country", "timezone", "closest_city", "dob", "gender",
    "learn_about_course", "consent_images", "consent_photo_on_site",
    "what_made_you_join", "get_from", "here_for",
}


def _extract_typeform_answer(answer: Dict[str, Any]) -> Any:
    """Extract the value from a Typeform answer based on its type."""
    atype = answer.get("type", "")
    if atype == "email":
        return answer.get("email")
    elif atype == "text":
        return answer.get("text")
    elif atype == "choice":
        return answer.get("choice", {}).get("label")
    elif atype == "choices":
        labels = answer.get("choices", {}).get("labels", [])
        return ", ".join(labels) if labels else None
    elif atype == "boolean":
        return answer.get("boolean")
    elif atype == "date":
        return answer.get("date")
    elif atype == "number":
        return answer.get("number")
    elif atype == "phone_number":
        return answer.get("phone_number")
    elif atype == "url":
        return answer.get("url")
    elif atype == "file_url":
        return answer.get("file_url")
    else:
        # Fallback: try common keys
        for key in ("text", "email", "number", "boolean", "date", "choice", "url"):
            if key in answer:
                val = answer[key]
                if isinstance(val, dict):
                    return val.get("label", str(val))
                return val
        return None


def _parse_typeform_answers(
    form_response: Dict[str, Any],
    field_map: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """
    Parse Typeform form_response.answers into a flat dict of student fields.

    Mapping priority:
    1. Explicit field_map: {typeform_field_ref: student_field_name}
    2. Convention: field ref matches student column name
    3. Special: 'name'/'full_name' ref → split into first_name/last_name
    """
    answers = form_response.get("answers", [])
    result: Dict[str, Any] = {}

    for answer in answers:
        field_ref = answer.get("field", {}).get("ref", "")
        value = _extract_typeform_answer(answer)
        if value is None:
            continue

        # 1. Explicit mapping
        if field_map and field_ref in field_map:
            target = field_map[field_ref]
            if target in ("name", "full_name"):
                first, last = _split_name(str(value))
                result["first_name"] = first
                result["last_name"] = last
            else:
                result[target] = value
            continue

        # 2. Convention: ref matches student field
        if field_ref in _STUDENT_FIELDS:
            result[field_ref] = value
            continue

        # Check field type for email (auto-detect email field)
        if answer.get("type") == "email" and "email" not in result:
            result["email"] = value
            continue

        # 3. Special: name/full_name convention
        if field_ref in ("name", "full_name"):
            first, last = _split_name(str(value))
            result["first_name"] = first
            result["last_name"] = last

    return result


def _verify_typeform_signature(payload: bytes, sig_header: str, secret: str) -> bool:
    """Verify Typeform webhook signature (HMAC-SHA256, base64 encoded)."""
    try:
        expected = base64.b64encode(
            hmac.new(secret.encode(), payload, hashlib.sha256).digest()
        ).decode()
        return hmac.compare_digest(f"sha256={expected}", sig_header)
    except Exception:
        return False


@router.post("/typeform/{product_id}")
async def typeform_submission(
    product_id: str, request: Request, db: Session = Depends(get_db),
):
    """
    Typeform webhook: form_response submitted.
    URL pattern: /api/webhook/typeform/{product_id}

    Parses Typeform's nested answer structure, enriches the student record,
    and creates/confirms enrollment.
    """
    body = await request.body()

    # Verify signature if secret is configured
    if TYPEFORM_WEBHOOK_SECRET:
        sig_header = request.headers.get("Typeform-Signature", "")
        if not _verify_typeform_signature(body, sig_header, TYPEFORM_WEBHOOK_SECRET):
            raise HTTPException(401, "Invalid Typeform signature")

    payload = json.loads(body)

    # Validate event type
    event_type = payload.get("event_type")
    if event_type != "form_response":
        return {"status": "ignored", "event_type": event_type}

    form_response = payload.get("form_response", {})

    # Look up product
    product = db.query(Product).filter(Product.product_id == product_id).first()
    if not product:
        raise HTTPException(404, f"No product with product_id '{product_id}'")

    # Optionally validate form_id
    form_id = form_response.get("form_id")
    if product.typeform_form_id and form_id != product.typeform_form_id:
        raise HTTPException(
            400,
            f"Form ID mismatch: expected {product.typeform_form_id}, got {form_id}",
        )

    # Parse field map from product config
    field_map = None
    if product.typeform_field_map:
        try:
            field_map = json.loads(product.typeform_field_map)
        except json.JSONDecodeError:
            logger.warning("Invalid typeform_field_map JSON for product %s", product_id)

    # Extract student data from answers
    parsed = _parse_typeform_answers(form_response, field_map)

    email = parsed.pop("email", None)
    if not email:
        raise HTTPException(400, "No email found in Typeform response")

    first_name = parsed.pop("first_name", "Unknown")
    last_name = parsed.pop("last_name", "")

    logger.info("Typeform webhook: product=%s email=%s fields=%s", product_id, email, list(parsed.keys()))

    # Find or create student
    student = _find_or_create_student(db, email, first_name, last_name)

    # Enrich student with additional fields from the form
    updated_fields = []
    for field, value in parsed.items():
        if field in _STUDENT_FIELDS and field not in ("email", "first_name", "last_name"):
            if value is not None:
                setattr(student, field, value)
                updated_fields.append(field)

    # Set onboarding_date from Typeform's submitted_at
    submitted_at = form_response.get("submitted_at")
    if submitted_at:
        try:
            student.onboarding_date = datetime.fromisoformat(
                submitted_at.replace("Z", "+00:00")
            )
            updated_fields.append("onboarding_date")
        except (ValueError, TypeError):
            pass

    if updated_fields:
        db.flush()
        logger.info("Enriched student #%d with: %s", student.student_number, updated_fields)

    # Create enrollment (idempotent)
    result = _create_enrollment(db, student, product)
    result["enriched_fields"] = updated_fields
    return result
