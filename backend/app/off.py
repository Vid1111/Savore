"""Open Food Facts (OFF): real packaged-food data, including a lot of Indian products.

OFF data is licensed under the ODbL, so every product imported here:
  - is stored as UNVERIFIED (PRD section 10) and shown with an "Unverified" notice,
  - carries the source "off" so the app can show the attribution.
"""
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request

from .validation import check_nutrition

BASE = "https://world.openfoodfacts.org"
USER_AGENT = "SavoreStudentProject/1.0 (university course project)"
FIELDS = ("code,product_name,brands,categories_tags,nutriments,ingredients_text,allergens_tags,"
          "ingredients_analysis_tags,serving_quantity")

# Open Food Facts category tags -> Savoré category. The FIRST matching rule wins, so specific
# categories come before general ones (nuts before snacks, noodles before cereals ...).
CATEGORY_RULES = [
    ("C12", {"en:carbonated-drinks", "en:sodas", "en:colas", "en:energy-drinks", "en:soft-drinks"}),
    ("C13", {"en:fruit-juices", "en:juices-and-nectars", "en:fruit-nectars", "en:fruit-based-beverages"}),
    ("C14", {"en:dairy-drinks", "en:flavoured-milks", "en:lassi", "en:buttermilks", "en:milkshakes"}),
    ("C15", {"en:teas", "en:coffees", "en:instant-coffees", "en:iced-teas", "en:tea-based-beverages"}),
    ("C16", {"en:malt-drinks", "en:beverage-preparations", "en:instant-beverages", "en:chocolate-powders"}),
    ("C7", {"en:instant-noodles", "en:noodles", "en:pastas", "en:vermicelli"}),
    ("C5", {"en:nuts", "en:peanuts", "en:roasted-nuts", "en:salted-nuts", "en:almonds", "en:cashew-nuts",
            "en:mixed-nuts", "en:seeds", "en:nuts-and-their-products"}),
    ("C1", {"en:biscuits", "en:cookies", "en:cakes", "en:rusks", "en:biscuits-and-cakes"}),
    ("C3", {"en:breakfast-cereals", "en:cereal-flakes", "en:oat-flakes", "en:muesli", "en:oatmeals"}),
    ("C6", {"en:chocolates", "en:candies", "en:confectioneries", "en:indian-sweets", "en:jams",
            "en:fruit-jams", "en:chocolate-candies"}),
    ("C4", {"en:salty-snacks", "en:crisps", "en:potato-crisps", "en:chips-and-fries", "en:extruded-snacks",
            "en:puffed-snacks", "en:bhujia", "en:namkeen", "en:appetizers"}),
    ("C9", {"en:yogurts", "en:dahi", "en:curds", "en:shrikhand"}),
    ("C10", {"en:cheeses", "en:paneer"}),
    ("C11", {"en:ice-creams", "en:frozen-desserts"}),
    ("C2", {"en:breads", "en:buns"}),
    ("C8", {"en:soups", "en:ready-meals", "en:meals", "en:instant-soups"}),
    ("C17", {"en:sauces", "en:ketchup", "en:chutneys", "en:dips", "en:spreads"}),
    ("C18", {"en:pickles"}),
    ("C19", {"en:fats", "en:vegetable-oils", "en:ghee", "en:butters", "en:margarines", "en:oils"}),
    ("C20", {"en:processed-meats", "en:sausages", "en:meat-products"}),
]
BEVERAGE_CODES = {"C12", "C13", "C14", "C15", "C16", "G-B"}

ALLERGEN_TAGS = {
    "en:gluten": "Gluten", "en:milk": "Milk", "en:soybeans": "Soy", "en:peanuts": "Peanut",
    "en:nuts": "Tree nuts", "en:eggs": "Egg", "en:fish": "Fish", "en:crustaceans": "Crustaceans",
    "en:sulphur-dioxide-and-sulphites": "Sulphite",
}


def category_for(tags: list[str]) -> str:
    tagset = set(tags)
    for code, wanted in CATEGORY_RULES:
        if tagset & wanted:
            return code
    # Not one of our categories: general fallback, beverage if it looks like a drink.
    if any(w in t for t in tags for w in ("beverage", "drinks", "waters")):
        return "G-B"
    return "G-S"


def _num(nutriments: dict, key: str) -> float | None:
    v = nutriments.get(key)
    try:
        return None if v is None or v == "" else float(v)
    except (TypeError, ValueError):
        return None


def map_product(raw: dict) -> dict | None:
    """OFF record -> our product payload, or None if it is incomplete or fails our data rules."""
    code = str(raw.get("code", "")).strip()
    name = (raw.get("product_name") or "").strip()
    if not re.fullmatch(r"\d{6,14}", code) or not name:
        return None
    n = raw.get("nutriments") or {}

    kcal = _num(n, "energy-kcal_100g")
    if kcal is None and _num(n, "energy_100g") is not None:
        kcal = _num(n, "energy_100g") / 4.184  # kJ -> kcal
    sodium = _num(n, "sodium_100g")
    sodium = sodium * 1000 if sodium is not None else (
        _num(n, "salt_100g") * 400 if _num(n, "salt_100g") is not None else None)  # g -> mg; salt = 2.5 x sodium
    values = {
        "energy_kcal": kcal, "protein_g": _num(n, "proteins_100g"), "carbohydrate_g": _num(n, "carbohydrates_100g"),
        "total_sugar_g": _num(n, "sugars_100g"), "total_fat_g": _num(n, "fat_100g"),
        "sat_fat_g": _num(n, "saturated-fat_100g"), "sodium_mg": sodium,
    }
    if any(v is None for v in values.values()):
        return None  # we only keep products with the nutrition we need to score them

    nutrition = {k: round(v, 2) for k, v in values.items()}
    nutrition["added_sugar_g"] = _num(n, "added-sugars_100g")
    nutrition["trans_fat_g"] = _num(n, "trans-fat_100g") or 0
    nutrition["fibre_g"] = _num(n, "fiber_100g") or 0

    # Reject obvious data-entry mistakes, tidy small rounding differences.
    limits = {"protein_g": 100, "carbohydrate_g": 100, "total_sugar_g": 100, "total_fat_g": 100,
              "sat_fat_g": 100, "energy_kcal": 900, "sodium_mg": 40000, "fibre_g": 100}
    if any(nutrition[k] < 0 or nutrition[k] > cap for k, cap in limits.items()):
        return None
    if 0 < nutrition["total_sugar_g"] - nutrition["carbohydrate_g"] <= 1:
        nutrition["total_sugar_g"] = nutrition["carbohydrate_g"]
    if 0 < nutrition["sat_fat_g"] - nutrition["total_fat_g"] <= 0.5:
        nutrition["sat_fat_g"] = nutrition["total_fat_g"]
    if nutrition["added_sugar_g"] is not None and not 0 <= nutrition["added_sugar_g"] <= nutrition["total_sugar_g"]:
        nutrition["added_sugar_g"] = None  # unreliable: treat as "not declared"
    if check_nutrition(nutrition):
        return None

    tags = raw.get("ingredients_analysis_tags") or []
    veg = "non_veg" if "en:non-vegetarian" in tags else "veg" if "en:vegetarian" in tags else "not_declared"
    serving = _num({"s": raw.get("serving_quantity")}, "s")
    brand = (raw.get("brands") or "").split(",")[0].strip()
    return {
        "barcode": code, "name": name[:160], "brand": brand[:80] or None,
        "category_code": category_for(raw.get("categories_tags") or []),
        "veg_status": veg, "serve_size": serving if serving and serving > 0 else 100.0,
        "ingredients_text": (raw.get("ingredients_text") or "")[:2000],
        "allergens": sorted({ALLERGEN_TAGS[t] for t in raw.get("allergens_tags") or [] if t in ALLERGEN_TAGS}),
        "nutrition": nutrition,
    }


# ------------------------------------------------------------------ network
def _get_json(url: str, tries: int = 6, timeout: int = 60) -> dict | None:
    """GET with retries: OFF often answers 503 when busy. Returns None on 404."""
    for attempt in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            return json.load(urllib.request.urlopen(req, timeout=timeout))
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            if e.code in (401, 403, 429):  # we are going too fast: Open Food Facts asks us to slow down
                time.sleep(60 * (attempt + 1))
                continue
            if e.code not in (500, 502, 503, 504):
                raise
        except (urllib.error.URLError, TimeoutError):
            pass
        time.sleep(5 + 4 * attempt)
    raise RuntimeError("Open Food Facts is not answering. Try again later.")


def fetch_page(page: int, page_size: int = 100) -> list[dict]:
    """One page of products sold in India."""
    q = urllib.parse.urlencode({"countries_tags_en": "india", "fields": FIELDS,
                                "page_size": page_size, "page": page})
    data = _get_json(f"{BASE}/api/v2/search?{q}")
    return (data or {}).get("products", [])


def lookup_barcode(code: str) -> dict | None:
    """Live lookup of one barcode (PRD lookup order: our database, then OFF, then 'not found').
    Never raises: any problem means 'not found'. Switch off with OFF_LOOKUP=0."""
    if os.getenv("OFF_LOOKUP", "1") == "0" or not re.fullmatch(r"\d{6,14}", code):
        return None
    try:
        data = _get_json(f"{BASE}/api/v2/product/{code}.json?fields={FIELDS}", tries=1, timeout=6)
    except Exception:
        return None
    if not data or data.get("status") != 1:
        return None
    return map_product({**data["product"], "code": code})
