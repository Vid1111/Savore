"""Builds a Product row (with nutrition, ingredients, allergens) from a plain dict.
Used by the review flow (approved submissions) and by the Open Food Facts importer."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from .ingredients import match_ingredient, split_ingredients
from .models import Allergen, Category, Ingredient, Nutrition, Product, ProductIngredient


def product_from_payload(db: Session, data: dict, *, verified: bool = True, source: str = "user",
                         known: list[Ingredient] | None = None, cats: dict[str, Category] | None = None,
                         allergens: dict[str, Allergen] | None = None) -> Product:
    """Pass `known`, `cats` and `allergens` (pre-loaded lookups) when adding many products at once."""
    cat = cats[data["category_code"]] if cats is not None else db.scalar(
        select(Category).where(Category.code == data["category_code"]))
    known = known if known is not None else list(db.scalars(select(Ingredient)))

    links = []
    for pos, text in enumerate(split_ingredients(data.get("ingredients_text", "")), start=1):
        i = match_ingredient(known, text)
        links.append(ProductIngredient(position=pos, ingredient=i, raw_text=None if i else text[:200]))

    found = []
    for name in data.get("allergens", []):
        key = name.strip().capitalize()
        a = allergens.get(key) if allergens is not None else db.scalar(select(Allergen).where(Allergen.name == key))
        if a is None:
            a = Allergen(name=key)
            if allergens is not None:
                allergens[key] = a
        found.append(a)

    return Product(
        barcode=data["barcode"], name=data["name"][:160], brand=(data.get("brand") or None) and data["brand"][:80],
        category=cat, format=cat.format, veg_status=data["veg_status"], serve_size=data["serve_size"],
        serve_unit="ml" if cat.format == "beverage" else "g", fssai_licence_no=data.get("fssai_licence_no"),
        verified=verified, source=source, nutrition=Nutrition(**data["nutrition"]),
        ingredient_links=links, allergens=found)
