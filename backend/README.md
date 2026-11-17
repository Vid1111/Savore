# Savoré backend

Python **FastAPI** + **SQLAlchemy** + a real SQL database (SQLite by default, **PostgreSQL** by setting one variable).
It stores products, computes the Savoré Score, compares products and takes user submissions for review.

## Run it (Windows)

```bash
cd backend
python -m venv .venv
.venv\Scripts\pip install -r requirements-dev.txt
.venv\Scripts\python -m uvicorn app.main:app --reload
```

Open **http://127.0.0.1:8000/docs**: every endpoint can be tried in the browser (great for the viva demo).
On first start the tables are created and filled with 8 sample products, 25 ingredients and 22 categories.
Try barcode `8901000000011`.

## A big database: real Indian products

```bash
.venv\Scripts\python -m scripts.import_off --limit 5000
```

Imports real products sold in India from **Open Food Facts** (open data, ODbL licence; 26,000+ available).
Only products with complete nutrition that pass our data rules are kept. They are stored as **unverified**
(PRD section 10), shown with an "Unverified" notice and the Open Food Facts credit, and sorted after verified
products in search. It waits between requests because Open Food Facts limits how fast you can ask, and it can
be stopped and run again (products already added are skipped).

Also: if someone scans a barcode that isn't in our database, the server asks Open Food Facts live, stores the
result as unverified, and returns it (PRD lookup order: our database → Open Food Facts → not found).
Switch this off with `OFF_LOOKUP=0`.

Measured on PostgreSQL with 5,000 products: search 25 to 40 ms, product page 8 ms, compare 13 ms.

## Put it online

See **[DEPLOY.md](DEPLOY.md)**: Supabase (database) + Render (server), step by step. `render.yaml` in the project
root is the Render setup file.

## Endpoints

| Method | Path | What it does |
|---|---|---|
| GET | `/products/by-barcode/{code}` | Product page: nutrition, %RDA, labels, allergens, ingredients, score |
| GET | `/products/search?q=` | Search by name, brand, category or barcode |
| GET | `/products/{id}` · `/products/{id}/score` | Full product · "How was this calculated?" breakdown with sources |
| GET | `/ingredients/{id}` | What an ingredient / INS code is, why it's used, source |
| POST | `/compare` | `{a, b}` → side-by-side rows + claims guard |
| POST | `/submissions` | User adds a product (rules checked immediately) |
| GET / POST | `/submissions`, `/submissions/{id}/verify` | Reviewer queue (needs header `X-Reviewer-Key`) |
| GET | `/categories`, `/health` | Helpers |

## Where things are

| File | Job |
|---|---|
| `app/models.py` | The database tables |
| `app/seed_data.py`, `app/seed.py` | Starting data (categories, scoring rules, ingredients, sample products) |
| `app/scoring.py` | **The score engine**: plain functions, no database |
| `app/claims.py` | Compare + claims guard (25% and Schedule I rule) |
| `app/validation.py` | Rules that block bad submissions |
| `app/main.py` | The API routes |
| `app/off.py`, `scripts/import_off.py` | Open Food Facts mapping, live barcode lookup, bulk importer |
| `app/catalog.py`, `app/ingredients.py` | Build a product row; split and match ingredient lists |
| `tests/` | 39 automatic tests |

## Tables (8 core + scoring rules)

`categories` → `products` → `nutrition_facts` · `product_ingredients` → `ingredients` · `product_allergens` → `allergens` ·
`category_parameters` (scoring rules per category, stored as data) · `submissions` (waiting for review).

## Connect the Flutter app

The app talks to the **deployed server** (`https://savore-api.onrender.com`) by default, so `flutter run` just works.
To use a server on your own PC instead, set `API_URL`:

- **Phone with USB cable:** `adb reverse tcp:8000 tcp:8000` then `flutter run --dart-define=API_URL=http://127.0.0.1:8000`
- **Phone on the same Wi-Fi:** `flutter run --dart-define=API_URL=http://YOUR-PC-IP:8000`
- **Android emulator:** `flutter run --dart-define=API_URL=http://10.0.2.2:8000`

## PostgreSQL

Set `DATABASE_URL` to any PostgreSQL URL (for example Supabase) before starting the server or the importer.
The tables and sample data are created automatically and no code changes. Without it, a local SQLite file is used.

## Tests

```bash
.venv\Scripts\python -m pytest
```

To run the same tests on PostgreSQL, point `TEST_DATABASE_URL` at an **empty** database first
(`set TEST_DATABASE_URL=postgresql://postgres@127.0.0.1:5432/savore_test`). All tests pass on SQLite and on PostgreSQL 18.

Includes the PRD's worked example (Overall 37.2, Category 55.5, score 46) and the stability checks S1 to S3.

## Viva notes

- **Why FastAPI?** Same language as OCR/AI later, automatic `/docs` page, validation built in.
- **Why SQLite by default?** Zero setup for development; the code is SQLAlchemy, so PostgreSQL is one environment variable.
- **How is the score computed?** `0.5 × Overall + 0.5 × Category`. Overall: start at 80, straight-line penalties/bonuses (FSSAI values). Category: per-category curves (WHO SEARO thresholds) read from the `category_parameters` table.
- **Verified:** the engine reproduces the PRD worked example exactly.
- **A finding from our own tests:** for the Orange Fizz sample, a 10% sugar change moves the score 3.2 points, just over the PRD's 3-point goal (S1). It comes from the PRD's C12 numbers (sugar weight 50) and is recorded in `tests/test_scoring.py`.
- **Where does the big database come from?** Real Indian products from Open Food Facts (open data, ODbL). We keep only
  products with complete nutrition that pass our own data rules, store them as *unverified* and credit the source. We
  did not invent any product data.
- **Honest limits:**
  - Imported products are unverified: their data may contain mistakes until a reviewer checks them against the pack.
  - Open Food Facts doesn't always give a serving size, so "per serve" falls back to 100 g / 100 ml.
  - Scoring rules exist for 9 categories (C1, C3, C4, C5, C6, C7, C9, C12, C13); others use the Overall score and say so.
  - WHO SEARO numbers still need checking against the original 2017 document (the PRD says so too).
  - Category caps (C) are team-proposed until each category has 20 verified products.
  - Ingredient modifier, alternatives, OCR, Hindi and accounts are not built.
  - The reviewer queue uses one shared key, fine for the course, not for production.
