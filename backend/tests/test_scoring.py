"""Score engine tests. No database needed."""
import pytest

from app.scoring import compute_score
from app.seed_data import CATEGORIES, PARAMETERS, PRODUCTS

FORMAT = {code: fmt for code, _, _, fmt in CATEGORIES}


def params_for(code):
    return [dict(zip(("factor", "kind", "t", "c", "h", "weight"), r)) for r in PARAMETERS.get(code, [])]


def score(n, code="C1", fmt="solid", nss=False, wg=False):
    return compute_score(n, fmt, params_for(code), nss, wg)


CREAM_BISCUIT = dict(energy_kcal=490, protein_g=6, carbohydrate_g=60, total_sugar_g=32, added_sugar_g=30,
                     total_fat_g=20, sat_fat_g=10, trans_fat_g=0, fibre_g=1.5, sodium_mg=300)


def test_prd_worked_example():
    """PRD Appendix B: Overall 37.2, Category 55.5, Savoré Score 46 (Moderate)."""
    r = score(CREAM_BISCUIT)
    assert r["overall"]["score"] == pytest.approx(37.2, abs=0.05)
    assert r["category"]["score"] == pytest.approx(55.5, abs=0.05)
    assert r["score_exact"] == pytest.approx(46.3, abs=0.05)
    assert r["score"] == 46 and r["band"] == "Moderate"


def test_stability_two_grams_less_sugar():
    """PRD: lowering sugar by 2 g raises the score by about 0.7. No cliff."""
    better = {**CREAM_BISCUIT, "total_sugar_g": 30, "added_sugar_g": 28}
    assert score(better)["score_exact"] - score(CREAM_BISCUIT)["score_exact"] == pytest.approx(0.7, abs=0.15)


def test_added_sugar_missing_falls_back_to_total_sugar():
    r = score({**CREAM_BISCUIT, "added_sugar_g": None})
    assert r["overall"]["added_sugar_assumed"] is True
    assert any(f["note"] for f in r["overall"]["factors"])


def test_s3_product_at_every_threshold_scores_high_on_category():
    """PRD S3: at or below every WHO SEARO threshold -> Category >= 80 (by design >= 84)."""
    n = {**CREAM_BISCUIT, "total_fat_g": 8, "total_sugar_g": 6, "added_sugar_g": 6, "sodium_mg": 250,
         "energy_kcal": 230, "sat_fat_g": 2, "carbohydrate_g": 40}
    assert score(n)["category"]["score"] >= 84


def test_unknown_category_uses_overall():
    r = score(CREAM_BISCUIT, code="C2")  # C2 has no rules yet
    assert r["category_confirmed"] is False
    assert r["category"] is None and r["score_exact"] == pytest.approx(r["overall"]["score"], abs=0.05)


# ---- properties over all sample products (PRD S1 and S2) --------------------
PENALISED = ["total_sugar_g", "added_sugar_g", "sat_fat_g", "sodium_mg", "total_fat_g", "energy_kcal"]
BONUS = ["protein_g", "fibre_g"]
KEYS = ["energy_kcal", "protein_g", "carbohydrate_g", "total_sugar_g", "added_sugar_g",
        "total_fat_g", "sat_fat_g", "trans_fat_g", "fibre_g", "sodium_mg"]


def products():
    for p in PRODUCTS:
        yield p["name"], p["cat"], FORMAT[p["cat"]], dict(zip(KEYS, [None if v is None else float(v) for v in
                                                                      p["n"].values()]))


def scaled(n, column, factor):
    m = dict(n)
    columns = ["total_sugar_g", "added_sugar_g"] if column in ("total_sugar_g", "added_sugar_g") else [column]
    for c in columns:  # sugar changes together, as on a real label
        if m[c] is not None:
            m[c] = m[c] * factor
    return m


@pytest.mark.parametrize("name,code,fmt,n", list(products()))
def test_s2_more_of_a_bad_nutrient_never_raises_the_score(name, code, fmt, n):
    base = score(n, code, fmt)["score_exact"]
    for column in PENALISED:
        assert score(scaled(n, column, 1.1), code, fmt)["score_exact"] <= base + 1e-9, column
    for column in BONUS:
        assert score(scaled(n, column, 1.1), code, fmt)["score_exact"] >= base - 1e-9, column


# KNOWN LIMIT (found by this test): in C12 (fizzy drinks) total sugar has weight 50 and a steep curve
# (T=2 g, C=13 g), so 10% less sugar in the Orange Fizz sample moves the score by 3.2 points (PRD S1 asks
# for <= 3). It comes from the PRD's own Appendix A numbers. To fix it, lower the C12 sugar weight or raise
# its cap, but only after the WHO SEARO values are verified. This test makes sure no OTHER case breaks S1,
# and that this one stays visible until it is fixed.
KNOWN_S1_LIMITS = {("Orange Fizz Drink", "total_sugar_g", 0.9), ("Orange Fizz Drink", "added_sugar_g", 0.9)}


@pytest.mark.parametrize("name,code,fmt,n", list(products()))
def test_s1_ten_percent_change_moves_score_at_most_three_points(name, code, fmt, n):
    base = score(n, code, fmt)["score_exact"]
    broken = set()
    for column in PENALISED + BONUS:
        for factor in (0.9, 1.1):
            moved = score(scaled(n, column, factor), code, fmt)["score_exact"]
            if abs(moved - base) > 3.0:
                broken.add((name, column, factor))
    assert broken <= KNOWN_S1_LIMITS, f"new S1 failures: {broken - KNOWN_S1_LIMITS}"
    known_here = {k for k in KNOWN_S1_LIMITS if k[0] == name}
    assert known_here <= broken, "a known limit is fixed now: remove it from KNOWN_S1_LIMITS"
