from sqlalchemy import (
    Column, Integer, String, Float, Boolean, Date, DateTime, Text,
    ForeignKey,
)
from sqlalchemy.orm import relationship
from app.database import Base


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(String, unique=True, nullable=False)
    product_name = Column(String, nullable=False)
    kit_tag = Column(String, nullable=True)
    stripe_price_id = Column(String, nullable=True)
    typeform_form_id = Column(String, nullable=True)
    typeform_field_map = Column(Text, nullable=True)

    enrollments = relationship("Enrollment", back_populates="product")
    sales = relationship("Sale", back_populates="product")


class Student(Base):
    __tablename__ = "students"

    id = Column(Integer, primary_key=True, index=True)
    student_number = Column(Integer, unique=True, nullable=False)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    preferred_name = Column(String, nullable=True)
    email = Column(String, unique=True, nullable=False)
    alternative_email = Column(String, nullable=True)
    country = Column(String, nullable=True)
    timezone = Column(String, nullable=True)
    closest_city = Column(String, nullable=True)
    dob = Column(Date, nullable=True)
    gender = Column(String, nullable=True)
    learn_about_course = Column(String, nullable=True)
    consent_images = Column(Boolean, nullable=True)
    consent_photo_on_site = Column(Boolean, nullable=True)
    what_made_you_join = Column(Text, nullable=True)
    get_from = Column(String, nullable=True)
    here_for = Column(String, nullable=True)
    claude_confidence_level = Column(Float, nullable=True)
    onboarding_date = Column(DateTime, nullable=True)

    enrollments = relationship("Enrollment", back_populates="student")


class Enrollment(Base):
    __tablename__ = "enrollments"

    id = Column(Integer, primary_key=True, index=True)
    enrollment_id = Column(String, unique=True, nullable=False)
    status = Column(String, nullable=True)
    source = Column(String, nullable=True)  # kit, stripe, form, typeform
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    sale_id = Column(Integer, ForeignKey("sales.id"), nullable=True)

    student = relationship("Student", back_populates="enrollments")
    product = relationship("Product", back_populates="enrollments")
    sale = relationship("Sale", back_populates="enrollments")

    # Survey fields (populated from CSV import)
    response_hash = Column(String, nullable=True)
    biggest_win = Column(Text, nullable=True)
    three_things_learned = Column(Text, nullable=True)
    confidence_after = Column(Integer, nullable=True)
    satisfaction = Column(String, nullable=True)
    recommend_score = Column(Integer, nullable=True)
    testimonial = Column(Text, nullable=True)
    improvement_suggestion = Column(Text, nullable=True)
    interest_longer_program = Column(String, nullable=True)
    followup_topics = Column(Text, nullable=True)
    beginner_friendly_rating = Column(String, nullable=True)
    expected_learning_not_covered = Column(Text, nullable=True)
    anything_else = Column(Text, nullable=True)
    survey_response_type = Column(String, nullable=True)
    survey_start_date = Column(DateTime, nullable=True)
    survey_stage_date = Column(DateTime, nullable=True)
    survey_submit_date = Column(DateTime, nullable=True)
    survey_network_id = Column(String, nullable=True)
    survey_tags = Column(String, nullable=True)


class Sale(Base):
    __tablename__ = "sales"

    id = Column(Integer, primary_key=True, index=True)
    sale_id = Column(String, unique=True, nullable=False)
    buyer_email = Column(String, nullable=False)
    buyer_name = Column(String, nullable=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    amount_cents = Column(Integer, nullable=False)
    currency = Column(String, default="USD")
    quantity = Column(Integer, default=1)
    status = Column(String, default="completed")  # completed, refunded
    source = Column(String, nullable=True)  # stripe, csv, manual
    stripe_checkout_session_id = Column(String, nullable=True)
    stripe_payment_intent_id = Column(String, nullable=True)
    purchase_date = Column(DateTime, nullable=True)
    notes = Column(Text, nullable=True)

    product = relationship("Product", back_populates="sales")
    enrollments = relationship("Enrollment", back_populates="sale")
