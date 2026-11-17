import os
import tempfile

# Use a throwaway database for tests, never the real one.
# To test against PostgreSQL instead, set TEST_DATABASE_URL (it must be an EMPTY database).
os.environ["DATABASE_URL"] = os.getenv("TEST_DATABASE_URL") or f"sqlite:///{tempfile.mkdtemp()}/test.db"
os.environ["REVIEWER_KEY"] = "test-key"
os.environ["OFF_LOOKUP"] = "0"  # tests never call the internet (the live-lookup test switches it on itself)

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:  # starting the client creates the tables and seeds them
        yield c
