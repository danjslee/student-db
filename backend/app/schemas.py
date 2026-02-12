from typing import Optional, List, Dict
from datetime import date, datetime
from pydantic import BaseModel


# ---------- Product ----------

class ProductBase(BaseModel):
    product_id: str
    product_name: str
    kit_tag: Optional[str] = None
    stripe_price_id: Optional[str] = None
    typeform_form_id: Optional[str] = None
    typeform_field_map: Optional[str] = None


class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseModel):
    product_id: Optional[str] = None
    product_name: Optional[str] = None
    kit_tag: Optional[str] = None
    stripe_price_id: Optional[str] = None
    typeform_form_id: Optional[str] = None
    typeform_field_map: Optional[str] = None


class ProductRead(ProductBase):
    id: int
    enrollment_count: int = 0

    model_config = {"from_attributes": True}


# ---------- Enrollment (nested, minimal) ----------

class EnrollmentBrief(BaseModel):
    id: int
    enrollment_id: str
    status: Optional[str] = None
    sale_id: Optional[int] = None

    model_config = {"from_attributes": True}


class EnrollmentWithProduct(EnrollmentBrief):
    product: ProductBase


class EnrollmentWithStudent(EnrollmentBrief):
    student: "StudentBrief"


# ---------- Student ----------

class StudentBase(BaseModel):
    first_name: str
    last_name: str
    preferred_name: Optional[str] = None
    email: str
    alternative_email: Optional[str] = None
    country: Optional[str] = None
    timezone: Optional[str] = None
    closest_city: Optional[str] = None
    dob: Optional[date] = None
    gender: Optional[str] = None
    learn_about_course: Optional[str] = None
    consent_images: Optional[bool] = None
    consent_photo_on_site: Optional[bool] = None
    what_made_you_join: Optional[str] = None
    get_from: Optional[str] = None
    here_for: Optional[str] = None
    claude_confidence_level: Optional[float] = None
    onboarding_date: Optional[datetime] = None


class StudentCreate(StudentBase):
    student_number: int


class StudentUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    preferred_name: Optional[str] = None
    email: Optional[str] = None
    alternative_email: Optional[str] = None
    country: Optional[str] = None
    timezone: Optional[str] = None
    closest_city: Optional[str] = None
    dob: Optional[date] = None
    gender: Optional[str] = None
    learn_about_course: Optional[str] = None
    consent_images: Optional[bool] = None
    consent_photo_on_site: Optional[bool] = None
    what_made_you_join: Optional[str] = None
    get_from: Optional[str] = None
    here_for: Optional[str] = None
    claude_confidence_level: Optional[float] = None
    onboarding_date: Optional[datetime] = None


class StudentBrief(BaseModel):
    id: int
    student_number: int
    first_name: str
    last_name: str
    email: str

    model_config = {"from_attributes": True}


class StudentRead(StudentBase):
    id: int
    student_number: int
    enrollments: List[EnrollmentWithProduct] = []

    model_config = {"from_attributes": True}


class StudentList(StudentBrief):
    preferred_name: Optional[str] = None
    alternative_email: Optional[str] = None
    country: Optional[str] = None
    timezone: Optional[str] = None
    closest_city: Optional[str] = None
    dob: Optional[date] = None
    gender: Optional[str] = None
    learn_about_course: Optional[str] = None
    consent_images: Optional[bool] = None
    consent_photo_on_site: Optional[bool] = None
    what_made_you_join: Optional[str] = None
    get_from: Optional[str] = None
    here_for: Optional[str] = None
    claude_confidence_level: Optional[float] = None
    onboarding_date: Optional[datetime] = None
    enrollment_count: int = 0

    model_config = {"from_attributes": True}


# ---------- Enrollment (full) ----------

class EnrollmentBase(BaseModel):
    enrollment_id: str
    status: Optional[str] = None
    student_id: int
    product_id: int
    sale_id: Optional[int] = None
    # Survey fields
    response_hash: Optional[str] = None
    biggest_win: Optional[str] = None
    three_things_learned: Optional[str] = None
    confidence_after: Optional[int] = None
    satisfaction: Optional[str] = None
    recommend_score: Optional[int] = None
    testimonial: Optional[str] = None
    improvement_suggestion: Optional[str] = None
    interest_longer_program: Optional[str] = None
    followup_topics: Optional[str] = None
    beginner_friendly_rating: Optional[str] = None
    expected_learning_not_covered: Optional[str] = None
    anything_else: Optional[str] = None
    survey_response_type: Optional[str] = None
    survey_start_date: Optional[datetime] = None
    survey_stage_date: Optional[datetime] = None
    survey_submit_date: Optional[datetime] = None
    survey_network_id: Optional[str] = None
    survey_tags: Optional[str] = None
    transformational_score: Optional[int] = None
    delivered_on_promise_score: Optional[int] = None


class EnrollmentCreate(EnrollmentBase):
    pass


class EnrollmentUpdate(BaseModel):
    status: Optional[str] = None
    student_id: Optional[int] = None
    product_id: Optional[int] = None
    sale_id: Optional[int] = None
    # Survey fields
    biggest_win: Optional[str] = None
    three_things_learned: Optional[str] = None
    confidence_after: Optional[int] = None
    satisfaction: Optional[str] = None
    recommend_score: Optional[int] = None
    testimonial: Optional[str] = None
    improvement_suggestion: Optional[str] = None
    interest_longer_program: Optional[str] = None
    followup_topics: Optional[str] = None
    beginner_friendly_rating: Optional[str] = None
    expected_learning_not_covered: Optional[str] = None
    anything_else: Optional[str] = None
    transformational_score: Optional[int] = None
    delivered_on_promise_score: Optional[int] = None


class EnrollmentRead(EnrollmentBase):
    id: int
    student: StudentBrief
    product: ProductBase

    model_config = {"from_attributes": True}


# ---------- Chat ----------

class ChatMessage(BaseModel):
    role: str          # "user" or "assistant"
    content: str

class ChatRequest(BaseModel):
    messages: List[ChatMessage]

class ChatResponse(BaseModel):
    answer: str


# ---------- Analytics ----------

class CountItem(BaseModel):
    label: str
    count: int


class TimelineItem(BaseModel):
    date: str
    count: int


# ---------- Sale ----------

class SaleBrief(BaseModel):
    id: int
    sale_id: str
    buyer_email: str
    amount_cents: int
    status: str

    model_config = {"from_attributes": True}


class SaleBase(BaseModel):
    sale_id: str
    buyer_email: str
    buyer_name: Optional[str] = None
    product_id: int
    amount_cents: int
    currency: str = "USD"
    quantity: int = 1
    status: str = "completed"
    scholarship: int = 0
    source: Optional[str] = None
    stripe_checkout_session_id: Optional[str] = None
    stripe_payment_intent_id: Optional[str] = None
    purchase_date: Optional[datetime] = None
    notes: Optional[str] = None


class SaleCreate(SaleBase):
    pass


class SaleUpdate(BaseModel):
    buyer_email: Optional[str] = None
    buyer_name: Optional[str] = None
    amount_cents: Optional[int] = None
    currency: Optional[str] = None
    quantity: Optional[int] = None
    status: Optional[str] = None
    scholarship: Optional[int] = None
    source: Optional[str] = None
    notes: Optional[str] = None
    purchase_date: Optional[datetime] = None


class SaleRead(SaleBase):
    id: int
    product: ProductBase

    model_config = {"from_attributes": True}


class SaleList(SaleBase):
    id: int
    product_name: str = ""

    model_config = {"from_attributes": True}


class SaleCSVImportResult(BaseModel):
    created: int
    skipped: int
    linked: int
    errors: List[str] = []


