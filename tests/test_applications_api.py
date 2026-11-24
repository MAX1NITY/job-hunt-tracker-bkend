"""Applications CRUD: routing, validation and SQL params, with fake_run as the DB."""

AID = "22222222-2222-2222-2222-222222222222"
CID = "11111111-1111-1111-1111-111111111111"

ROW = {
    "id": AID, "company": "Canva", "role": "Frontend Engineer",
    "job_url": "https://example.com/job", "applied_date": "2026-11-20",
    "status": "Applied", "source": "Referral", "contact_id": CID,
    "next_step": "Follow up", "next_step_date": None, "work_mode": "Hybrid",
    "job_description": "", "notes": "", "created_at": "2026-11-20T00:00:00",
    "updated_at": "2026-11-20T00:00:00",
}


def test_list_maps_rows(auth_client, fake_run):
    fake_run.return_value = [ROW]
    body = auth_client.get("/applications").json()
    assert body[0]["contactId"] == CID
    assert body[0]["jobUrl"] == "https://example.com/job"
    assert body[0]["nextStepDate"] is None


def test_create_sends_blank_optionals_as_null(auth_client, fake_run):
    fake_run.return_value = [ROW]
    res = auth_client.post("/applications", json={
        "company": "Canva", "role": "Frontend Engineer",
        "contactId": "", "appliedDate": "", "workMode": "",
    })
    assert res.status_code == 201
    sql, params = fake_run.call_args.args
    assert sql.startswith("INSERT INTO applications")
    assert params["contact_id"] is None and params["work_mode"] is None
    assert params["status"] == "Applied"


def test_create_requires_role_and_valid_status(auth_client, fake_run):
    assert auth_client.post("/applications", json={"company": "Canva"}).status_code == 422
    assert auth_client.post("/applications", json={"company": "C", "role": "R", "status": "Nope"}).status_code == 422
    fake_run.assert_not_called()


def test_update_404_and_success(auth_client, fake_run):
    fake_run.return_value = []
    assert auth_client.put(f"/applications/{AID}", json={"company": "C", "role": "R"}).status_code == 404
    fake_run.return_value = [ROW]
    res = auth_client.put(f"/applications/{AID}", json={"company": "C", "role": "R", "contactId": CID})
    assert res.status_code == 200
    sql, params = fake_run.call_args.args
    assert "updated_at = now()" in sql and str(params["contact_id"]) == CID


def test_delete_and_auth(client, auth_client, fake_run):
    assert auth_client.delete(f"/applications/{AID}").status_code == 204
    assert client.get("/applications", headers={"X-Access-Key": "wrong"}).status_code == 401
