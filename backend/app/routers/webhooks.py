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
from app.models import Enrollment, Product, Sale, ScholarshipApplication, Student

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/webhook", tags=["webhooks"])

KIT_WEBHOOK_SECRET = os.getenv("KIT_WEBHOOK_SECRET", "")
KIT_API_KEY = os.getenv("KIT_API_KEY", "")
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
    source: str = None,
    sale_id: int = None,
) -> dict:
    """Create an enrollment (idempotent — returns existing if duplicate)."""
    enrollment_id = f"{student.email}_{product.product_id}"
    existing = db.query(Enrollment).filter(Enrollment.enrollment_id == enrollment_id).first()

    if existing:
        # Link sale if not already linked
        if sale_id and not existing.sale_id:
            existing.sale_id = sale_id
            db.commit()
        logger.info("Enrollment already exists: %s", enrollment_id)
        return {"status": "already_enrolled", "enrollment_id": enrollment_id}

    enrollment = Enrollment(
        enrollment_id=enrollment_id,
        status=status,
        source=source,
        student_id=student.id,
        product_id=product.id,
        sale_id=sale_id,
    )
    db.add(enrollment)
    db.commit()

    logger.info("Created enrollment: %s", enrollment_id)

    # Tag subscriber with RSVP tag in Kit if configured
    kit_rsvp_tagged = False
    if product.kit_rsvp_tag:
        kit_rsvp_tagged = kit_tag_subscriber_by_email(student.email, product.kit_rsvp_tag)

    result = {
        "status": "enrolled",
        "enrollment_id": enrollment_id,
        "student_id": student.id,
        "product_id": product.id,
    }
    if product.kit_rsvp_tag:
        result["kit_rsvp_tagged"] = kit_rsvp_tagged
    return result


def _split_name(full_name: str) -> tuple:
    """Split a name string into (first, last)."""
    parts = full_name.strip().split(None, 1)
    first = parts[0] if parts else "Unknown"
    last = parts[1] if len(parts) > 1 else ""
    return first, last


# ---------------------------------------------------------------------------
# Kit API helpers — outbound calls to tag subscribers
# ---------------------------------------------------------------------------

import urllib.request
import urllib.error

_KIT_API_BASE = "https://api.kit.com/v4"


def _kit_api_request(method: str, path: str, body: dict = None) -> Optional[dict]:
    """Make an authenticated request to Kit API v4. Returns parsed JSON or None on failure."""
    if not KIT_API_KEY:
        logger.warning("KIT_API_KEY not set — skipping Kit API call")
        return None
    url = f"{_KIT_API_BASE}{path}"
    data = json.dumps(body).encode() if body else b"{}"
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    req.add_header("X-Kit-Api-Key", KIT_API_KEY)
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        logger.error("Kit API %s %s → %d: %s", method, path, e.code, e.read().decode()[:200])
        return None
    except Exception as e:
        logger.error("Kit API %s %s failed: %s", method, path, e)
        return None


def _kit_find_or_create_tag(tag_name: str) -> Optional[int]:
    """Create a tag in Kit (idempotent — returns existing if name matches). Returns tag ID."""
    result = _kit_api_request("POST", "/tags", {"name": tag_name})
    if result and "tag" in result:
        return result["tag"]["id"]
    return None


def _kit_find_subscriber_by_email(email: str) -> Optional[int]:
    """Find a Kit subscriber by email. Returns subscriber ID or None."""
    clean = email.lower().strip()
    encoded = urllib.request.quote(clean)
    result = _kit_api_request("GET", f"/subscribers?email_address={encoded}")
    if result and result.get("subscribers"):
        return result["subscribers"][0]["id"]
    return None


def _kit_tag_subscriber(tag_id: int, subscriber_id: int) -> bool:
    """Add a tag to a subscriber. Returns True on success."""
    result = _kit_api_request("POST", f"/tags/{tag_id}/subscribers/{subscriber_id}")
    return result is not None


def kit_tag_subscriber_by_email(email: str, tag_name: str) -> bool:
    """
    High-level: find subscriber by email, find/create tag, apply tag.
    Returns True if successful, False otherwise. Non-blocking on failure.
    """
    subscriber_id = _kit_find_subscriber_by_email(email)
    if not subscriber_id:
        logger.warning("Kit: subscriber not found for %s — skipping tag '%s'", email, tag_name)
        return False
    tag_id = _kit_find_or_create_tag(tag_name)
    if not tag_id:
        logger.error("Kit: failed to find/create tag '%s'", tag_name)
        return False
    success = _kit_tag_subscriber(tag_id, subscriber_id)
    if success:
        logger.info("Kit: tagged %s with '%s'", email, tag_name)
    return success


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
    return _create_enrollment(db, student, product, source="kit")


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

    # Create Sale from Stripe checkout data
    session_id = session.get("id", "")
    sale_id_str = f"stripe_{session_id}"
    existing_sale = db.query(Sale).filter(Sale.sale_id == sale_id_str).first()
    sale = existing_sale
    if not existing_sale:
        amount_total = session.get("amount_total") or 0
        currency = (session.get("currency") or "usd").upper()
        payment_intent = session.get("payment_intent")
        sale = Sale(
            sale_id=sale_id_str,
            buyer_email=email.lower().strip(),
            buyer_name=name or None,
            product_id=product.id,
            amount_cents=amount_total,
            currency=currency,
            quantity=1,
            status="completed",
            source="stripe",
            stripe_checkout_session_id=session_id,
            stripe_payment_intent_id=payment_intent if isinstance(payment_intent, str) else None,
            purchase_date=datetime.utcnow(),
        )
        db.add(sale)
        db.flush()

    # Auto-match scholarship: if accepted scholarship exists for this email+product, flag the sale
    clean_buyer_email = email.lower().strip()
    scholarship_app = (
        db.query(ScholarshipApplication)
        .filter(
            func.lower(ScholarshipApplication.email) == clean_buyer_email,
            ScholarshipApplication.product_id == product.id,
            ScholarshipApplication.status == "accepted",
        )
        .first()
    )
    if scholarship_app:
        sale.scholarship = 1
        scholarship_app.enrolled = True
        db.commit()
        logger.info("Scholarship auto-matched: sale=%s app=#%d", sale.sale_id, scholarship_app.id)

    return _create_enrollment(db, student, product, source="stripe", sale_id=sale.id)


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
    return _create_enrollment(db, student, product, source="form")


# ---------------------------------------------------------------------------
# 4. Typeform — form_response submitted
# ---------------------------------------------------------------------------

# Enrollment survey fields that can be populated from a completion survey
_ENROLLMENT_SURVEY_FIELDS = {
    "biggest_win", "three_things_learned", "confidence_after", "satisfaction",
    "recommend_score", "testimonial", "improvement_suggestion",
    "interest_longer_program", "followup_topics", "beginner_friendly_rating",
    "expected_learning_not_covered", "anything_else",
    "transformational_score", "delivered_on_promise_score",
}

# Student model fields that can be enriched via Typeform
_STUDENT_FIELDS = {
    "first_name", "last_name", "preferred_name", "email", "alternative_email",
    "country", "timezone", "closest_city", "dob", "gender",
    "learn_about_course", "consent_images", "consent_photo_on_site",
    "what_made_you_join", "get_from", "here_for", "claude_confidence_level",
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
    elif atype in ("number", "opinion_scale"):
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
            if value is None:
                continue
            # Type coercions for SQLAlchemy column types
            if field == "dob" and isinstance(value, str):
                from datetime import date as date_type
                try:
                    value = date_type.fromisoformat(value)
                except (ValueError, TypeError):
                    continue
            if field == "claude_confidence_level" and not isinstance(value, (int, float)):
                try:
                    value = float(value)
                except (ValueError, TypeError):
                    continue
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
        db.commit()
        logger.info("Enriched student #%d with: %s", student.student_number, updated_fields)

    # Tag subscriber in Kit if product has an onboarded tag configured
    kit_tagged = False
    if product.kit_onboarded_tag:
        kit_tagged = kit_tag_subscriber_by_email(email, product.kit_onboarded_tag)

    # Create enrollment as safety net (idempotent — normally student is already enrolled)
    result = _create_enrollment(db, student, product, source="typeform")
    result["enriched_fields"] = updated_fields
    if product.kit_onboarded_tag:
        result["kit_tagged"] = kit_tagged
    return result


# ---------------------------------------------------------------------------
# 5. Typeform completion survey — updates enrollment with survey responses
# ---------------------------------------------------------------------------

def _parse_completion_answers(
    form_response: Dict[str, Any],
    field_map: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """
    Parse Typeform completion survey answers into enrollment survey fields.

    Mapping priority:
    1. Explicit field_map: {typeform_field_ref: enrollment_field_name}
    2. Convention: field ref matches enrollment survey column name
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
            result[target] = value
            continue

        # 2. Convention: ref matches enrollment survey field
        if field_ref in _ENROLLMENT_SURVEY_FIELDS:
            result[field_ref] = value
            continue

        # 3. Auto-detect email field
        if answer.get("type") == "email" and "email" not in result:
            result["email"] = value

    return result


@router.post("/typeform/{product_id}/completion")
async def typeform_completion_survey(
    product_id: str, request: Request, db: Session = Depends(get_db),
):
    """
    Typeform completion survey webhook.
    URL pattern: /api/webhook/typeform/{product_id}/completion

    Finds the student's enrollment and populates survey response fields.
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
    if product.completion_survey_form_id and form_id != product.completion_survey_form_id:
        raise HTTPException(
            400,
            f"Form ID mismatch: expected {product.completion_survey_form_id}, got {form_id}",
        )

    # Parse field map from product config
    field_map = None
    if product.completion_survey_field_map:
        try:
            field_map = json.loads(product.completion_survey_field_map)
        except json.JSONDecodeError:
            logger.warning("Invalid completion_survey_field_map JSON for product %s", product_id)

    # Extract survey data from answers
    parsed = _parse_completion_answers(form_response, field_map)

    email = parsed.pop("email", None)
    if not email:
        raise HTTPException(400, "No email found in completion survey response")

    clean_email = email.lower().strip()
    logger.info("Completion survey: product=%s email=%s fields=%s", product_id, clean_email, list(parsed.keys()))

    # Find the student
    student = db.query(Student).filter(func.lower(Student.email) == clean_email).first()
    if not student:
        raise HTTPException(404, f"No student found with email '{clean_email}'")

    # Find the enrollment
    enrollment = (
        db.query(Enrollment)
        .filter(Enrollment.student_id == student.id, Enrollment.product_id == product.id)
        .first()
    )
    if not enrollment:
        raise HTTPException(404, f"No enrollment found for student '{clean_email}' in product '{product_id}'")

    # Update enrollment with survey fields
    updated_fields = []
    for field, value in parsed.items():
        if field in _ENROLLMENT_SURVEY_FIELDS:
            # Type coercions for integer fields
            if field in ("confidence_after", "recommend_score", "transformational_score", "delivered_on_promise_score"):
                try:
                    value = int(value)
                except (ValueError, TypeError):
                    continue
            setattr(enrollment, field, value)
            updated_fields.append(field)

    # Set survey metadata
    enrollment.survey_response_type = "completion"
    submitted_at = form_response.get("submitted_at")
    if submitted_at:
        try:
            enrollment.survey_submit_date = datetime.fromisoformat(
                submitted_at.replace("Z", "+00:00")
            )
        except (ValueError, TypeError):
            pass

    db.commit()
    logger.info("Completion survey saved for enrollment %s: %s", enrollment.enrollment_id, updated_fields)

    return {
        "status": "survey_saved",
        "enrollment_id": enrollment.enrollment_id,
        "updated_fields": updated_fields,
    }


# ---------------------------------------------------------------------------
# 6. Scholarship application — shared Typeform (not per-product)
# ---------------------------------------------------------------------------

# Hardcoded Typeform field IDs for the scholarship form (BlmrafcZ)
_SCHOLARSHIP_FIELD_MAP = {
    "BDW3qHqGK2jN": "contact_info",
    "tL7F7QZoBHNt": "is_subscriber",
    "AKZmKw95FZnv": "course_name",
    "qkEtJzfrekMw": "amount_willing_to_pay",
    "tSu0EbTN0f3n": "circumstances",
    "cr4NgV8ICSTY": "hopes",
    "G18vXstzfsDw": "best_case_impact",
}


def _fuzzy_match_product(course_name: str, db: Session) -> Optional[Product]:
    """Match a course dropdown label to a Product. Tries exact, then substring."""
    if not course_name:
        return None
    clean = course_name.strip().lower()
    # Try exact match on product_name
    product = db.query(Product).filter(func.lower(Product.product_name) == clean).first()
    if product:
        return product
    # Try substring match
    for p in db.query(Product).all():
        if clean in p.product_name.lower() or p.product_name.lower() in clean:
            return p
    return None


@router.post("/typeform/scholarship")
async def typeform_scholarship(request: Request, db: Session = Depends(get_db)):
    """
    Scholarship application webhook (shared form, not per-product).
    URL: /api/webhook/typeform/scholarship
    """
    body = await request.body()

    if TYPEFORM_WEBHOOK_SECRET:
        sig_header = request.headers.get("Typeform-Signature", "")
        if not _verify_typeform_signature(body, sig_header, TYPEFORM_WEBHOOK_SECRET):
            raise HTTPException(401, "Invalid Typeform signature")

    payload = json.loads(body)

    event_type = payload.get("event_type")
    if event_type != "form_response":
        return {"status": "ignored", "event_type": event_type}

    form_response = payload.get("form_response", {})
    answers = form_response.get("answers", [])

    # Parse scholarship-specific fields
    parsed = {}  # type: Dict[str, Any]
    for answer in answers:
        field_id = answer.get("field", {}).get("id", "")
        mapped = _SCHOLARSHIP_FIELD_MAP.get(field_id)
        if not mapped:
            continue

        if mapped == "contact_info":
            # Nested contact_info — extract from the answer's sub-fields
            # Typeform contact_info has: first_name, last_name, email as direct keys
            ci = answer.get("contact_info") or answer.get("contacts") or {}
            parsed["first_name"] = ci.get("first_name", "")
            parsed["last_name"] = ci.get("last_name", "")
            parsed["email"] = ci.get("email", "")
        elif mapped == "is_subscriber":
            parsed["is_subscriber"] = answer.get("boolean", False)
        elif mapped == "course_name":
            parsed["course_name"] = _extract_typeform_answer(answer)
        else:
            parsed[mapped] = _extract_typeform_answer(answer)

    email = (parsed.get("email") or "").lower().strip()
    if not email:
        raise HTTPException(400, "No email found in scholarship application")

    # Resolve course → product
    product = _fuzzy_match_product(parsed.get("course_name", ""), db)

    # Get submitted_at
    submitted_at = form_response.get("submitted_at")
    applied_at = None
    if submitted_at:
        try:
            applied_at = datetime.fromisoformat(submitted_at.replace("Z", "+00:00"))
        except (ValueError, TypeError):
            applied_at = datetime.utcnow()

    app = ScholarshipApplication(
        email=email,
        first_name=parsed.get("first_name", ""),
        last_name=parsed.get("last_name", ""),
        product_id=product.id if product else None,
        is_subscriber=parsed.get("is_subscriber"),
        amount_willing_to_pay=parsed.get("amount_willing_to_pay"),
        circumstances=parsed.get("circumstances"),
        hopes=parsed.get("hopes"),
        best_case_impact=parsed.get("best_case_impact"),
        status="pending",
        applied_at=applied_at or datetime.utcnow(),
    )
    db.add(app)
    db.commit()

    logger.info(
        "Scholarship application #%d from %s for %s",
        app.id, email, product.product_name if product else "unknown course",
    )
    return {
        "status": "application_received",
        "id": app.id,
        "email": email,
        "product": product.product_name if product else None,
    }
