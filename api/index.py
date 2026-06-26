import os
from datetime import datetime
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
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
security = HTTPBearer()


def get_user_id(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    try:
        response = supabase.auth.get_user(credentials.credentials)
        return response.user.id
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")


class ContactIn(BaseModel):
    name: str
    role: Optional[str] = None
    company: str
    email: Optional[str] = None
    linkedinUrl: Optional[str] = None
    status: str = "Not Contacted"
    followUpDate: Optional[str] = None
    notes: Optional[str] = None


def to_row(data: dict, user_id: str = None) -> dict:
    row = {
        "name": data.get("name"),
        "role": data.get("role"),
        "company": data.get("company"),
        "email": data.get("email"),
        "linkedin_url": data.get("linkedinUrl"),
        "status": data.get("status"),
        "follow_up_date": data.get("followUpDate") or None,
        "notes": data.get("notes"),
        "updated_at": datetime.utcnow().isoformat(),
    }
    if user_id:
        row["user_id"] = user_id
    return row


def to_contact(row: dict) -> dict:
    return {
        "id": row["id"],
        "name": row["name"],
        "role": row.get("role") or "",
        "company": row["company"],
        "email": row.get("email") or "",
        "linkedinUrl": row.get("linkedin_url") or "",
        "status": row["status"],
        "followUpDate": str(row["follow_up_date"]) if row.get("follow_up_date") else None,
        "notes": row.get("notes") or "",
        "createdAt": row.get("created_at"),
        "updatedAt": row.get("updated_at"),
    }


@app.get("/contacts")
def get_contacts(user_id: str = Depends(get_user_id)):
    res = (
        supabase.table(TABLE)
        .select("*")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .execute()
    )
    return [to_contact(r) for r in res.data]


@app.post("/contacts", status_code=201)
def create_contact(body: ContactIn, user_id: str = Depends(get_user_id)):
    row = to_row(body.model_dump(), user_id=user_id)
    row.pop("updated_at", None)
    res = supabase.table(TABLE).insert(row).execute()
    return to_contact(res.data[0])


@app.put("/contacts/{contact_id}")
def update_contact(contact_id: str, body: ContactIn, user_id: str = Depends(get_user_id)):
    row = to_row(body.model_dump())
    res = (
        supabase.table(TABLE)
        .update(row)
        .eq("id", contact_id)
        .eq("user_id", user_id)
        .execute()
    )
    if not res.data:
        raise HTTPException(status_code=404, detail="Contact not found")
    return to_contact(res.data[0])


@app.delete("/contacts/{contact_id}", status_code=204)
def delete_contact(contact_id: str, user_id: str = Depends(get_user_id)):
    supabase.table(TABLE).delete().eq("id", contact_id).eq("user_id", user_id).execute()
