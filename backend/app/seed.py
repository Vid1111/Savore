"""Fills an empty database with the starting data. Safe to run more than once."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from . import seed_data as d
from .models import (Allergen, Category, CategoryParameter, Ingredient, Nutrition, Product,
                     ProductIngredient)
from .scoring import VERSION

CAP_NOTE = "C is a team-proposed cap: replace with the 90th percentile once the category has 20 verified products."


def seed_if_empty(db: Session) -> bool:
    if db.scalar(select(Category.id).limit(1)) is not None:
        return False

    cats = {}
    for code, name, searo, fmt in d.CATEGORIES:
        cats[code] = Category(code=code, name=name, searo_code=searo, format=fmt)
        db.add(cats[code])

    for code, rules in d.PARAMETERS.items():
        for factor, kind, t, c, h, weight in rules:
            db.add(CategoryParameter(
                version=VERSION, category=cats[code], factor=factor, kind=kind, t=t, c=c, h=h,
                weight=weight, t_source="searo",
                citation=f"WHO SEARO Nutrient Profile Model 2017 (category {cats[code].searo_code}), "
                         f"via PRD v3.0 Appendix A. Verify against the original. {CAP_NOTE}"))

    allergens = {n: Allergen(name=n) for n in d.ALLERGENS}
    db.add_all(allergens.values())

    ingredients = {}
    for key, i in d.INGREDIENTS.items():
        ingredients[key] = Ingredient(
            name=i["name"], ins_code=i["ins"], functional_class=i["cls"], what_it_is=i["what"],
            why_used=i["why"], source=i["source"], is_nss=i["nss"], is_whole_grain=i["wg"])
        db.add(ingredients[key])
    db.flush()

    for p in d.PRODUCTS:
        cat = cats[p["cat"]]
        product = Product(
            barcode=p["barcode"], name=p["name"], brand=p["brand"], category=cat, format=cat.format,
            veg_status=p["veg"], serve_size=p["serve"], serve_unit=p["unit"], verified=True, source="seed",
            nutrition=Nutrition(**p["n"]),
            allergens=[allergens[a] for a in p["allergens"]])
        product.ingredient_links = [
            ProductIngredient(position=i + 1, ingredient=ingredients[k]) for i, k in enumerate(p["ings"])]
        db.add(product)

    db.commit()
    return True
