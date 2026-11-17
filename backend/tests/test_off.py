"""Open Food Facts mapping and the live-lookup fallback. No internet is used."""
from app import off
from app.ingredients import split_ingredients

GOOD = {
    "code": "8906000000019", "product_name": "Test Masala Chips", "brands": "ChipCo, Other",
    "categories_tags": ["en:snacks", "en:salty-snacks", "en:chips-and-fries"],
    "nutriments": {"energy-kcal_100g": 520, "proteins_100g": 6, "carbohydrates_100g": 52, "sugars_100g": 2,
                   "fat_100g": 32, "saturated-fat_100g": 14, "fiber_100g": 3, "salt_100g": 1.5},
    "ingredients_text": "Potato, Palm oil, Salt, Spices (chilli, turmeric), INS 621",
    "allergens_tags": ["en:milk", "en:something-we-ignore"], "ingredients_analysis_tags": ["en:vegetarian"],
    "serving_quantity": 30,
}


def test_maps_a_complete_product():
    p = off.map_product(GOOD)
    assert p["barcode"] == "8906000000019" and p["brand"] == "ChipCo"
    assert p["category_code"] == "C4" and p["veg_status"] == "veg" and p["serve_size"] == 30
    assert p["nutrition"]["sodium_mg"] == 600  # salt 1.5 g x 400
    assert p["allergens"] == ["Milk"]


def test_sodium_in_grams_is_converted_and_kj_to_kcal():
    raw = {**GOOD, "nutriments": {**GOOD["nutriments"], "sodium_100g": 0.5, "salt_100g": None,
                                  "energy-kcal_100g": None, "energy_100g": 2174}}
    n = off.map_product(raw)["nutrition"]
    assert n["sodium_mg"] == 500 and abs(n["energy_kcal"] - 519.6) < 0.5


def test_incomplete_or_impossible_products_are_rejected():
    assert off.map_product({**GOOD, "product_name": ""}) is None
    assert off.map_product({**GOOD, "code": "12"}) is None
    no_fat = {**GOOD, "nutriments": {k: v for k, v in GOOD["nutriments"].items() if k != "fat_100g"}}
    assert off.map_product(no_fat) is None
    impossible = {**GOOD, "nutriments": {**GOOD["nutriments"], "sugars_100g": 90}}  # more than carbs
    assert off.map_product(impossible) is None


def test_veg_flag_and_category_fallbacks():
    assert off.map_product({**GOOD, "ingredients_analysis_tags": ["en:non-vegetarian"]})["veg_status"] == "non_veg"
    assert off.map_product({**GOOD, "ingredients_analysis_tags": ["en:maybe-vegetarian"]})["veg_status"] == "not_declared"
    assert off.category_for(["en:nuts", "en:salty-snacks"]) == "C5"  # specific rule beats the general one
    assert off.category_for(["en:instant-noodles"]) == "C7"
    assert off.category_for(["en:waters"]) == "G-B"
    assert off.category_for(["en:something-unknown"]) == "G-S"


def test_ingredient_splitter_keeps_brackets_together():
    assert split_ingredients("Flour (wheat, salt), Sugar; INS 322.") == ["Flour (wheat, salt)", "Sugar", "INS 322"]


def test_unknown_barcode_is_fetched_from_off_then_stored_unverified(client, monkeypatch):
    monkeypatch.setenv("OFF_LOOKUP", "1")
    calls = []

    def fake_lookup(code):
        calls.append(code)
        return off.map_product({**GOOD, "code": code})

    monkeypatch.setattr("app.main.off.lookup_barcode", fake_lookup)
    r = client.get("/products/by-barcode/8906000000026")
    assert r.status_code == 200
    p = r.json()
    assert p["name"] == "Test Masala Chips" and p["verified"] is False and p["source"] == "off"
    assert p["ingredients"][-1]["ins_code"] == "INS 621" and p["allergens"] == ["Milk"]
    assert client.get("/products/by-barcode/8906000000026").status_code == 200
    assert calls == ["8906000000026"]  # second time came from our own database


def test_search_puts_verified_products_first(client):
    first = client.get("/products/search").json()
    flags = [x["verified"] for x in first]
    assert flags == sorted(flags, reverse=True)  # all True first, then False
