"""to_row / to_contact are pure functions (no I/O), so they're tested directly
with plain dicts in, plain dicts out — no client, no app, no mocking needed.
This is the cheapest kind of test to write and the first thing to reach for.
"""
from api.index import to_contact, to_row


def test_to_row_maps_camelcase_to_snake_case():
    row = to_row({
        "name": "Ada Lovelace",
        "company": "Analytical Engines Inc",
        "linkedinUrl": "https://linkedin.com/in/ada",
        "followUpDate": "2026-08-01",
        "status": "Messaged",
    })

    assert row["linkedin_url"] == "https://linkedin.com/in/ada"
    assert row["follow_up_date"] == "2026-08-01"
    assert "linkedinUrl" not in row
    assert "followUpDate" not in row


def test_to_row_empty_follow_up_date_becomes_none():
    row = to_row({"name": "Ada", "company": "X", "followUpDate": ""})
    assert row["follow_up_date"] is None


def test_to_row_has_no_user_or_timestamp_columns():
    row = to_row({"name": "Ada", "company": "X"})
    assert "user_id" not in row
    assert "updated_at" not in row  # the database sets it


def test_to_contact_maps_snake_case_to_camelcase_and_fills_blanks():
    contact = to_contact({
        "id": "abc",
        "name": "Ada",
        "company": "X",
        "status": "Replied",
        "linkedin_url": None,
        "follow_up_date": None,
    })

    assert contact["linkedinUrl"] == ""
    assert contact["followUpDate"] is None
    assert contact["role"] == ""
    assert contact["notes"] == ""


def test_to_contact_stringifies_follow_up_date():
    contact = to_contact({
        "id": "abc", "name": "Ada", "company": "X", "status": "Replied",
        "follow_up_date": "2026-08-01",
    })
    assert contact["followUpDate"] == "2026-08-01"


def test_to_contact_stringifies_uuid_and_isoformats_datetimes():
    from datetime import datetime, timezone
    from uuid import UUID

    contact = to_contact({
        "id": UUID("11111111-1111-1111-1111-111111111111"),
        "name": "Ada", "company": "X", "status": "Replied",
        "created_at": datetime(2026, 7, 1, tzinfo=timezone.utc),
    })
    assert contact["id"] == "11111111-1111-1111-1111-111111111111"
    assert contact["createdAt"].startswith("2026-07-01")
