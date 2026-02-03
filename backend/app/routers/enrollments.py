from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models import Enrollment, Student, Product
from app.schemas import EnrollmentCreate, EnrollmentUpdate, EnrollmentRead

router = APIRouter(prefix="/api/enrollments", tags=["enrollments"])


@router.get("/", response_model=List[EnrollmentRead])
def list_enrollments(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    status: Optional[str] = None,
    product_id: Optional[int] = None,
    student_id: Optional[int] = None,
    db: Session = Depends(get_db),
):
    q = (
        db.query(Enrollment)
        .options(
            joinedload(Enrollment.student),
            joinedload(Enrollment.product),
        )
    )
    if status:
        q = q.filter(Enrollment.status == status)
    if product_id:
        q = q.filter(Enrollment.product_id == product_id)
    if student_id:
        q = q.filter(Enrollment.student_id == student_id)

    return q.order_by(Enrollment.id).offset(skip).limit(limit).all()


@router.get("/{enrollment_id}", response_model=EnrollmentRead)
def get_enrollment(enrollment_id: int, db: Session = Depends(get_db)):
    enrollment = (
        db.query(Enrollment)
        .options(
            joinedload(Enrollment.student),
            joinedload(Enrollment.product),
        )
        .filter(Enrollment.id == enrollment_id)
        .first()
    )
    if not enrollment:
        raise HTTPException(404, "Enrollment not found")
    return enrollment


@router.post("/", response_model=EnrollmentRead, status_code=201)
def create_enrollment(payload: EnrollmentCreate, db: Session = Depends(get_db)):
    # Verify FK references exist
    if not db.query(Student).filter(Student.id == payload.student_id).first():
        raise HTTPException(400, "Student not found")
    if not db.query(Product).filter(Product.id == payload.product_id).first():
        raise HTTPException(400, "Product not found")

    enrollment = Enrollment(**payload.model_dump())
    db.add(enrollment)
    db.commit()
    db.refresh(enrollment)
    # Reload with relationships
    return (
        db.query(Enrollment)
        .options(joinedload(Enrollment.student), joinedload(Enrollment.product))
        .filter(Enrollment.id == enrollment.id)
        .first()
    )


@router.put("/{enrollment_id}", response_model=EnrollmentRead)
def update_enrollment(enrollment_id: int, payload: EnrollmentUpdate, db: Session = Depends(get_db)):
    enrollment = db.query(Enrollment).filter(Enrollment.id == enrollment_id).first()
    if not enrollment:
        raise HTTPException(404, "Enrollment not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(enrollment, key, value)
    db.commit()
    db.refresh(enrollment)
    return (
        db.query(Enrollment)
        .options(joinedload(Enrollment.student), joinedload(Enrollment.product))
        .filter(Enrollment.id == enrollment.id)
        .first()
    )


@router.delete("/{enrollment_id}", status_code=204)
def delete_enrollment(enrollment_id: int, db: Session = Depends(get_db)):
    enrollment = db.query(Enrollment).filter(Enrollment.id == enrollment_id).first()
    if not enrollment:
        raise HTTPException(404, "Enrollment not found")
    db.delete(enrollment)
    db.commit()
