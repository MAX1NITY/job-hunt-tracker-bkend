import os
from datetime import date, datetime
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from supabase import create_client

load_dotenv()

app = FastAPI()

_raw_origins = os.getenv("ALLOWED_ORIGINS", "*")
_origins = [o.strip() for o in _raw_origins.split(",") if o.strip()] or ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

supabase = create_client(
    os.environ["SUPABASE_URL"],
    os.environ["SUPABASE_SERVICE_KEY"],
)

TABLE = "contacts"


class ContactIn(BaseModel):
    name: str
    role: Optional[str] = None
    company: str
    linkedinUrl: Optional[str] = None
    status: str = "Not Contacted"
    followUpDate: Optional[str] = None
    notes: Optional[str] = None


def to_row(data: dict) -> dict:
    """camelCase → snake_case for Supabase."""
    return {
        "name": data.get("name"),
        "role": data.get("role"),
        "company": data.get("company"),
        "linkedin_url": data.get("linkedinUrl"),
        "status": data.get("status"),
        "follow_up_date": data.get("followUpDate") or None,
        "notes": data.get("notes"),
        "updated_at": datetime.utcnow().isoformat(),
    }


def to_contact(row: dict) -> dict:
    """snake_case → camelCase for the frontend."""
    return {
        "id": row["id"],
        "name": row["name"],
        "role": row.get("role") or "",
        "company": row["company"],
        "linkedinUrl": row.get("linkedin_url") or "",
        "status": row["status"],
        "followUpDate": str(row["follow_up_date"]) if row.get("follow_up_date") else None,
        "notes": row.get("notes") or "",
        "createdAt": row.get("created_at"),
        "updatedAt": row.get("updated_at"),
    }


@app.get("/contacts")
def get_contacts():
    res = supabase.table(TABLE).select("*").order("created_at", desc=True).execute()
    return [to_contact(r) for r in res.data]


@app.post("/contacts", status_code=201)
def create_contact(body: ContactIn):
    row = to_row(body.model_dump())
    row.pop("updated_at", None)  # let DB default handle created_at + updated_at
    res = supabase.table(TABLE).insert(row).execute()
    return to_contact(res.data[0])


@app.put("/contacts/{contact_id}")
def update_contact(contact_id: str, body: ContactIn):
    row = to_row(body.model_dump())
    res = supabase.table(TABLE).update(row).eq("id", contact_id).execute()
    if not res.data:
        raise HTTPException(status_code=404, detail="Contact not found")
    return to_contact(res.data[0])


@app.delete("/contacts/{contact_id}", status_code=204)
def delete_contact(contact_id: str):
    supabase.table(TABLE).delete().eq("id", contact_id).execute()
