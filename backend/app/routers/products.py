from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.models import Product, Enrollment
from app.schemas import ProductCreate, ProductUpdate, ProductRead

router = APIRouter(prefix="/api/products", tags=["products"])


@router.get("/", response_model=List[ProductRead])
def list_products(db: Session = Depends(get_db)):
    rows = (
        db.query(Product, func.count(Enrollment.id).label("enrollment_count"))
        .outerjoin(Enrollment)
        .group_by(Product.id)
        .order_by(Product.id)
        .all()
    )
    results = []
    for product, enrollment_count in rows:
        d = ProductRead.model_validate(product)
        d.enrollment_count = enrollment_count
        results.append(d)
    return results


@router.get("/{product_id}", response_model=ProductRead)
def get_product(product_id: int, db: Session = Depends(get_db)):
    row = (
        db.query(Product, func.count(Enrollment.id).label("enrollment_count"))
        .outerjoin(Enrollment)
        .filter(Product.id == product_id)
        .group_by(Product.id)
        .first()
    )
    if not row:
        raise HTTPException(404, "Product not found")
    product, enrollment_count = row
    d = ProductRead.model_validate(product)
    d.enrollment_count = enrollment_count
    return d


@router.post("/", response_model=ProductRead, status_code=201)
def create_product(payload: ProductCreate, db: Session = Depends(get_db)):
    product = Product(**payload.model_dump())
    db.add(product)
    db.commit()
    db.refresh(product)
    d = ProductRead.model_validate(product)
    d.enrollment_count = 0
    return d


@router.put("/{product_id}", response_model=ProductRead)
def update_product(product_id: int, payload: ProductUpdate, db: Session = Depends(get_db)):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(404, "Product not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(product, key, value)
    db.commit()
    db.refresh(product)
    count = db.query(func.count(Enrollment.id)).filter(Enrollment.product_id == product_id).scalar()
    d = ProductRead.model_validate(product)
    d.enrollment_count = count
    return d


@router.delete("/{product_id}", status_code=204)
def delete_product(product_id: int, db: Session = Depends(get_db)):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(404, "Product not found")
    db.delete(product)
    db.commit()
