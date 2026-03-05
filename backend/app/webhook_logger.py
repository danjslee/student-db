"""Webhook event logger — records every webhook invocation for monitoring."""
from __future__ import annotations

import json
import logging
import time
from datetime import datetime
from typing import Optional

from app.database import SessionLocal
from app.models import WebhookEvent

logger = logging.getLogger(__name__)


class WebhookLog:
    """Accumulates webhook event data and saves to DB at the end."""

    def __init__(self, endpoint: str, product_id: Optional[str] = None):
        self._start = time.time()
        self.endpoint = endpoint
        self.product_id = product_id
        self.email = None  # type: Optional[str]
        self.status = "success"
        self.error_message = None  # type: Optional[str]

        # Downstream flags
        self.kit_tagged = False
        self.circle_invited = False
        self.circle_access_group_added = False
        self.enrollment_created = False
        self.student_created = False

        self._response = None  # type: Optional[dict]

    def set_error(self, msg: str):
        self.status = "error"
        self.error_message = str(msg)[:2000]

    def set_ignored(self):
        self.status = "ignored"

    def set_response(self, resp: dict):
        self._response = resp
        # Auto-detect downstream results from response dict
        if resp.get("status") == "enrolled":
            self.enrollment_created = True
        if resp.get("kit_rsvp_tagged"):
            self.kit_tagged = True
        if resp.get("kit_tagged"):
            self.kit_tagged = True
        if resp.get("kit_offboarded_tagged"):
            self.kit_tagged = True
        if resp.get("circle_invited"):
            self.circle_invited = True
        if resp.get("circle_access_group_added"):
            self.circle_access_group_added = True
        if resp.get("circle_onboarded"):
            self.circle_access_group_added = True
        if resp.get("circle_offboarded"):
            self.circle_access_group_added = True

    def save(self):
        """Persist the event to DB. Uses its own session so it never breaks the webhook."""
        try:
            duration_ms = int((time.time() - self._start) * 1000)
            response_summary = None
            if self._response:
                response_summary = json.dumps(self._response, default=str)[:2000]

            event = WebhookEvent(
                timestamp=datetime.utcnow(),
                endpoint=self.endpoint,
                product_id=self.product_id,
                email=self.email,
                status=self.status,
                error_message=self.error_message,
                duration_ms=duration_ms,
                kit_tagged=self.kit_tagged,
                circle_invited=self.circle_invited,
                circle_access_group_added=self.circle_access_group_added,
                enrollment_created=self.enrollment_created,
                student_created=self.student_created,
                response_summary=response_summary,
            )

            db = SessionLocal()
            try:
                db.add(event)
                db.commit()
            finally:
                db.close()
        except Exception:
            logger.exception("Failed to save webhook event log")
