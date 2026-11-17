"""Database connection.

By default the app uses a local SQLite file (no install needed).
To use PostgreSQL instead, set the DATABASE_URL environment variable, e.g.
    DATABASE_URL=postgresql://user:password@host:5432/dbname
Nothing else in the code changes.
"""
import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./savore.db")

# Hosts hand out "postgres://..." or "postgresql://..." URLs. Name the driver we install (psycopg2)
# so any of them works.
for prefix in ("postgres://", "postgresql://"):
    if DATABASE_URL.startswith(prefix):
        DATABASE_URL = "postgresql+psycopg2://" + DATABASE_URL[len(prefix):]

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
# pool_pre_ping: reconnect quietly if the hosted database closed an idle connection.
engine = create_engine(DATABASE_URL, connect_args=connect_args, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False)


def get_db():
    """One database session per request, closed afterwards."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
