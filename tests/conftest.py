import os
from unittest.mock import MagicMock

import pytest

# Endpoints read APP_ACCESS_KEY at request time; DATABASE_URL is only read
# inside run(), which tests replace, so no database is ever contacted.
os.environ["APP_ACCESS_KEY"] = "test-key"
os.environ.setdefault("DATABASE_URL", "postgresql://user:pw@localhost/none")
os.environ.setdefault("ALLOWED_ORIGINS", "http://localhost:5173")

from fastapi.testclient import TestClient

from api import index as api_index

KEY = {"X-Access-Key": "test-key"}


@pytest.fixture
def fake_run(monkeypatch):
    """Replace api.index.run (the single DB seam) with a MagicMock so tests
    never touch a database. Configure fake_run.return_value per test and
    inspect fake_run.call_args for the SQL and params that were sent.
    """
    mock = MagicMock(return_value=[])
    monkeypatch.setattr(api_index, "run", mock)
    return mock


@pytest.fixture
def client(fake_run):
    return TestClient(api_index.app)


@pytest.fixture
def auth_client(client):
    """A client that sends the correct access key on every request."""
    client.headers.update(KEY)
    return client
