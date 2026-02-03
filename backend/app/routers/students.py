from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func

from app.database import get_db
from app.models import Student, Enrollment
from app.schemas import StudentCreate, StudentUpdate, StudentRead, StudentList

router = APIRouter(prefix="/api/students", tags=["students"])


@router.get("/", response_model=List[StudentList])
def list_students(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    search: Optional[str] = None,
    country: Optional[str] = None,
    city: Optional[str] = None,
    db: Session = Depends(get_db),
):
    q = db.query(
        Student,
        func.count(Enrollment.id).label("enrollment_count"),
    ).outerjoin(Enrollment).group_by(Student.id)

    if search:
        pattern = f"%{search}%"
        q = q.filter(
            (Student.first_name.ilike(pattern))
            | (Student.last_name.ilike(pattern))
            | (Student.email.ilike(pattern))
        )
    if country:
        q = q.filter(Student.country == country)
    if city:
        q = q.filter(Student.closest_city == city)

    rows = q.order_by(Student.student_number).offset(skip).limit(limit).all()

    results = []
    for student, enrollment_count in rows:
        d = StudentList.model_validate(student)
        d.enrollment_count = enrollment_count
        results.append(d)
    return results


@router.get("/{student_id}", response_model=StudentRead)
def get_student(student_id: int, db: Session = Depends(get_db)):
    student = (
        db.query(Student)
        .options(joinedload(Student.enrollments).joinedload(Enrollment.product))
        .filter(Student.id == student_id)
        .first()
    )
    if not student:
        raise HTTPException(404, "Student not found")
    return student


@router.post("/", response_model=StudentRead, status_code=201)
def create_student(payload: StudentCreate, db: Session = Depends(get_db)):
    student = Student(**payload.model_dump())
    db.add(student)
    db.commit()
    db.refresh(student)
    return student


@router.put("/{student_id}", response_model=StudentRead)
def update_student(student_id: int, payload: StudentUpdate, db: Session = Depends(get_db)):
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(404, "Student not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(student, key, value)
    db.commit()
    db.refresh(student)
    return student


@router.delete("/{student_id}", status_code=204)
def delete_student(student_id: int, db: Session = Depends(get_db)):
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(404, "Student not found")
    db.delete(student)
    db.commit()
