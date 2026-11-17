"""Database tables (SQLAlchemy). A simplified, working version of PRD section 12.

categories ──< products >── nutrition_facts (1 row each)
categories ──< category_parameters          (scoring rules, stored as data)
products ──< product_ingredients >── ingredients
products ──< product_allergens  >── allergens
submissions                                 (user-added products waiting for review)
"""
from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def now() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class Category(Base):
    __tablename__ = "categories"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(8), unique=True)  # C1..C20, G-S, G-B
    name: Mapped[str] = mapped_column(String(120))
    searo_code: Mapped[str | None] = mapped_column(String(8))
    format: Mapped[str] = mapped_column(String(10))  # solid | beverage
    parameters: Mapped[list["CategoryParameter"]] = relationship(back_populates="category")


class CategoryParameter(Base):
    """One scoring rule for one category, e.g. 'sodium: T=250, C=700, weight 15'."""
    __tablename__ = "category_parameters"
    id: Mapped[int] = mapped_column(primary_key=True)
    version: Mapped[str] = mapped_column(String(10), default="v1")
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id"))
    factor: Mapped[str] = mapped_column(String(20))  # fat, total_sugar, sodium, nss, wg ...
    kind: Mapped[str] = mapped_column(String(10))  # penalty | bonus | binary
    t: Mapped[float | None] = mapped_column(Float)  # WHO SEARO threshold
    c: Mapped[float | None] = mapped_column(Float)  # cap
    h: Mapped[float | None] = mapped_column(Float)  # "high in" level for bonuses
    weight: Mapped[float] = mapped_column(Float)
    t_source: Mapped[str] = mapped_column(String(10), default="searo")  # searo | team
    citation: Mapped[str | None] = mapped_column(Text)
    category: Mapped[Category] = relationship(back_populates="parameters")


class Allergen(Base):
    __tablename__ = "allergens"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(40), unique=True)


class ProductAllergen(Base):
    __tablename__ = "product_allergens"
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), primary_key=True)
    allergen_id: Mapped[int] = mapped_column(ForeignKey("allergens.id"), primary_key=True)


class Ingredient(Base):
    """Reference entry: what an ingredient / INS code is, why it is used, source."""
    __tablename__ = "ingredients"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    ins_code: Mapped[str | None] = mapped_column(String(20))
    functional_class: Mapped[str | None] = mapped_column(String(60))
    what_it_is: Mapped[str] = mapped_column(Text)
    why_used: Mapped[str] = mapped_column(Text)
    source: Mapped[str] = mapped_column(Text)
    is_nss: Mapped[bool] = mapped_column(Boolean, default=False)  # non-sugar sweetener
    is_whole_grain: Mapped[bool] = mapped_column(Boolean, default=False)


class ProductIngredient(Base):
    __tablename__ = "product_ingredients"
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), primary_key=True)
    position: Mapped[int] = mapped_column(primary_key=True)  # order printed on the label
    ingredient_id: Mapped[int | None] = mapped_column(ForeignKey("ingredients.id"))
    raw_text: Mapped[str | None] = mapped_column(String(200))  # used when not in our list
    ingredient: Mapped[Ingredient | None] = relationship()


class Nutrition(Base):
    """Nutrition per 100 g (solids) or per 100 ml (beverages), as sold."""
    __tablename__ = "nutrition_facts"
    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), unique=True)
    energy_kcal: Mapped[float] = mapped_column(Float)
    protein_g: Mapped[float] = mapped_column(Float)
    carbohydrate_g: Mapped[float] = mapped_column(Float)
    total_sugar_g: Mapped[float] = mapped_column(Float)
    added_sugar_g: Mapped[float | None] = mapped_column(Float)  # None = not declared
    total_fat_g: Mapped[float] = mapped_column(Float)
    sat_fat_g: Mapped[float] = mapped_column(Float)
    trans_fat_g: Mapped[float] = mapped_column(Float, default=0)
    fibre_g: Mapped[float] = mapped_column(Float, default=0)
    sodium_mg: Mapped[float] = mapped_column(Float)


class Product(Base):
    __tablename__ = "products"
    id: Mapped[int] = mapped_column(primary_key=True)
    barcode: Mapped[str] = mapped_column(String(14), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(160))
    brand: Mapped[str | None] = mapped_column(String(80))
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id"))
    format: Mapped[str] = mapped_column(String(10))  # solid | beverage
    veg_status: Mapped[str] = mapped_column(String(15))  # veg | non_veg | not_declared
    fssai_licence_no: Mapped[str | None] = mapped_column(String(14))
    serve_size: Mapped[float] = mapped_column(Float)
    serve_unit: Mapped[str] = mapped_column(String(2), default="g")  # g | ml
    verified: Mapped[bool] = mapped_column(Boolean, default=False)
    source: Mapped[str] = mapped_column(String(10), default="seed")  # seed | user
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

    category: Mapped[Category] = relationship()
    nutrition: Mapped[Nutrition] = relationship(uselist=False, cascade="all, delete-orphan")
    ingredient_links: Mapped[list[ProductIngredient]] = relationship(
        order_by="ProductIngredient.position", cascade="all, delete-orphan"
    )
    allergens: Mapped[list[Allergen]] = relationship(secondary="product_allergens")


class Submission(Base):
    """A product added by a user. A reviewer approves or rejects it."""
    __tablename__ = "submissions"
    id: Mapped[int] = mapped_column(primary_key=True)
    barcode: Mapped[str] = mapped_column(String(14), index=True)
    payload: Mapped[dict] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(10), default="pending")  # pending|approved|rejected
    reviewer_note: Mapped[str | None] = mapped_column(Text)
    product_id: Mapped[int | None] = mapped_column(ForeignKey("products.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
