import hmac
import os
from datetime import date, datetime
from typing import Literal, Optional
from uuid import UUID

import psycopg
import sentry_sdk
from dotenv import load_dotenv
from fastapi import FastAPI, Header, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from psycopg.rows import dict_row
from pydantic import BaseModel, EmailStr, field_validator

load_dotenv()

# No-op until SENTRY_DSN is set (e.g. as a Vercel env var) -- keeps local dev,
# tests, and CI free of any Sentry network calls or account requirement.
if sentry_dsn := os.getenv("SENTRY_DSN"):
    sentry_sdk.init(dsn=sentry_dsn, traces_sample_rate=0.1)

app = FastAPI()

_raw_origins = os.getenv("ALLOWED_ORIGINS", "*")
_origins = [o.strip() for o in _raw_origins.split(",") if o.strip()] or ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

TABLE = "contacts"
COLUMNS = (
    "id, name, role, company, email, linkedin_url, status, "
    "follow_up_date, notes, created_at, updated_at"
)


def run(sql: str, params=None) -> list:
    """Run one statement against Postgres (Neon) and return rows as dicts.

    One short-lived connection per call: right for serverless, where there is
    no long-lived process to hold a pool. Use Neon's pooled connection string.
    The connection context manager commits on success and closes on exit.
    """
    with psycopg.connect(os.environ["DATABASE_URL"], row_factory=dict_row) as conn:
        cur = conn.execute(sql, params)
        return cur.fetchall() if cur.description else []


def require_access_key(x_access_key: Optional[str] = Header(default=None)) -> None:
    """Single-user app: no accounts, just one shared secret.

    Fails closed -- if APP_ACCESS_KEY isn't configured, every request is
    refused rather than silently leaving the API open.
    """
    expected = os.environ.get("APP_ACCESS_KEY", "")
    if not expected:
        raise HTTPException(status_code=503, detail="Server access key is not configured")
    if not x_access_key or not hmac.compare_digest(x_access_key, expected):
        raise HTTPException(status_code=401, detail="Invalid or missing access key")


STATUSES = ("Not Contacted", "Messaged", "Replied", "Interview", "Closed")


class ContactIn(BaseModel):
    name: str
    role: Optional[str] = None
    company: str
    email: Optional[EmailStr] = None
    linkedinUrl: Optional[str] = None
    status: Literal[STATUSES] = "Not Contacted"
    followUpDate: Optional[date] = None
    notes: Optional[str] = None

    @field_validator("name", "company")
    @classmethod
    def not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("must not be blank")
        return v.strip()

    @field_validator("email", "followUpDate", mode="before")
    @classmethod
    def blank_string_to_none(cls, v):
        # The frontend sends "" for unset optional fields; EmailStr/date
        # reject "" outright, so treat blank the same as omitted.
        return v or None


def to_row(data: dict) -> dict:
    return {
        "name": data.get("name"),
        "role": data.get("role"),
        "company": data.get("company"),
        "email": data.get("email"),
        "linkedin_url": data.get("linkedinUrl"),
        "status": data.get("status"),
        "follow_up_date": data.get("followUpDate") or None,
        "notes": data.get("notes"),
    }


def _iso(v):
    return v.isoformat() if isinstance(v, (datetime, date)) else v


def to_contact(row: dict) -> dict:
    return {
        "id": str(row["id"]),
        "name": row["name"],
        "role": row.get("role") or "",
        "company": row["company"],
        "email": row.get("email") or "",
        "linkedinUrl": row.get("linkedin_url") or "",
        "status": row["status"],
        "followUpDate": str(row["follow_up_date"]) if row.get("follow_up_date") else None,
        "notes": row.get("notes") or "",
        "createdAt": _iso(row.get("created_at")),
        "updatedAt": _iso(row.get("updated_at")),
    }


@app.get("/contacts", dependencies=[Depends(require_access_key)])
def get_contacts():
    rows = run(f"SELECT {COLUMNS} FROM {TABLE} ORDER BY created_at DESC")
    return [to_contact(r) for r in rows]


@app.post("/contacts", status_code=201, dependencies=[Depends(require_access_key)])
def create_contact(body: ContactIn):
    row = to_row(body.model_dump(mode="json"))
    rows = run(
        f"INSERT INTO {TABLE} (name, role, company, email, linkedin_url, status, follow_up_date, notes) "
        "VALUES (%(name)s, %(role)s, %(company)s, %(email)s, %(linkedin_url)s, %(status)s, "
        f"%(follow_up_date)s, %(notes)s) RETURNING {COLUMNS}",
        row,
    )
    return to_contact(rows[0])


@app.put("/contacts/{contact_id}", dependencies=[Depends(require_access_key)])
def update_contact(contact_id: UUID, body: ContactIn):
    row = to_row(body.model_dump(mode="json"))
    row["id"] = contact_id
    rows = run(
        f"UPDATE {TABLE} SET name = %(name)s, role = %(role)s, company = %(company)s, "
        "email = %(email)s, linkedin_url = %(linkedin_url)s, status = %(status)s, "
        "follow_up_date = %(follow_up_date)s, notes = %(notes)s, updated_at = now() "
        f"WHERE id = %(id)s RETURNING {COLUMNS}",
        row,
    )
    if not rows:
        raise HTTPException(status_code=404, detail="Contact not found")
    return to_contact(rows[0])


@app.delete("/contacts/{contact_id}", status_code=204, dependencies=[Depends(require_access_key)])
def delete_contact(contact_id: UUID):
    run(f"DELETE FROM {TABLE} WHERE id = %s", (contact_id,))
