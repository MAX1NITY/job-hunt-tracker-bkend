import os
from unittest.mock import MagicMock

import pytest

# api/index.py reads these at import time (os.environ["SUPABASE_URL"], etc.),
# so they must exist before the module is ever imported.
os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
# The supabase client validates this looks like a JWT (header.payload.signature)
# before it'll even construct a client, so a plain string won't do.
os.environ.setdefault("SUPABASE_SERVICE_KEY", "fake.fake.fake")
os.environ.setdefault("ALLOWED_ORIGINS", "http://localhost:5173")

from fastapi.testclient import TestClient

from api import index as api_index


@pytest.fixture
def fake_supabase(monkeypatch):
    """Replace the module-level `supabase` client with a MagicMock so tests
    never touch the network. Each test gets a fresh mock and configures the
    query chain it needs (e.g. fake_supabase.table.return_value.select...).
    """
    mock = MagicMock()
    monkeypatch.setattr(api_index, "supabase", mock)
    return mock


@pytest.fixture
def client(fake_supabase):
    return TestClient(api_index.app)


@pytest.fixture
def auth_client(client):
    """A client where the auth dependency is overridden, so endpoint tests
    don't need a real (or fake) JWT — only the auth-specific tests do.
    """
    api_index.app.dependency_overrides[api_index.get_user_id] = lambda: "user-123"
    yield client
    api_index.app.dependency_overrides.clear()
