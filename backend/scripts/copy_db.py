"""Copy the local SQLite database into another database, e.g. your Supabase PostgreSQL.

    set DATABASE_URL=postgresql://user:password@host:5432/postgres      (the TARGET)
    python -m scripts.copy_db                                           (copies ./savore.db)

It creates the tables in the target, copies every table in the right order, and fixes the id counters
so new products added later get fresh ids. It refuses to run if the target already has products.
"""
import argparse
import os
import sys

from sqlalchemy import create_engine, func, select, text

from app.db import normalize_url
from app.models import Base

CHUNK = 500


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--source", default="sqlite:///./savore.db", help="database to copy FROM")
    args = ap.parse_args()

    target_url = os.environ.get("DATABASE_URL", "")
    if not target_url or target_url.startswith("sqlite"):
        sys.exit("Set DATABASE_URL to the PostgreSQL database you want to copy INTO.")

    src = create_engine(args.source)
    dst = create_engine(normalize_url(target_url), pool_pre_ping=True)

    Base.metadata.create_all(dst)
    products = Base.metadata.tables["products"]
    with dst.connect() as conn:
        existing = conn.execute(select(func.count()).select_from(products)).scalar()
    if existing:
        sys.exit(f"The target already has {existing} products. Nothing was copied.")

    tables = Base.metadata.sorted_tables  # parents before children
    with src.connect() as s, dst.begin() as d:  # one transaction: all or nothing
        for t in tables:
            rows = [dict(r._mapping) for r in s.execute(select(t))]
            for i in range(0, len(rows), CHUNK):
                d.execute(t.insert(), rows[i:i + CHUNK])
            print(f"{t.name:22} {len(rows):6} rows", flush=True)
        for t in tables:  # let the id counters continue after the copied ids
            if "id" in t.c:
                d.execute(text(
                    f"select setval(pg_get_serial_sequence('{t.name}', 'id'), "
                    f"coalesce((select max(id) from {t.name}), 1), (select count(*) > 0 from {t.name}))"))
    print("Done.")


if __name__ == "__main__":
    main()
