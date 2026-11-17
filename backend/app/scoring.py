"""The Savoré Score engine (PRD v3.0 section 7).

    Savoré Score = 0.5 x Overall + 0.5 x Category - Ingredient modifier (0 for now)

Everything here is a plain function: numbers in, numbers out. No database.
"""
VERSION = "v1"
BLEND_W = 0.5

# ---- Overall half: control points (amount, points) per nutrient -------------
# Between points the score changes in a straight line. After the last point it stays flat.
SOLID = {
    "added_sugar": [(0, 0), (5, -5), (12.5, -15), (25, -25)],  # g per 100 g
    "sat_fat": [(0, 0), (1.5, -4), (5.5, -12), (11, -20)],
    "sodium": [(0, 0), (120, -4), (500, -12), (1000, -20)],  # mg
    "protein": [(0, 0), (5, 5), (10, 10)],
    "fibre": [(0, 0), (3, 5), (6, 10)],
}
BEVERAGE = {  # per 100 ml
    "added_sugar": [(0, 0), (2.5, -5), (6.25, -15), (12.5, -25)],
    "sat_fat": [(0, 0), (0.75, -4), (2.75, -12), (5.5, -20)],
    "sodium": [(0, 0), (120, -4), (250, -12), (500, -20)],
    "protein": [(0, 0), (2.5, 5), (5, 10)],
    "fibre": [(0, 0), (1.5, 5), (3, 10)],
}
LABELS = {"added_sugar": "Added sugar", "sat_fat": "Saturated fat", "sodium": "Sodium",
          "protein": "Protein", "fibre": "Fibre"}
UNITS = {"added_sugar": "g", "sat_fat": "g", "sodium": "mg", "protein": "g", "fibre": "g"}

# ---- Category half: which nutrient column each rule reads -------------------
FACTOR_COLUMN = {
    "fat": "total_fat_g", "total_sugar": "total_sugar_g", "added_sugar": "added_sugar_g",
    "sodium": "sodium_mg", "energy": "energy_kcal", "sat_fat": "sat_fat_g",
    "trans_fat": "trans_fat_g", "fibre": "fibre_g", "protein": "protein_g",
}
FACTOR_LABEL = {
    "fat": "Total fat", "total_sugar": "Total sugar", "added_sugar": "Added sugar", "sodium": "Sodium",
    "energy": "Energy", "sat_fat": "Saturated fat", "trans_fat": "Trans fat", "fibre": "Fibre",
    "protein": "Protein", "nss": "Non-sugar sweetener present", "wg": "Whole grain is first ingredient",
}

OVERALL_SOURCE = "FSSAI Schedule I claim levels and FSSAI daily reference values (Claims 2018, L&D 2020)"
CATEGORY_SOURCE = "WHO SEARO Nutrient Profile Model 2017 (category thresholds)"


def clamp(x: float, lo: float = 0, hi: float = 100) -> float:
    return max(lo, min(hi, x))


def interp(points: list[tuple[float, float]], x: float) -> float:
    """Straight-line interpolation between control points; flat after the last one."""
    if x <= points[0][0]:
        return points[0][1]
    for (x0, y0), (x1, y1) in zip(points, points[1:]):
        if x <= x1:
            return y0 + (y1 - y0) * (x - x0) / (x1 - x0)
    return points[-1][1]


def band(score: int) -> str:
    return "Limit" if score < 40 else "Moderate" if score < 70 else "Better choice"


def nutrient_values(n: dict) -> tuple[dict, bool]:
    """Nutrient amounts used for scoring. If added sugar isn't declared, total sugar is used."""
    assumed = n.get("added_sugar_g") is None
    values = dict(n)
    if assumed:
        values["added_sugar_g"] = n["total_sugar_g"]
    return values, assumed


# ------------------------------------------------------------------ Overall
def overall_score(n: dict, fmt: str) -> dict:
    table = BEVERAGE if fmt == "beverage" else SOLID
    values, assumed = nutrient_values(n)
    amounts = {"added_sugar": values["added_sugar_g"], "sat_fat": values["sat_fat_g"],
               "sodium": values["sodium_mg"], "protein": values["protein_g"], "fibre": values["fibre_g"]}
    total, factors = 80.0, []
    for key, points in table.items():
        pts = interp(points, amounts[key])
        total += pts
        note = "added sugar not declared: total sugar used" if key == "added_sugar" and assumed else None
        factors.append({"factor": LABELS[key], "value": amounts[key], "unit": UNITS[key],
                        "points": round(pts, 2), "source": OVERALL_SOURCE, "note": note})
    return {"score": round(clamp(total), 2), "start": 80, "factors": factors,
            "added_sugar_assumed": assumed}


def labels(n: dict, fmt: str) -> dict:
    """Low / Moderate / High for added sugar, saturated fat and sodium."""
    table = BEVERAGE if fmt == "beverage" else SOLID
    values, _ = nutrient_values(n)
    amounts = {"added_sugar": values["added_sugar_g"], "sat_fat": values["sat_fat_g"],
               "sodium": values["sodium_mg"]}
    result = {}
    for key, x in amounts.items():
        low, high = table[key][1][0], table[key][2][0]
        result[key] = "Low" if x <= low else "Moderate" if x <= high else "High"
    return result


# ----------------------------------------------------------------- Category
def penalty_fraction(x: float, t: float, c: float) -> float:
    """0 at 0, 0.2 at the WHO threshold T, 1 at the cap C, flat after."""
    if x <= 0:
        return 0.0
    if x <= t:
        return 0.2 * x / t
    if x >= c:
        return 1.0
    return 0.2 + 0.8 * (x - t) / (c - t)


def category_score(n: dict, params: list[dict], has_nss: bool, first_whole_grain: bool) -> dict | None:
    """params: [{factor, kind, t, c, h, weight}, ...] for the product's category.
    Returns None when the category has no rules (then Category = Overall)."""
    if not params:
        return None
    values, assumed = nutrient_values(n)
    total, factors = 100.0, []
    for p in params:
        f, kind = p["factor"], p["kind"]
        if kind == "penalty":
            x = values[FACTOR_COLUMN[f]]
            pts = -p["weight"] * penalty_fraction(x, p["t"], p["c"])
            detail = {"value": x, "t": p["t"], "c": p["c"], "weight": p["weight"]}
        elif kind == "bonus":
            x = values[FACTOR_COLUMN[f]]
            pts = p["weight"] * min(x / p["h"], 1)
            detail = {"value": x, "h": p["h"], "weight": p["weight"]}
        else:  # binary: nss is a penalty, wg is a bonus
            present = has_nss if f == "nss" else first_whole_grain
            pts = (-p["weight"] if f == "nss" else p["weight"]) * (1 if present else 0)
            detail = {"present": present, "weight": p["weight"]}
        total += pts
        factors.append({"factor": FACTOR_LABEL[f], "points": round(pts, 2), "source": CATEGORY_SOURCE, **detail})
    return {"score": round(clamp(total), 2), "start": 100, "factors": factors}


# -------------------------------------------------------------------- Final
def compute_score(n: dict, fmt: str, params: list[dict], has_nss: bool = False,
                  first_whole_grain: bool = False) -> dict:
    overall = overall_score(n, fmt)
    category = category_score(n, params, has_nss, first_whole_grain)
    confirmed = category is not None
    category_value = category["score"] if confirmed else overall["score"]
    exact = clamp(BLEND_W * overall["score"] + (1 - BLEND_W) * category_value)  # modifier = 0 for now
    rounded = int(exact + 0.5)
    return {
        "version": VERSION, "blend_w": BLEND_W,
        "score": rounded, "score_exact": round(exact, 1), "band": band(rounded),
        "overall": overall, "category": category, "modifier": 0,
        "category_confirmed": confirmed,
        "note": None if confirmed else "Category rules not available: Category score = Overall score.",
    }
