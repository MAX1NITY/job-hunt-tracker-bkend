"""CRUD endpoint tests. `auth_client` sends the right access key, and
`fake_run` stands in for the database, so these tests are about routing,
status codes, payload shape and the SQL parameters -- not Postgres itself.
"""

CID = "11111111-1111-1111-1111-111111111111"

SAMPLE_ROW = {
    "id": CID,
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


def test_get_contacts_returns_mapped_list(auth_client, fake_run):
    fake_run.return_value = [SAMPLE_ROW]

    res = auth_client.get("/contacts")

    assert res.status_code == 200
    body = res.json()
    assert body[0]["linkedinUrl"] == "https://linkedin.com/in/ada"
    assert body[0]["id"] == CID
    assert "ORDER BY created_at DESC" in fake_run.call_args.args[0]


def test_create_contact_returns_201_with_created_row(auth_client, fake_run):
    fake_run.return_value = [SAMPLE_ROW]

    res = auth_client.post("/contacts", json={"name": "Ada Lovelace", "company": "Analytical Engines Inc"})

    assert res.status_code == 201
    assert res.json()["name"] == "Ada Lovelace"

    sql, params = fake_run.call_args.args
    assert sql.startswith("INSERT INTO contacts")
    assert params["name"] == "Ada Lovelace"
    assert "user_id" not in params  # single-user app: no per-user column


def test_create_contact_requires_name_and_company(auth_client, fake_run):
    res = auth_client.post("/contacts", json={"name": "Ada Lovelace"})
    assert res.status_code == 422  # pydantic: `company` is required
    fake_run.assert_not_called()


def test_update_contact_returns_404_when_not_found(auth_client, fake_run):
    fake_run.return_value = []

    res = auth_client.put(f"/contacts/{CID}", json={"name": "Ada", "company": "X"})

    assert res.status_code == 404


def test_update_contact_returns_updated_row(auth_client, fake_run):
    fake_run.return_value = [SAMPLE_ROW]

    res = auth_client.put(f"/contacts/{CID}", json={"name": "Ada Lovelace", "company": "Analytical Engines Inc"})

    assert res.status_code == 200
    sql, params = fake_run.call_args.args
    assert sql.startswith("UPDATE contacts")
    assert "updated_at = now()" in sql
    assert str(params["id"]) == CID


def test_update_rejects_malformed_id(auth_client, fake_run):
    res = auth_client.put("/contacts/not-a-uuid", json={"name": "Ada", "company": "X"})
    assert res.status_code == 422
    fake_run.assert_not_called()


def test_delete_contact_returns_204(auth_client, fake_run):
    res = auth_client.delete(f"/contacts/{CID}")
    assert res.status_code == 204
    assert res.content == b""
    sql, params = fake_run.call_args.args
    assert sql.startswith("DELETE FROM contacts")
    assert str(params[0]) == CID
