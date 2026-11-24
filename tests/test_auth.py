"""The access-key check: one shared secret in the X-Access-Key header.
The CRUD endpoint tests send the right key via `auth_client`; the cases here
cover missing, wrong and unconfigured keys, and that a refused request never
reaches the database.
"""


def test_missing_key_is_rejected(client, fake_run):
    res = client.get("/contacts")
    assert res.status_code == 401
    fake_run.assert_not_called()


def test_wrong_key_is_rejected(client, fake_run):
    res = client.get("/contacts", headers={"X-Access-Key": "nope"})
    assert res.status_code == 401
    fake_run.assert_not_called()


def test_correct_key_is_accepted(client, fake_run):
    res = client.get("/contacts", headers={"X-Access-Key": "test-key"})
    assert res.status_code == 200


def test_fails_closed_when_server_key_not_configured(client, fake_run, monkeypatch):
    monkeypatch.delenv("APP_ACCESS_KEY")
    res = client.get("/contacts", headers={"X-Access-Key": "anything"})
    assert res.status_code == 503
    fake_run.assert_not_called()


def test_every_write_endpoint_requires_the_key(client, fake_run):
    body = {"name": "Ada", "company": "X"}
    cid = "11111111-1111-1111-1111-111111111111"
    assert client.post("/contacts", json=body).status_code == 401
    assert client.put(f"/contacts/{cid}", json=body).status_code == 401
    assert client.delete(f"/contacts/{cid}").status_code == 401
    fake_run.assert_not_called()
