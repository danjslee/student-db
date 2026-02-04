from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, Integer

from app.database import get_db
from app.models import Student, Enrollment
from app.schemas import CountItem, TimelineItem

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("/students-by-country", response_model=List[CountItem])
def students_by_country(
    product_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    q = db.query(Student.country, func.count(func.distinct(Student.id)))
    if product_id is not None:
        q = q.join(Enrollment, Enrollment.student_id == Student.id).filter(
            Enrollment.product_id == product_id
        )
    q = (
        q.filter(Student.country.isnot(None), Student.country != "")
        .group_by(Student.country)
        .order_by(func.count(func.distinct(Student.id)).desc())
    )
    rows = q.all()
    return [CountItem(label=country, count=count) for country, count in rows]


@router.get("/students-by-city", response_model=List[CountItem])
def students_by_city(
    product_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    q = db.query(Student.closest_city, func.count(func.distinct(Student.id)))
    if product_id is not None:
        q = q.join(Enrollment, Enrollment.student_id == Student.id).filter(
            Enrollment.product_id == product_id
        )
    q = (
        q.filter(Student.closest_city.isnot(None), Student.closest_city != "")
        .group_by(Student.closest_city)
        .order_by(func.count(func.distinct(Student.id)).desc())
    )
    rows = q.all()
    return [CountItem(label=city, count=count) for city, count in rows]


@router.get("/enrollment-status", response_model=List[CountItem])
def enrollment_status(db: Session = Depends(get_db)):
    rows = (
        db.query(Enrollment.status, func.count(Enrollment.id))
        .filter(Enrollment.status.isnot(None), Enrollment.status != "")
        .group_by(Enrollment.status)
        .order_by(func.count(Enrollment.id).desc())
        .all()
    )
    return [CountItem(label=status, count=count) for status, count in rows]


@router.get("/onboarding-timeline", response_model=List[TimelineItem])
def onboarding_timeline(db: Session = Depends(get_db)):
    rows = (
        db.query(
            func.date(Student.onboarding_date).label("day"),
            func.count(Student.id),
        )
        .filter(Student.onboarding_date.isnot(None))
        .group_by("day")
        .order_by("day")
        .all()
    )
    return [TimelineItem(date=day, count=count) for day, count in rows]


@router.get("/confidence-distribution", response_model=List[CountItem])
def confidence_distribution(db: Session = Depends(get_db)):
    # Bucket confidence levels into integer ranges (floor)
    bucket = func.cast(Student.claude_confidence_level, Integer).label("level")
    rows = (
        db.query(bucket, func.count(Student.id))
        .filter(Student.claude_confidence_level.isnot(None))
        .group_by(bucket)
        .order_by(bucket)
        .all()
    )
    return [CountItem(label=str(int(level)), count=count) for level, count in rows]


@router.get("/referral-sources", response_model=List[CountItem])
def referral_sources(db: Session = Depends(get_db)):
    rows = (
        db.query(Student.learn_about_course, func.count(Student.id))
        .filter(Student.learn_about_course.isnot(None), Student.learn_about_course != "")
        .group_by(Student.learn_about_course)
        .order_by(func.count(Student.id).desc())
        .all()
    )
    return [CountItem(label=source, count=count) for source, count in rows]


@router.get("/satisfaction-distribution", response_model=List[CountItem])
def satisfaction_distribution(db: Session = Depends(get_db)):
    rows = (
        db.query(Enrollment.satisfaction, func.count(Enrollment.id))
        .filter(
            Enrollment.satisfaction.isnot(None),
            Enrollment.satisfaction != "",
        )
        .group_by(Enrollment.satisfaction)
        .order_by(func.count(Enrollment.id).desc())
        .all()
    )
    return [CountItem(label=level, count=count) for level, count in rows]


@router.get("/nps-distribution", response_model=List[CountItem])
def nps_distribution(db: Session = Depends(get_db)):
    rows = (
        db.query(Enrollment.recommend_score, func.count(Enrollment.id))
        .filter(Enrollment.recommend_score.isnot(None))
        .group_by(Enrollment.recommend_score)
        .order_by(Enrollment.recommend_score)
        .all()
    )
    return [CountItem(label=str(int(score)), count=count) for score, count in rows]


@router.get("/confidence-after-distribution", response_model=List[CountItem])
def confidence_after_distribution(db: Session = Depends(get_db)):
    rows = (
        db.query(Enrollment.confidence_after, func.count(Enrollment.id))
        .filter(Enrollment.confidence_after.isnot(None))
        .group_by(Enrollment.confidence_after)
        .order_by(Enrollment.confidence_after)
        .all()
    )
    return [CountItem(label=str(int(level)), count=count) for level, count in rows]
