"""ContactIn is the request-body model for POST/PUT. Pydantic rejects bad
payloads before the handler body ever runs, so these tests just check the
422 boundary — valid input still reaches the (mocked) database untouched.
"""


def test_rejects_blank_name(auth_client):
    res = auth_client.post("/contacts", json={"name": "   ", "company": "Acme"})
    assert res.status_code == 422


def test_rejects_invalid_email(auth_client):
    res = auth_client.post("/contacts", json={"name": "Ada", "company": "Acme", "email": "not-an-email"})
    assert res.status_code == 422


def test_accepts_blank_email_as_unset(auth_client, fake_supabase):
    fake_supabase.table.return_value.insert.return_value.execute.return_value.data = [{
        "id": "1", "name": "Ada", "company": "Acme", "status": "Not Contacted",
    }]

    res = auth_client.post("/contacts", json={"name": "Ada", "company": "Acme", "email": ""})

    assert res.status_code == 201
    inserted_row = fake_supabase.table.return_value.insert.call_args[0][0]
    assert inserted_row["email"] is None


def test_rejects_invalid_follow_up_date(auth_client):
    res = auth_client.post(
        "/contacts", json={"name": "Ada", "company": "Acme", "followUpDate": "not-a-date"}
    )
    assert res.status_code == 422


def test_rejects_unknown_status(auth_client):
    res = auth_client.post("/contacts", json={"name": "Ada", "company": "Acme", "status": "Ghosted"})
    assert res.status_code == 422


def test_accepts_valid_follow_up_date_as_iso_string(auth_client, fake_supabase):
    fake_supabase.table.return_value.insert.return_value.execute.return_value.data = [{
        "id": "1", "name": "Ada", "company": "Acme", "status": "Not Contacted",
    }]

    res = auth_client.post(
        "/contacts", json={"name": "Ada", "company": "Acme", "followUpDate": "2026-08-01"}
    )

    assert res.status_code == 201
    inserted_row = fake_supabase.table.return_value.insert.call_args[0][0]
    assert inserted_row["follow_up_date"] == "2026-08-01"
