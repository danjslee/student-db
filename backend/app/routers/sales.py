from __future__ import annotations

import csv
import io
import logging
import re
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models import Sale, Product, Enrollment
from app.schemas import SaleCreate, SaleUpdate, SaleRead, SaleCSVImportResult

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/sales", tags=["sales"])


@router.get("/", response_model=List[SaleRead])
def list_sales(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    product_id: Optional[int] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
):
    q = db.query(Sale).options(joinedload(Sale.product))
    if product_id:
        q = q.filter(Sale.product_id == product_id)
    if status:
        q = q.filter(Sale.status == status)
    return q.order_by(Sale.id.desc()).offset(skip).limit(limit).all()


@router.get("/{sale_id}", response_model=SaleRead)
def get_sale(sale_id: int, db: Session = Depends(get_db)):
    sale = (
        db.query(Sale)
        .options(joinedload(Sale.product))
        .filter(Sale.id == sale_id)
        .first()
    )
    if not sale:
        raise HTTPException(404, "Sale not found")
    return sale


@router.post("/", response_model=SaleRead, status_code=201)
def create_sale(payload: SaleCreate, db: Session = Depends(get_db)):
    if not db.query(Product).filter(Product.id == payload.product_id).first():
        raise HTTPException(400, "Product not found")
    sale = Sale(**payload.model_dump())
    db.add(sale)
    db.commit()
    db.refresh(sale)
    return (
        db.query(Sale)
        .options(joinedload(Sale.product))
        .filter(Sale.id == sale.id)
        .first()
    )


@router.put("/{sale_id}", response_model=SaleRead)
def update_sale(sale_id: int, payload: SaleUpdate, db: Session = Depends(get_db)):
    sale = db.query(Sale).filter(Sale.id == sale_id).first()
    if not sale:
        raise HTTPException(404, "Sale not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(sale, key, value)
    db.commit()
    db.refresh(sale)
    return (
        db.query(Sale)
        .options(joinedload(Sale.product))
        .filter(Sale.id == sale.id)
        .first()
    )


@router.delete("/{sale_id}", status_code=204)
def delete_sale(sale_id: int, db: Session = Depends(get_db)):
    sale = db.query(Sale).filter(Sale.id == sale_id).first()
    if not sale:
        raise HTTPException(404, "Sale not found")
    db.delete(sale)
    db.commit()


def _parse_price(price_str: str) -> int:
    """Parse a price string like '$712.00' or '712' into cents."""
    cleaned = re.sub(r'[^0-9.]', '', str(price_str))
    if not cleaned:
        return 0
    return int(round(float(cleaned) * 100))


def _parse_date(date_str: str) -> Optional[datetime]:
    """Try common date formats."""
    if not date_str or not date_str.strip():
        return None
    for fmt in ("%m/%d/%Y", "%Y-%m-%d", "%m/%d/%y", "%d/%m/%Y", "%B %d, %Y"):
        try:
            return datetime.strptime(date_str.strip(), fmt)
        except ValueError:
            continue
    return None


@router.post("/import-csv", response_model=SaleCSVImportResult)
async def import_sales_csv(
    product_id: str = Query(..., description="Product ID slug (e.g. ccfb1)"),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """
    Import sales from CSV. Expected columns (flexible matching):
    Email, Name, Purchase Date, RSVP Status, Price Paid USD
    """
    product = db.query(Product).filter(Product.product_id == product_id).first()
    if not product:
        raise HTTPException(404, f"No product with product_id '{product_id}'")

    content = await file.read()
    text = content.decode("utf-8-sig")  # handle BOM
    reader = csv.DictReader(io.StringIO(text))

    # Flexible column name matching
    def find_col(fieldnames, *candidates):
        for c in candidates:
            for f in fieldnames:
                if c.lower() in f.lower():
                    return f
        return None

    fields = reader.fieldnames or []
    col_email = find_col(fields, "email")
    col_name = find_col(fields, "name", "buyer")
    col_date = find_col(fields, "purchase date", "date")
    col_status = find_col(fields, "rsvp", "status")
    col_price = find_col(fields, "price", "amount", "paid")

    if not col_email:
        raise HTTPException(400, f"No email column found. Columns: {fields}")

    created = 0
    skipped = 0
    linked = 0
    errors = []

    for i, row in enumerate(reader, start=2):
        try:
            email = (row.get(col_email) or "").strip().lower()
            if not email:
                continue

            name = (row.get(col_name) or "").strip() if col_name else None
            date_str = (row.get(col_date) or "").strip() if col_date else ""
            status_str = (row.get(col_status) or "").strip() if col_status else ""
            price_str = (row.get(col_price) or "0").strip() if col_price else "0"

            purchase_date = _parse_date(date_str)
            date_part = purchase_date.strftime("%Y%m%d") if purchase_date else "unknown"
            sale_id_str = f"{email}_{product_id}_{date_part}"

            # Deduplicate
            existing = db.query(Sale).filter(Sale.sale_id == sale_id_str).first()
            if existing:
                skipped += 1
                continue

            status = "refunded" if "refund" in status_str.lower() else "completed"
            amount_cents = _parse_price(price_str)

            sale = Sale(
                sale_id=sale_id_str,
                buyer_email=email,
                buyer_name=name,
                product_id=product.id,
                amount_cents=amount_cents,
                currency="USD",
                quantity=1,
                status=status,
                source="csv",
                purchase_date=purchase_date,
                notes=status_str if status_str else None,
            )
            db.add(sale)
            db.flush()

            # Link to existing enrollment by email + product
            enrollment = (
                db.query(Enrollment)
                .filter(
                    Enrollment.enrollment_id == f"{email}_{product_id}",
                    Enrollment.sale_id.is_(None),
                )
                .first()
            )
            if enrollment:
                enrollment.sale_id = sale.id
                linked += 1

            created += 1
        except Exception as e:
            errors.append(f"Row {i}: {str(e)}")

    db.commit()
    logger.info(
        "CSV import for %s: created=%d skipped=%d linked=%d errors=%d",
        product_id, created, skipped, linked, len(errors),
    )
    return SaleCSVImportResult(created=created, skipped=skipped, linked=linked, errors=errors)
