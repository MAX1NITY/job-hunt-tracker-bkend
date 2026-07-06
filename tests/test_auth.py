"""get_user_id is the dependency that turns a Bearer token into a Supabase
user id (or a 401). It's tested in isolation here, separate from the CRUD
endpoint tests, which override this dependency entirely so they can focus
on request/response shape instead of auth.
"""
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from api.index import get_user_id


def test_get_user_id_returns_id_for_valid_token(fake_supabase):
    fake_supabase.auth.get_user.return_value = MagicMock(user=MagicMock(id="user-123"))
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="valid-token")

    assert get_user_id(creds) == "user-123"
    fake_supabase.auth.get_user.assert_called_once_with("valid-token")


def test_get_user_id_raises_401_for_invalid_token(fake_supabase):
    fake_supabase.auth.get_user.side_effect = Exception("token expired")
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="bad-token")

    with pytest.raises(HTTPException) as exc_info:
        get_user_id(creds)

    assert exc_info.value.status_code == 401


def test_endpoint_rejects_missing_authorization_header(client):
    # No Authorization header at all -> HTTPBearer itself rejects the request
    # before get_user_id ever runs.
    res = client.get("/contacts")
    assert res.status_code == 403  # FastAPI's HTTPBearer default for "missing"


def test_endpoint_rejects_invalid_token(client, fake_supabase):
    fake_supabase.auth.get_user.side_effect = Exception("bad token")
    res = client.get("/contacts", headers={"Authorization": "Bearer bad-token"})
    assert res.status_code == 401
