"""Import real Indian products from Open Food Facts into the database.

    python -m scripts.import_off --limit 5000

It uses DATABASE_URL like the API does: local SQLite by default, or set DATABASE_URL to your
Supabase connection string to fill the online database. Safe to run again: barcodes already in the
database are skipped, so you can stop (Ctrl+C) and continue later with --start-page.

Open Food Facts allows about 10 search requests a minute, so the script waits between pages.
Products are stored as UNVERIFIED (Open Food Facts data, ODbL licence).
"""
import argparse
import time

from sqlalchemy import select

from app import off
from app.catalog import product_from_payload
from app.db import SessionLocal, engine
from app.models import Allergen, Base, Category, Ingredient, Product
from app.seed import seed_if_empty


def fetch_patiently(page: int, cooldown_minutes: int = 5, attempts: int = 8) -> list[dict]:
    """Open Food Facts blocks us for a while if we ask too fast: wait and try again instead of crashing."""
    for attempt in range(1, attempts + 1):
        try:
            return off.fetch_page(page)
        except RuntimeError:
            if attempt == attempts:
                raise
            print(f"Open Food Facts is busy or limiting us. Waiting {cooldown_minutes} minutes "
                  f"(try {attempt}/{attempts})...", flush=True)
            time.sleep(cooldown_minutes * 60)
    return []


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--limit", type=int, default=5000, help="stop after adding this many products")
    ap.add_argument("--start-page", type=int, default=1, help="Open Food Facts page to start from")
    ap.add_argument("--max-pages", type=int, default=400, help="safety limit on pages fetched")
    ap.add_argument("--delay", type=float, default=12.0, help="seconds to wait between pages")
    args = ap.parse_args()

    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        seed_if_empty(db)
        known = list(db.scalars(select(Ingredient)))
        cats = {c.code: c for c in db.scalars(select(Category))}
        allergens = {a.name: a for a in db.scalars(select(Allergen))}
        existing = set(db.scalars(select(Product.barcode)))
        print(f"Database has {len(existing)} products. Importing up to {args.limit} more...")

        added = duplicates = rejected = 0
        page = args.start_page
        while added < args.limit and page < args.start_page + args.max_pages:
            raws = fetch_patiently(page)
            if not raws:
                print("No more products from Open Food Facts.")
                break
            for raw in raws:
                payload = off.map_product(raw)
                if payload is None:
                    rejected += 1  # incomplete nutrition, or fails our data rules
                elif payload["barcode"] in existing:
                    duplicates += 1
                else:
                    db.add(product_from_payload(db, payload, verified=False, source="off",
                                                known=known, cats=cats, allergens=allergens))
                    existing.add(payload["barcode"])
                    added += 1
                    if added >= args.limit:
                        break
            db.commit()
            print(f"page {page}: added {added} | skipped {duplicates} already present, "
                  f"{rejected} incomplete or invalid", flush=True)
            page += 1
            time.sleep(args.delay)
        print(f"Done. Added {added} products. Resume later with --start-page {page}.")


if __name__ == "__main__":
    main()
