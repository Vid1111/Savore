"""Helpers for turning an ingredient list printed on a label into rows of our reference list."""
import re

from .models import Ingredient


def split_ingredients(text: str, max_items: int = 40) -> list[str]:
    """Split on commas, but not commas inside brackets: 'Flour (wheat, salt), Sugar' -> 2 items."""
    parts, depth, current = [], 0, ""
    for ch in text.replace("\n", " "):
        if ch in "([{":
            depth += 1
        elif ch in ")]}":
            depth = max(0, depth - 1)
        if ch in ",;" and depth == 0:
            parts.append(current)
            current = ""
        else:
            current += ch
    parts.append(current)
    cleaned = [re.sub(r"\s+", " ", p).strip(" .:*") for p in parts]
    return [p for p in cleaned if p][:max_items]


def match_ingredient(known: list[Ingredient], text: str) -> Ingredient | None:
    """Find an ingredient in our reference list by INS code or name."""
    low = text.strip().lower()
    m = re.search(r"ins\s*([0-9]+[a-z]?)", low)
    for i in known:
        if m and i.ins_code and i.ins_code.lower().replace(" ", "").startswith("ins" + m.group(1)):
            return i
        if not m and (i.name.lower() == low or (len(low) >= 4 and low in i.name.lower())):
            return i
    return None
