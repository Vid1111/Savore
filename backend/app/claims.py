"""Compare two products and apply the claims guard (PRD section 6.7).

"less" or "more" is only said if ALL of these are true:
  1. both products are in the same Savoré category,
  2. the difference is at least 25% (relative to the higher value),
  3. the difference is at least the FSSAI Schedule I "low / source" amount for that nutrient.
Otherwise the row says "similar".
"""

# (nutrient column, label, unit, minimum absolute difference from Schedule I)
ROWS = [
    ("energy_kcal", "Energy", "kcal", 40),
    ("added_sugar_g", "Added sugar", "g", 5),
    ("sat_fat_g", "Saturated fat", "g", 1.5),
    ("total_fat_g", "Total fat", "g", 3),
    ("sodium_mg", "Sodium", "mg", 120),
    ("protein_g", "Protein", "g", 5),
    ("fibre_g", "Fibre", "g", 3),
]
MIN_RELATIVE = 0.25


def compare_rows(a: dict, b: dict, name_a: str, name_b: str, same_category: bool) -> list[dict]:
    rows = []
    for column, label, unit, min_abs in ROWS:
        va, vb = a[column], b[column]
        diff = va - vb
        high = max(va, vb)
        relative = abs(diff) / high if high > 0 else 0
        verdict, statement = "similar", None
        if same_category and relative >= MIN_RELATIVE and abs(diff) >= min_abs:
            verdict = "less" if diff < 0 else "more"
            lo_name, hi_name = (name_a, name_b) if diff < 0 else (name_b, name_a)
            statement = (f"{lo_name} has {relative * 100:.0f}% less {label.lower()} than {hi_name} "
                         f"({abs(diff):.1f} {unit} difference).")
        rows.append({"nutrient": label, "unit": unit, "a": va, "b": vb, "verdict": verdict,
                     "difference": round(diff, 2), "relative_difference": round(relative, 3),
                     "statement": statement})
    return rows
