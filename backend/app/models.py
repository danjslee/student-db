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

    enrollments = relationship("Enrollment", back_populates="product")


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
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)

    student = relationship("Student", back_populates="enrollments")
    product = relationship("Product", back_populates="enrollments")
