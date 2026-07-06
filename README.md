# Job Hunt Tracker — Backend

FastAPI backend for the [Job Hunt Tracker](https://github.com/MAX1NITY/job-hunt-tracker-frntend)
frontend. Exposes CRUD endpoints over a `contacts` table in Supabase
(Postgres), with every request authenticated via a Supabase-issued JWT.

**Live:** https://job-hunt-tracker-bkend.vercel.app

For the reasoning behind the auth model, RLS, and CORS setup, see the
[case study](https://github.com/MAX1NITY/job-hunt-tracker-frntend/blob/main/docs/case-study.md)
in the frontend repo (it covers the full-stack picture; this README covers
running and testing this service specifically).

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements-dev.txt

cp .env.example .env             # fill in your Supabase project's values
uvicorn api.index:app --reload
```

## Environment Variables

```
SUPABASE_URL=
SUPABASE_SERVICE_KEY=            # service_role key — bypasses RLS, server-only, never expose to a client
ALLOWED_ORIGINS=                 # comma-separated, or * to allow any origin
SENTRY_DSN=                      # optional — leave blank to disable error monitoring
```

## Testing

```bash
pytest -v
```

Tests mock the Supabase client entirely (`tests/conftest.py`), so they run
with no network access and no real database. They're split by concern:

- `tests/test_conversions.py` — pure `to_row`/`to_contact` mapping functions
- `tests/test_auth.py` — the JWT-to-user-id dependency, valid and invalid tokens
- `tests/test_contacts_api.py` — CRUD endpoints, with auth mocked via
  `app.dependency_overrides` so these tests focus on request/response shape
  and on the `user_id` scoping that keeps users' data separate
- `tests/test_validation.py` — the pydantic validators on `ContactIn`
  (blank names, malformed email/date, unknown status values)

CI (`.github/workflows/ci.yml`) runs this suite on every push and PR.

## Input Validation

`ContactIn` (the POST/PUT request body) validates beyond "is it JSON":
`name`/`company` reject blank/whitespace-only strings, `email` must be a
real email address (or blank, which the frontend sends for "unset"),
`followUpDate` must be a real date, and `status` must be one of the five
known values. Bad input gets a `422` with field-level detail instead of
reaching the database.

## Error Monitoring

[Sentry](https://sentry.io) (`sentry-sdk[fastapi]`) is wired up but stays
completely inert until `SENTRY_DSN` is set — no account or network calls
otherwise. Create a free Sentry project and set the DSN as a Vercel env var
to turn it on.

## Endpoints

All endpoints require `Authorization: Bearer <supabase-jwt>` and operate only
on the authenticated user's own contacts.

| Method | Path              | |
|--------|-------------------|---|
| GET    | `/contacts`       | List the user's contacts |
| POST   | `/contacts`       | Create a contact |
| PUT    | `/contacts/{id}`  | Update a contact (404 if not found or not owned) |
| DELETE | `/contacts/{id}`  | Delete a contact |
