"""Savoré backend API (FastAPI).

Run:   uvicorn app.main:app --reload
Docs:  http://127.0.0.1:8000/docs   (try every endpoint in the browser)
"""
import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Literal

from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from . import claims, off, scoring
from .catalog import product_from_payload
from .db import SessionLocal, engine, get_db
from .models import Base, Category, Ingredient, Product, ProductIngredient, Submission
from .seed import seed_if_empty
from .validation import check_nutrition

NUTRIENT_COLUMNS = ["energy_kcal", "protein_g", "carbohydrate_g", "total_sugar_g", "added_sugar_g",
                    "total_fat_g", "sat_fat_g", "trans_fat_g", "fibre_g", "sodium_mg"]
# Daily reference values for %RDA (FSSAI for the first six; ICMR-NIN 2020 for the rest)
RDA = {"energy_kcal": 2000, "total_fat_g": 67, "sat_fat_g": 22, "trans_fat_g": 2,
       "added_sugar_g": 50, "sodium_mg": 2000, "protein_g": 54, "carbohydrate_g": 300, "fibre_g": 30}
DISCLAIMER = ("Informational only. Not medical advice. Based on label data, FSSAI reference values "
              "and WHO SEARO category thresholds.")

# Load everything a product needs in a few queries instead of hundreds (matters with a big database).
LOAD_ALL = (
    selectinload(Product.category).selectinload(Category.parameters),
    selectinload(Product.nutrition),
    selectinload(Product.ingredient_links).selectinload(ProductIngredient.ingredient),
    selectinload(Product.allergens),
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(engine)  # create tables on first start
    with SessionLocal() as db:
        seed_if_empty(db)  # fill with starting data if the database is empty
    yield


app = FastAPI(title="Savoré API", version="1.1", lifespan=lifespan,
              description="Backend for the Savoré food-label app: products, scores, compare, submissions.")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


# ------------------------------------------------------------------ helpers
def nutrition_dict(nf) -> dict:
    return {c: getattr(nf, c) for c in NUTRIENT_COLUMNS}


def score_for(p: Product) -> dict:
    params = [dict(factor=x.factor, kind=x.kind, t=x.t, c=x.c, h=x.h, weight=x.weight)
              for x in p.category.parameters if x.version == scoring.VERSION]
    links = p.ingredient_links
    has_nss = any(l.ingredient and l.ingredient.is_nss for l in links)
    first_wg = bool(links and links[0].ingredient and links[0].ingredient.is_whole_grain)
    return scoring.compute_score(nutrition_dict(p.nutrition), p.format, params, has_nss, first_wg)


def summary(p: Product) -> dict:
    s = score_for(p)
    return {"id": p.id, "barcode": p.barcode, "name": p.name, "brand": p.brand,
            "category": {"code": p.category.code, "name": p.category.name},
            "veg_status": p.veg_status, "verified": p.verified, "source": p.source,
            "score": s["score"], "band": s["band"]}


def detail(p: Product) -> dict:
    n = nutrition_dict(p.nutrition)
    per_serve = {k: (None if v is None else round(v * p.serve_size / 100, 2)) for k, v in n.items()}
    rda = {k: (None if per_serve[k] is None else round(per_serve[k] / ref * 100)) for k, ref in RDA.items()}
    lab = scoring.labels(n, p.format)
    return {
        **summary(p),
        "format": p.format, "fssai_licence_no": p.fssai_licence_no,
        "serve_size": p.serve_size, "serve_unit": p.serve_unit,
        "nutrition": {"per_100": n, "per_serve": per_serve, "rda_percent": rda,
                      "basis": "per 100 ml" if p.format == "beverage" else "per 100 g"},
        "labels": lab, "labels_status": "provisional",  # FSSAI front-of-pack thresholds not yet notified
        "high_in": [scoring.LABELS[k] for k, v in lab.items() if v == "High"],
        "allergens": [a.name for a in p.allergens],
        "ingredients": [{"position": l.position,
                         "id": l.ingredient.id if l.ingredient else None,
                         "name": l.ingredient.name if l.ingredient else l.raw_text,
                         "ins_code": l.ingredient.ins_code if l.ingredient else None}
                        for l in p.ingredient_links],
        "score_detail": score_for(p),
        "disclaimer": DISCLAIMER,
    }


def get_product(db: Session, product_id: int) -> Product:
    p = db.scalar(select(Product).where(Product.id == product_id).options(*LOAD_ALL))
    if p is None:
        raise HTTPException(404, "Product not found")
    return p


# ------------------------------------------------------------------ general
@app.get("/", include_in_schema=False)
def root():
    return {"app": "Savoré API", "docs": "/docs"}


@app.get("/health")
def health(db: Session = Depends(get_db)):
    return {"status": "ok", "products": db.scalar(select(func.count(Product.id)))}


@app.get("/categories")
def categories(db: Session = Depends(get_db)):
    return [{"code": c.code, "name": c.name, "format": c.format, "scored": bool(c.parameters)}
            for c in db.scalars(select(Category).options(selectinload(Category.parameters)).order_by(Category.id))]


# ----------------------------------------------------------------- products
@app.get("/products/by-barcode/{code}")
def by_barcode(code: str, db: Session = Depends(get_db)):
    """Lookup order (PRD 6.1): our database, then Open Food Facts (stored as unverified), then not found."""
    code = code.strip()
    p = db.scalar(select(Product).where(Product.barcode == code).options(*LOAD_ALL))
    if p is None:
        payload = off.lookup_barcode(code)
        if payload:
            try:
                db.add(product_from_payload(db, payload, verified=False, source="off"))
                db.commit()
            except IntegrityError:  # someone else added it at the same moment
                db.rollback()
            p = db.scalar(select(Product).where(Product.barcode == code).options(*LOAD_ALL))
    if p is None:
        raise HTTPException(404, "Not in Savoré yet")
    return detail(p)


@app.get("/products/search")
def search(q: str = "", limit: int = Query(50, le=100), offset: int = Query(0, ge=0),
           db: Session = Depends(get_db)):
    """Name, brand, category or barcode. Verified products come first."""
    stmt = select(Product).join(Category)
    if q.strip():
        like = f"%{q.strip()}%"
        stmt = stmt.where(or_(Product.name.ilike(like), Product.brand.ilike(like),
                              Category.name.ilike(like), Product.barcode.like(like)))
    stmt = stmt.order_by(Product.verified.desc(), Product.name, Product.id).limit(limit).offset(offset)
    return [summary(p) for p in db.scalars(stmt.options(*LOAD_ALL))]


@app.get("/products/{product_id}")
def product_page(product_id: int, db: Session = Depends(get_db)):
    return detail(get_product(db, product_id))


@app.get("/products/{product_id}/score")
def product_score(product_id: int, db: Session = Depends(get_db)):
    """The 'How was this calculated?' screen: both halves, every nutrient, with sources."""
    p = get_product(db, product_id)
    return {"product": summary(p), **score_for(p)}


@app.get("/ingredients/{ingredient_id}")
def ingredient(ingredient_id: int, db: Session = Depends(get_db)):
    i = db.get(Ingredient, ingredient_id)
    if i is None:
        raise HTTPException(404, "Ingredient not found")
    return {"id": i.id, "name": i.name, "ins_code": i.ins_code, "functional_class": i.functional_class,
            "what_it_is": i.what_it_is, "why_used": i.why_used, "source": i.source}


# ------------------------------------------------------------------ compare
class CompareIn(BaseModel):
    a: int
    b: int


def scoring_values(p: Product) -> dict:
    values, _ = scoring.nutrient_values(nutrition_dict(p.nutrition))  # added sugar falls back to total
    return values


@app.post("/compare")
def compare(body: CompareIn, db: Session = Depends(get_db)):
    pa, pb = get_product(db, body.a), get_product(db, body.b)
    same = pa.category_id == pb.category_id
    rows = claims.compare_rows(scoring_values(pa), scoring_values(pb), pa.name, pb.name, same)
    return {"a": summary(pa), "b": summary(pb), "same_category": same,
            "warning": None if same else "Different food types – compare with care.",
            "rows": rows, "high_in": {"a": detail(pa)["high_in"], "b": detail(pb)["high_in"]}}


# -------------------------------------------------------------- submissions
class NutritionIn(BaseModel):
    energy_kcal: float = Field(ge=0)
    protein_g: float = Field(ge=0)
    carbohydrate_g: float = Field(ge=0)
    total_sugar_g: float = Field(ge=0)
    added_sugar_g: float | None = Field(default=None, ge=0)
    total_fat_g: float = Field(ge=0)
    sat_fat_g: float = Field(ge=0)
    trans_fat_g: float = Field(default=0, ge=0)
    fibre_g: float = Field(default=0, ge=0)
    sodium_mg: float = Field(ge=0)


class SubmissionIn(BaseModel):
    barcode: str = Field(pattern=r"^\d{6,14}$")
    name: str = Field(min_length=1, max_length=160)
    brand: str | None = None
    category_code: str
    veg_status: Literal["veg", "non_veg"]
    serve_size: float = Field(gt=0)
    fssai_licence_no: str | None = None
    ingredients_text: str = Field(min_length=1)
    allergens: list[str] = []
    nutrition: NutritionIn


@app.post("/submissions", status_code=201)
def submit(body: SubmissionIn, db: Session = Depends(get_db)):
    """User adds a product. Rules are checked now; a reviewer approves it later."""
    if db.scalar(select(Category.id).where(Category.code == body.category_code)) is None:
        raise HTTPException(422, {"errors": [f"Unknown category {body.category_code}."]})
    if db.scalar(select(Product.id).where(Product.barcode == body.barcode)):
        raise HTTPException(409, "This barcode is already in Savoré.")
    errors = check_nutrition(body.nutrition.model_dump(), body.fssai_licence_no)
    if errors:
        raise HTTPException(422, {"errors": errors})
    sub = Submission(barcode=body.barcode, payload=body.model_dump())
    db.add(sub)
    db.commit()
    return {"id": sub.id, "status": sub.status, "message": "Thanks! Sent for review."}


# ------------------------------------------------------- reviewer (team only)
def reviewer(x_reviewer_key: str | None = Header(default=None)):
    if x_reviewer_key != os.getenv("REVIEWER_KEY", "savore-dev"):
        raise HTTPException(401, "Reviewer key required (header X-Reviewer-Key)")


@app.get("/submissions", dependencies=[Depends(reviewer)])
def submissions(status: str = "pending", db: Session = Depends(get_db)):
    rows = db.scalars(select(Submission).where(Submission.status == status).order_by(Submission.id))
    return [{"id": s.id, "barcode": s.barcode, "status": s.status, "payload": s.payload,
             "created_at": s.created_at.isoformat()} for s in rows]


class ReviewIn(BaseModel):
    action: Literal["approve", "reject"]
    note: str | None = None


@app.post("/submissions/{submission_id}/verify", dependencies=[Depends(reviewer)])
def verify(submission_id: int, body: ReviewIn, db: Session = Depends(get_db)):
    sub = db.get(Submission, submission_id)
    if sub is None:
        raise HTTPException(404, "Submission not found")
    if sub.status != "pending":
        raise HTTPException(409, f"Already {sub.status}")
    sub.reviewer_note, sub.reviewed_at = body.note, datetime.now(timezone.utc)
    if body.action == "reject":
        sub.status = "rejected"
    else:
        if db.scalar(select(Product.id).where(Product.barcode == sub.barcode)):
            raise HTTPException(409, "This barcode is already in Savoré.")
        product = product_from_payload(db, sub.payload, verified=True, source="user")
        db.add(product)
        db.flush()
        sub.status, sub.product_id = "approved", product.id
    db.commit()
    return {"id": sub.id, "status": sub.status, "product_id": sub.product_id}
