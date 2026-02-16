from __future__ import annotations

import logging
from typing import List, Optional
from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, Integer, extract, case

from app.database import get_db
from app.models import Student, Enrollment, Product, Sale
from app.schemas import CountItem, TimelineItem

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


# ── Helpers ──────────────────────────────────────────────

def _parse_product_ids(product_ids: Optional[str]) -> Optional[List[int]]:
    """Parse comma-separated product IDs string into list of ints."""
    if not product_ids:
        return None
    try:
        return [int(x.strip()) for x in product_ids.split(",") if x.strip()]
    except ValueError:
        return None


def _filter_by_products(q, product_ids_str: Optional[str], product_id: Optional[int] = None):
    """Apply product filter — supports both single product_id and multi product_ids."""
    ids = _parse_product_ids(product_ids_str)
    if ids:
        q = q.join(Enrollment, Enrollment.student_id == Student.id).filter(
            Enrollment.product_id.in_(ids)
        )
    elif product_id is not None:
        q = q.join(Enrollment, Enrollment.student_id == Student.id).filter(
            Enrollment.product_id == product_id
        )
    return q


def _filter_enrollments_by_products(q, product_ids_str: Optional[str]):
    """Filter enrollment queries by product_ids."""
    ids = _parse_product_ids(product_ids_str)
    if ids:
        q = q.filter(Enrollment.product_id.in_(ids))
    return q


# ── Overview (Phase 2) ──────────────────────────────────

@router.get("/overview")
def overview(
    year: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """Cross-course KPIs + per-course breakdown."""
    products = db.query(Product).all()

    # Year filter
    year_int = int(year) if year and year.isdigit() else None

    courses = []
    total_students = 0
    total_revenue = 0
    total_refunds = 0
    all_nps = []
    total_enrollments_with_survey = 0
    total_enrollments = 0

    for product in products:
        # Year filter: determine if this product belongs to the selected year
        # A product belongs to a year if it has any student onboarded in that year
        # OR any sale purchased in that year. Then show ALL enrollments.
        if year_int:
            from sqlalchemy import or_
            has_students_in_year = db.query(Enrollment.id).join(Student).filter(
                Enrollment.product_id == product.id,
                extract("year", Student.onboarding_date) == year_int,
            ).first() is not None
            has_sales_in_year = db.query(Sale.id).filter(
                Sale.product_id == product.id,
                extract("year", Sale.purchase_date) == year_int,
            ).first() is not None
            if not has_students_in_year and not has_sales_in_year:
                continue

        # ALL enrollments for this product (not filtered by date)
        enrollments = db.query(Enrollment).filter(
            Enrollment.product_id == product.id
        ).all()
        enrollment_count = len(enrollments)
        if enrollment_count == 0:
            continue

        total_enrollments += enrollment_count

        # All sales for this product
        all_product_sales = db.query(Sale).filter(Sale.product_id == product.id).all()
        # Build sale lookup by id
        sale_by_id = {s.id: s for s in all_product_sales}

        # Enrollment breakdown — derived from linked Sale data
        # Categories: Full Fee, Early Bird, Scholarship, Free Place, Refunded, Deferred
        breakdown = {}
        for e in enrollments:
            sale = sale_by_id.get(e.sale_id) if e.sale_id else None
            if sale:
                if sale.status == "refunded":
                    cat = "Refunded"
                elif sale.status == "deferred":
                    cat = "Deferred"
                elif getattr(sale, "scholarship", 0) == 1:
                    cat = "Scholarship"
                else:
                    # Check enrollment status for early-bird hint
                    e_status = (e.status or "").lower()
                    if "early" in e_status:
                        cat = "Early Bird"
                    else:
                        cat = "Full Fee"
            else:
                cat = "Free Place"
            breakdown[cat] = breakdown.get(cat, 0) + 1
        # Remove zero entries
        breakdown = {k: v for k, v in breakdown.items() if v > 0}

        # Revenue data (filtered by year for revenue)
        sale_q = db.query(Sale).filter(Sale.product_id == product.id)
        if year_int:
            sale_q = sale_q.filter(extract("year", Sale.purchase_date) == year_int)
        sales = sale_q.all()

        revenue = sum(s.amount_cents for s in sales if s.status == "completed")
        refunds = sum(s.amount_cents for s in sales if s.status == "refunded")
        total_revenue += revenue
        total_refunds += refunds

        # NPS — actual NPS formula: %promoters(9-10) - %detractors(0-6)
        nps_scores = [e.recommend_score for e in enrollments if e.recommend_score is not None]
        if nps_scores:
            promoters = sum(1 for s in nps_scores if s >= 9)
            detractors = sum(1 for s in nps_scores if s <= 6)
            course_nps = round((promoters - detractors) / len(nps_scores) * 100)
        else:
            course_nps = None
        all_nps.extend(nps_scores)

        # Scholarships — from Sale.scholarship flag
        scholarship_count = sum(1 for s in all_product_sales if getattr(s, "scholarship", 0) == 1)
        scholarship_amount = sum(
            (s.amount_cents or 0) for s in all_product_sales
            if getattr(s, "scholarship", 0) == 1
        )

        # Student count (distinct)
        student_ids = set(e.student_id for e in enrollments)
        total_students += len(student_ids)

        courses.append({
            "product_id": product.id,
            "product_name": product.product_name,
            "enrollment_count": enrollment_count,
            "student_count": len(student_ids),
            "revenue_cents": revenue,
            "refund_cents": refunds,
            "nps": course_nps,
            "enrollment_breakdown": breakdown,
            "scholarship_count": scholarship_count,
            "scholarship_amount_cents": scholarship_amount,
        })

    # Overall NPS from all scores
    if all_nps:
        promoters = sum(1 for s in all_nps if s >= 9)
        detractors = sum(1 for s in all_nps if s <= 6)
        overall_nps = round((promoters - detractors) / len(all_nps) * 100)
    else:
        overall_nps = None

    return {
        "total_students": total_students,
        "total_revenue_cents": total_revenue,
        "total_refunds_cents": total_refunds,
        "nps": overall_nps,
        "courses": courses,
    }


# ── Purchase Timeline ─────────────────────────────────────

def _build_benchmark_curve(db: Session) -> dict:
    """Build a benchmark curve from the first completed course (ccfb).

    Returns dict mapping days_before -> cumulative_pct (0-100).
    Used to forecast sales for upcoming courses.
    """
    # Find the first product with a past course_start_date (= completed course)
    today = date.today()
    completed = (
        db.query(Product)
        .filter(Product.course_start_date.isnot(None), Product.course_start_date < today)
        .order_by(Product.course_start_date)
        .first()
    )
    if not completed:
        return {}

    start_date = completed.course_start_date
    if isinstance(start_date, datetime):
        start_date = start_date.date()

    sales = (
        db.query(Sale)
        .filter(
            Sale.product_id == completed.id,
            Sale.status != "refunded",
            Sale.purchase_date.isnot(None),
        )
        .all()
    )
    if not sales:
        return {}

    total = len(sales)
    daily = {}
    for s in sales:
        pdate = s.purchase_date.date() if isinstance(s.purchase_date, datetime) else s.purchase_date
        d = (start_date - pdate).days
        daily[d] = daily.get(d, 0) + 1

    # Build cumulative pct curve (from earliest to latest)
    curve = {}
    cumul = 0
    for d in sorted(daily.keys(), reverse=True):
        cumul += daily[d]
        curve[d] = round(cumul / total * 100, 2)

    return curve


@router.get("/purchase-timeline")
def purchase_timeline(
    db: Session = Depends(get_db),
):
    """Purchase timeline with forecast based on historical benchmark."""
    products = db.query(Product).filter(Product.course_start_date.isnot(None)).all()
    if not products:
        return []

    today = date.today()
    benchmark = _build_benchmark_curve(db)

    result = []
    for product in products:
        start_date = product.course_start_date
        if isinstance(start_date, datetime):
            start_date = start_date.date()

        sales = (
            db.query(Sale)
            .filter(
                Sale.product_id == product.id,
                Sale.status != "refunded",
                Sale.purchase_date.isnot(None),
            )
            .order_by(Sale.purchase_date)
            .all()
        )
        if not sales:
            continue

        total_sales = len(sales)
        total_rev = sum(s.amount_cents or 0 for s in sales)
        avg_price = total_rev / total_sales if total_sales else 0

        # Build daily cumulative data
        daily = {}
        for s in sales:
            pdate = s.purchase_date.date() if isinstance(s.purchase_date, datetime) else s.purchase_date
            days_before = (start_date - pdate).days
            if days_before not in daily:
                daily[days_before] = {"count": 0, "revenue_cents": 0}
            daily[days_before]["count"] += 1
            daily[days_before]["revenue_cents"] += s.amount_cents or 0

        # Build actual cumulative series
        sorted_days = sorted(daily.keys(), reverse=True)
        cumulative = 0
        cumulative_rev = 0
        actual_series = []
        for d in sorted_days:
            cumulative += daily[d]["count"]
            cumulative_rev += daily[d]["revenue_cents"]
            actual_series.append({
                "days_before": d,
                "date": str(start_date - timedelta(days=d)),
                "new_sales": daily[d]["count"],
                "cumulative": cumulative,
                "revenue_cents": daily[d]["revenue_cents"],
                "cumulative_revenue_cents": cumulative_rev,
            })

        # Forecast for upcoming courses
        days_until_start = (start_date - today).days
        is_upcoming = days_until_start > 0
        forecast_series = []
        forecast_total_sales = None
        forecast_total_revenue = None
        rating = None

        if is_upcoming and benchmark and total_sales > 0:
            # Find where we are on the benchmark curve
            # Get benchmark pct at current days_until_start
            bench_pct_now = 0
            for d in sorted(benchmark.keys(), reverse=True):
                if d >= days_until_start:
                    bench_pct_now = benchmark[d]
            # If no benchmark data at this point, use the lowest available
            if bench_pct_now == 0:
                bench_pct_now = min(benchmark.values()) if benchmark else 1

            # Projected total = current_sales / (bench_pct_now / 100)
            projected_total = round(total_sales / (bench_pct_now / 100))
            forecast_total_sales = projected_total
            forecast_total_revenue = round(projected_total * avg_price)

            # Build forecast curve from today to course start
            for d in sorted(benchmark.keys(), reverse=True):
                if d < days_until_start:
                    projected_at_d = round(projected_total * benchmark[d] / 100)
                    forecast_series.append({
                        "days_before": d,
                        "date": str(start_date - timedelta(days=d)),
                        "cumulative": projected_at_d,
                    })

            # Rating vs target
            target = product.sales_target
            if target and forecast_total_sales:
                pct_of_target = forecast_total_sales / target * 100
                if pct_of_target >= 80:
                    rating = "green"
                elif pct_of_target >= 50:
                    rating = "yellow"
                else:
                    rating = "red"

        days_list = sorted([
            (start_date - (s.purchase_date.date() if isinstance(s.purchase_date, datetime) else s.purchase_date)).days
            for s in sales
        ])

        result.append({
            "product_id": product.id,
            "product_name": product.product_name,
            "product_slug": product.product_id,
            "course_start_date": str(start_date),
            "is_upcoming": is_upcoming,
            "days_until_start": (start_date - today).days,
            "total_sales": total_sales,
            "total_revenue_cents": total_rev,
            "avg_price_cents": round(avg_price),
            "sales_target": product.sales_target,
            "forecast_total_sales": forecast_total_sales,
            "forecast_total_revenue_cents": forecast_total_revenue,
            "rating": rating,
            "median_days_before": days_list[len(days_list) // 2] if days_list else None,
            "actual_series": actual_series,
            "forecast_series": forecast_series,
        })

    return result


# ── Existing endpoints (updated with product_ids support) ─

@router.get("/students-by-country", response_model=List[CountItem])
def students_by_country(
    product_id: Optional[int] = Query(None),
    product_ids: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    q = db.query(Student.country, func.count(func.distinct(Student.id)))
    q = _filter_by_products(q, product_ids, product_id)
    q = (
        q.filter(Student.country.isnot(None), Student.country != "")
        .group_by(Student.country)
        .order_by(func.count(func.distinct(Student.id)).desc())
    )
    return [CountItem(label=country, count=count) for country, count in q.all()]


@router.get("/students-by-city", response_model=List[CountItem])
def students_by_city(
    product_id: Optional[int] = Query(None),
    product_ids: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    q = db.query(Student.closest_city, func.count(func.distinct(Student.id)))
    q = _filter_by_products(q, product_ids, product_id)
    q = (
        q.filter(Student.closest_city.isnot(None), Student.closest_city != "")
        .group_by(Student.closest_city)
        .order_by(func.count(func.distinct(Student.id)).desc())
    )
    return [CountItem(label=city, count=count) for city, count in q.all()]


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


# ── Confidence (before) ─────────────────────────────────

@router.get("/confidence-distribution", response_model=List[CountItem])
def confidence_distribution(
    product_ids: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    bucket = func.cast(Student.claude_confidence_level, Integer).label("level")
    q = db.query(bucket, func.count(Student.id)).filter(Student.claude_confidence_level.isnot(None))
    ids = _parse_product_ids(product_ids)
    if ids:
        q = q.join(Enrollment, Enrollment.student_id == Student.id).filter(Enrollment.product_id.in_(ids))
    q = q.group_by(bucket).order_by(bucket)
    return [CountItem(label=str(int(level)), count=count) for level, count in q.all()]


# ── Confidence (after) ──────────────────────────────────

@router.get("/confidence-after-distribution", response_model=List[CountItem])
def confidence_after_distribution(
    product_ids: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    q = (
        db.query(Enrollment.confidence_after, func.count(Enrollment.id))
        .filter(Enrollment.confidence_after.isnot(None))
    )
    q = _filter_enrollments_by_products(q, product_ids)
    q = q.group_by(Enrollment.confidence_after).order_by(Enrollment.confidence_after)
    return [CountItem(label=str(int(level)), count=count) for level, count in q.all()]


# ── Referral Sources ────────────────────────────────────

@router.get("/referral-sources", response_model=List[CountItem])
def referral_sources(
    product_ids: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    q = db.query(Student.learn_about_course, func.count(Student.id)).filter(
        Student.learn_about_course.isnot(None), Student.learn_about_course != ""
    )
    ids = _parse_product_ids(product_ids)
    if ids:
        q = q.join(Enrollment, Enrollment.student_id == Student.id).filter(Enrollment.product_id.in_(ids))
    q = q.group_by(Student.learn_about_course).order_by(func.count(Student.id).desc())
    return [CountItem(label=source, count=count) for source, count in q.all()]


# ── Satisfaction ────────────────────────────────────────

@router.get("/satisfaction-distribution", response_model=List[CountItem])
def satisfaction_distribution(
    product_ids: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    q = (
        db.query(Enrollment.satisfaction, func.count(Enrollment.id))
        .filter(Enrollment.satisfaction.isnot(None), Enrollment.satisfaction != "")
    )
    q = _filter_enrollments_by_products(q, product_ids)
    q = q.group_by(Enrollment.satisfaction).order_by(func.count(Enrollment.id).desc())
    return [CountItem(label=level, count=count) for level, count in q.all()]


# ── NPS Distribution ───────────────────────────────────

@router.get("/nps-distribution", response_model=List[CountItem])
def nps_distribution(
    product_ids: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    q = (
        db.query(Enrollment.recommend_score, func.count(Enrollment.id))
        .filter(Enrollment.recommend_score.isnot(None))
    )
    q = _filter_enrollments_by_products(q, product_ids)
    q = q.group_by(Enrollment.recommend_score).order_by(Enrollment.recommend_score)
    return [CountItem(label=str(int(score)), count=count) for score, count in q.all()]


# ── Phase 3: Cohort Snapshot ────────────────────────────

@router.get("/timezone-distribution", response_model=List[CountItem])
def timezone_distribution(
    product_ids: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    q = db.query(Student.timezone, func.count(func.distinct(Student.id))).filter(
        Student.timezone.isnot(None), Student.timezone != ""
    )
    ids = _parse_product_ids(product_ids)
    if ids:
        q = q.join(Enrollment, Enrollment.student_id == Student.id).filter(Enrollment.product_id.in_(ids))
    q = q.group_by(Student.timezone).order_by(func.count(func.distinct(Student.id)).desc())
    return [CountItem(label=tz, count=count) for tz, count in q.all()]


@router.get("/age-distribution")
def age_distribution(
    product_ids: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    q = db.query(Student.dob).filter(Student.dob.isnot(None))
    ids = _parse_product_ids(product_ids)
    if ids:
        q = q.join(Enrollment, Enrollment.student_id == Student.id).filter(Enrollment.product_id.in_(ids))

    dobs = [row[0] for row in q.all()]
    if not dobs:
        return {"buckets": [], "average_age": None}

    today = date.today()
    ages = []
    for dob in dobs:
        if isinstance(dob, datetime):
            dob = dob.date()
        age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
        ages.append(age)

    avg_age = round(sum(ages) / len(ages), 1)

    # Bucket into decade ranges
    buckets = {}
    for age in ages:
        bucket = f"{(age // 10) * 10}s"
        buckets[bucket] = buckets.get(bucket, 0) + 1

    bucket_list = [{"label": k, "count": v} for k, v in sorted(buckets.items())]
    return {"buckets": bucket_list, "average_age": avg_age}


@router.get("/gender-distribution", response_model=List[CountItem])
def gender_distribution(
    product_ids: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    q = db.query(Student.gender, func.count(func.distinct(Student.id))).filter(
        Student.gender.isnot(None), Student.gender != ""
    )
    ids = _parse_product_ids(product_ids)
    if ids:
        q = q.join(Enrollment, Enrollment.student_id == Student.id).filter(Enrollment.product_id.in_(ids))
    q = q.group_by(Student.gender).order_by(func.count(func.distinct(Student.id)).desc())
    return [CountItem(label=g, count=count) for g, count in q.all()]


# ── Phase 4: Decision to Join ───────────────────────────

@router.get("/here-for-distribution", response_model=List[CountItem])
def here_for_distribution(
    product_ids: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    q = db.query(Student.here_for, func.count(func.distinct(Student.id))).filter(
        Student.here_for.isnot(None), Student.here_for != ""
    )
    ids = _parse_product_ids(product_ids)
    if ids:
        q = q.join(Enrollment, Enrollment.student_id == Student.id).filter(Enrollment.product_id.in_(ids))
    q = q.group_by(Student.here_for).order_by(func.count(func.distinct(Student.id)).desc())
    return [CountItem(label=v, count=c) for v, c in q.all()]


@router.get("/get-from-distribution", response_model=List[CountItem])
def get_from_distribution(
    product_ids: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    q = db.query(Student.get_from, func.count(func.distinct(Student.id))).filter(
        Student.get_from.isnot(None), Student.get_from != ""
    )
    ids = _parse_product_ids(product_ids)
    if ids:
        q = q.join(Enrollment, Enrollment.student_id == Student.id).filter(Enrollment.product_id.in_(ids))
    q = q.group_by(Student.get_from).order_by(func.count(func.distinct(Student.id)).desc())
    return [CountItem(label=v, count=c) for v, c in q.all()]


@router.get("/survey-response-rates")
def survey_response_rates(
    product_ids: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    q = db.query(Enrollment)
    q = _filter_enrollments_by_products(q, product_ids)
    enrollments = q.all()

    total = len(enrollments)
    if total == 0:
        return {"onboarding_rate": 0, "completion_rate": 0}

    # Onboarding: student has learn_about_course or here_for or get_from filled
    student_ids = [e.student_id for e in enrollments]
    students = db.query(Student).filter(Student.id.in_(student_ids)).all() if student_ids else []
    student_map = {s.id: s for s in students}

    onboarding_count = 0
    for e in enrollments:
        s = student_map.get(e.student_id)
        if s and (s.learn_about_course or s.here_for or s.get_from):
            onboarding_count += 1

    # Completion: enrollment has recommend_score or satisfaction
    completion_count = sum(
        1 for e in enrollments
        if e.recommend_score is not None or e.satisfaction is not None
    )

    return {
        "onboarding_rate": onboarding_count / total,
        "completion_rate": completion_count / total,
    }


# ── Phase 5: Transformational + Delivered on Promise ────

@router.get("/transformational-distribution", response_model=List[CountItem])
def transformational_distribution(
    product_ids: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    q = (
        db.query(Enrollment.transformational_score, func.count(Enrollment.id))
        .filter(Enrollment.transformational_score.isnot(None))
    )
    q = _filter_enrollments_by_products(q, product_ids)
    q = q.group_by(Enrollment.transformational_score).order_by(Enrollment.transformational_score)
    return [CountItem(label=str(int(score)), count=count) for score, count in q.all()]


@router.get("/delivered-on-promise-distribution", response_model=List[CountItem])
def delivered_on_promise_distribution(
    product_ids: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    q = (
        db.query(Enrollment.delivered_on_promise_score, func.count(Enrollment.id))
        .filter(Enrollment.delivered_on_promise_score.isnot(None))
    )
    q = _filter_enrollments_by_products(q, product_ids)
    q = q.group_by(Enrollment.delivered_on_promise_score).order_by(Enrollment.delivered_on_promise_score)
    return [CountItem(label=str(int(score)), count=count) for score, count in q.all()]


# ── Phase 6: Testimonials ──────────────────────────────

@router.get("/testimonials")
def testimonials(
    product_ids: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    q = (
        db.query(Enrollment)
        .join(Student, Student.id == Enrollment.student_id)
        .join(Product, Product.id == Enrollment.product_id)
        .filter(Enrollment.testimonial.isnot(None), Enrollment.testimonial != "")
    )
    q = _filter_enrollments_by_products(q, product_ids)
    enrollments = q.all()

    result = []
    for e in enrollments:
        student = db.query(Student).filter(Student.id == e.student_id).first()
        product = db.query(Product).filter(Product.id == e.product_id).first()
        result.append({
            "student_name": f"{student.first_name} {student.last_name}" if student else "Unknown",
            "product_name": product.product_name if product else "Unknown",
            "testimonial": e.testimonial,
        })

    return result
