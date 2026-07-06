"""CRUD endpoint tests. `auth_client` overrides get_user_id so every request
is treated as "user-123" without needing a real JWT — these tests are about
routing, status codes, and payload shape, not auth (see test_auth.py for that).
"""

SAMPLE_ROW = {
    "id": "row-1",
    "name": "Ada Lovelace",
    "role": "Engineering Manager",
    "company": "Analytical Engines Inc",
    "email": "ada@example.com",
    "linkedin_url": "https://linkedin.com/in/ada",
    "status": "Messaged",
    "follow_up_date": None,
    "notes": "",
    "created_at": "2026-07-01T00:00:00",
    "updated_at": "2026-07-01T00:00:00",
}


def test_get_contacts_returns_mapped_list(auth_client, fake_supabase):
    query = fake_supabase.table.return_value.select.return_value.eq.return_value.order.return_value
    query.execute.return_value.data = [SAMPLE_ROW]

    res = auth_client.get("/contacts")

    assert res.status_code == 200
    body = res.json()
    assert body[0]["linkedinUrl"] == "https://linkedin.com/in/ada"
    fake_supabase.table.return_value.select.return_value.eq.assert_called_with("user_id", "user-123")


def test_create_contact_returns_201_with_created_row(auth_client, fake_supabase):
    fake_supabase.table.return_value.insert.return_value.execute.return_value.data = [SAMPLE_ROW]

    res = auth_client.post("/contacts", json={"name": "Ada Lovelace", "company": "Analytical Engines Inc"})

    assert res.status_code == 201
    assert res.json()["name"] == "Ada Lovelace"

    inserted_row = fake_supabase.table.return_value.insert.call_args[0][0]
    assert inserted_row["user_id"] == "user-123"
    assert "updated_at" not in inserted_row  # stripped before insert; DB sets it


def test_create_contact_requires_name_and_company(auth_client):
    res = auth_client.post("/contacts", json={"name": "Ada Lovelace"})
    assert res.status_code == 422  # pydantic: `company` is required


def test_update_contact_returns_404_when_not_found_or_not_owned(auth_client, fake_supabase):
    fake_supabase.table.return_value.update.return_value.eq.return_value.eq.return_value.execute.return_value.data = []

    res = auth_client.put("/contacts/does-not-exist", json={"name": "Ada", "company": "X"})

    assert res.status_code == 404


def test_update_contact_scopes_to_owning_user(auth_client, fake_supabase):
    chain = fake_supabase.table.return_value.update.return_value.eq.return_value.eq.return_value
    chain.execute.return_value.data = [SAMPLE_ROW]

    res = auth_client.put("/contacts/row-1", json={"name": "Ada Lovelace", "company": "Analytical Engines Inc"})

    assert res.status_code == 200
    eq_calls = fake_supabase.table.return_value.update.return_value.eq.call_args_list
    assert eq_calls[0].args == ("id", "row-1")
    # the second .eq(...) call is what enforces "only your own rows"
    second_eq = fake_supabase.table.return_value.update.return_value.eq.return_value.eq
    second_eq.assert_called_with("user_id", "user-123")


def test_delete_contact_returns_204(auth_client, fake_supabase):
    res = auth_client.delete("/contacts/row-1")
    assert res.status_code == 204
    assert res.content == b""
