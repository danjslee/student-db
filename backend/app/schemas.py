from typing import Optional, List, Dict
from datetime import date, datetime
from pydantic import BaseModel


# ---------- Product ----------

class ProductBase(BaseModel):
    product_id: str
    product_name: str
    kit_tag: Optional[str] = None


class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseModel):
    product_id: Optional[str] = None
    product_name: Optional[str] = None
    kit_tag: Optional[str] = None


class ProductRead(ProductBase):
    id: int
    enrollment_count: int = 0

    model_config = {"from_attributes": True}


# ---------- Enrollment (nested, minimal) ----------

class EnrollmentBrief(BaseModel):
    id: int
    enrollment_id: str
    status: Optional[str] = None

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
    country: Optional[str] = None
    closest_city: Optional[str] = None
    enrollment_count: int = 0

    model_config = {"from_attributes": True}


# ---------- Enrollment (full) ----------

class EnrollmentBase(BaseModel):
    enrollment_id: str
    status: Optional[str] = None
    student_id: int
    product_id: int


class EnrollmentCreate(EnrollmentBase):
    pass


class EnrollmentUpdate(BaseModel):
    status: Optional[str] = None
    student_id: Optional[int] = None
    product_id: Optional[int] = None


class EnrollmentRead(EnrollmentBase):
    id: int
    student: StudentBrief
    product: ProductBase

    model_config = {"from_attributes": True}


# ---------- Chat ----------

class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    answer: str
    sql: Optional[str] = None
    data: Optional[List[Dict]] = None


# ---------- Analytics ----------

class CountItem(BaseModel):
    label: str
    count: int


class TimelineItem(BaseModel):
    date: str
    count: int
