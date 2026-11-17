"""Checks run on every submitted product (PRD section 10). A broken rule blocks the submission."""


def check_nutrition(n: dict, fssai_licence_no: str | None = None) -> list[str]:
    errors = []
    added = n.get("added_sugar_g")
    if added is not None and added > n["total_sugar_g"]:
        errors.append("Added sugar cannot be more than total sugar.")
    if n["total_sugar_g"] > n["carbohydrate_g"]:
        errors.append("Total sugar cannot be more than carbohydrate.")
    if n["sat_fat_g"] > n["total_fat_g"]:
        errors.append("Saturated fat cannot be more than total fat.")
    if n.get("trans_fat_g", 0) > n["total_fat_g"]:
        errors.append("Trans fat cannot be more than total fat.")
    if n["protein_g"] + n["carbohydrate_g"] + n["total_fat_g"] > 100:
        errors.append("Protein + carbohydrate + fat cannot be more than 100 per 100 g.")
    expected = 4 * n["protein_g"] + 4 * n["carbohydrate_g"] + 9 * n["total_fat_g"]
    if expected > 0 and abs(n["energy_kcal"] - expected) > 0.2 * expected:
        errors.append(f"Energy ({n['energy_kcal']} kcal) does not match 4P + 4C + 9F "
                      f"(about {expected:.0f} kcal, allowed +/-20%).")
    if fssai_licence_no and not (fssai_licence_no.isdigit() and len(fssai_licence_no) == 14):
        errors.append("FSSAI licence number must be exactly 14 digits.")
    return errors
