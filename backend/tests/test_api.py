"""API tests: run against a fresh, seeded test database."""

BISCUIT = {
    "barcode": "8909999999991", "name": "Test Cream Biscuit", "brand": "Test Co", "category_code": "C1",
    "veg_status": "veg", "serve_size": 25, "ingredients_text": "Refined wheat flour (maida), Sugar, INS 322",
    "allergens": ["gluten"],
    "nutrition": {"energy_kcal": 480, "protein_g": 6, "carbohydrate_g": 65, "total_sugar_g": 20,
                  "added_sugar_g": 15, "total_fat_g": 20, "sat_fat_g": 9, "fibre_g": 2, "sodium_mg": 300},
}
KEY = {"X-Reviewer-Key": "test-key"}


def find(client, q):
    return client.get("/products/search", params={"q": q}).json()


def test_health_and_seed(client):
    assert client.get("/health").json() == {"status": "ok", "products": 8}


def test_barcode_found_has_everything_the_product_page_needs(client):
    r = client.get("/products/by-barcode/8901000000011")
    assert r.status_code == 200
    p = r.json()
    assert p["name"] == "Masala Instant Noodles" and p["veg_status"] == "veg"
    assert p["allergens"] == ["Gluten"] and len(p["ingredients"]) == 9
    assert p["labels"]["sodium"] == "High" and "Sodium" in p["high_in"]
    assert p["nutrition"]["rda_percent"]["sodium_mg"] == 42  # 840 mg per 70 g serve / 2000 mg
    assert 0 <= p["score"] <= 100 and p["band"] in ("Limit", "Moderate", "Better choice")


def test_barcode_not_found(client):
    r = client.get("/products/by-barcode/0000000000")
    assert r.status_code == 404


def test_search(client):
    assert len(find(client, "noodles")) == 3
    assert len(find(client, "")) == 8


def test_score_breakdown_shows_both_halves_with_sources(client):
    pid = find(client, "Masala")[0]["id"]
    s = client.get(f"/products/{pid}/score").json()
    assert s["overall"]["start"] == 80 and s["category"]["start"] == 100
    assert all(f["source"] for f in s["overall"]["factors"] + s["category"]["factors"])
    assert s["score"] == client.get(f"/products/{pid}").json()["score"]


def test_ingredient_explainer(client):
    ins = client.get("/products/by-barcode/8901000000011").json()["ingredients"]
    msg = next(i for i in ins if i["ins_code"] == "INS 621")
    r = client.get(f"/ingredients/{msg['id']}").json()
    assert r["name"] == "Monosodium glutamate" and r["source"]


def test_compare_same_category_uses_claims_guard(client):
    a = find(client, "Masala Instant")[0]["id"]
    b = find(client, "Whole Wheat")[0]["id"]
    r = client.post("/compare", json={"a": b, "b": a}).json()
    assert r["same_category"] and r["warning"] is None
    sodium = next(x for x in r["rows"] if x["nutrient"] == "Sodium")
    assert sodium["verdict"] == "less" and "less sodium" in sodium["statement"]
    protein = next(x for x in r["rows"] if x["nutrient"] == "Protein")
    assert protein["verdict"] == "similar" and protein["statement"] is None  # 11 g vs 9 g: too close


def test_compare_different_categories_gives_no_comparative_words(client):
    a = find(client, "Masala Instant")[0]["id"]
    b = find(client, "Rolled Oats")[0]["id"]
    r = client.post("/compare", json={"a": a, "b": b}).json()
    assert r["warning"] == "Different food types – compare with care."
    assert all(x["statement"] is None for x in r["rows"])


def test_submission_rules_block_bad_data(client):
    bad = {**BISCUIT, "nutrition": {**BISCUIT["nutrition"], "added_sugar_g": 25}}  # more than total sugar
    r = client.post("/submissions", json=bad)
    assert r.status_code == 422 and "Added sugar" in r.json()["detail"]["errors"][0]


def test_submission_of_existing_barcode_is_refused(client):
    assert client.post("/submissions", json={**BISCUIT, "barcode": "8901000000011"}).status_code == 409


def test_reviewer_flow_submit_approve_then_scan(client):
    sub = client.post("/submissions", json=BISCUIT)
    assert sub.status_code == 201 and sub.json()["status"] == "pending"
    sid = sub.json()["id"]

    assert client.get("/submissions").status_code == 401  # no key
    assert client.post(f"/submissions/{sid}/verify", json={"action": "approve"}).status_code == 401
    assert [s["id"] for s in client.get("/submissions", headers=KEY).json()] == [sid]

    r = client.post(f"/submissions/{sid}/verify", json={"action": "approve"}, headers=KEY)
    assert r.status_code == 200 and r.json()["status"] == "approved"
    assert client.post(f"/submissions/{sid}/verify", json={"action": "approve"}, headers=KEY).status_code == 409

    p = client.get(f"/products/by-barcode/{BISCUIT['barcode']}").json()  # now scannable, with a score
    assert p["name"] == "Test Cream Biscuit" and p["verified"] is True
    assert p["ingredients"][0]["id"] is not None and p["ingredients"][2]["ins_code"] == "INS 322"
    assert p["score_detail"]["category_confirmed"] is True
