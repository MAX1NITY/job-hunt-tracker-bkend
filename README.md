# Job Hunt Tracker — Backend

FastAPI backend for the [Job Hunt Tracker](https://github.com/MAX1NITY/job-hunt-tracker-frntend)
frontend. Exposes CRUD endpoints over a `contacts` table in Neon
(Postgres). It is a single-user app: there are no accounts, and every request
must carry one shared secret in the `X-Access-Key` header.

**Live:** https://job-hunt-tracker-bkend.vercel.app

Note: the frontend case study describes the earlier Supabase/Google-login
design. This service now uses Neon and a single access key instead.

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements-dev.txt

cp .env.example .env             # fill in your Neon connection string and an access key
uvicorn api.index:app --reload
```

## Environment Variables

```
DATABASE_URL=                    # Neon connection string (use the pooled one)
APP_ACCESS_KEY=                  # long random secret; the frontend sends it as X-Access-Key. Unset = every request refused (503)
ALLOWED_ORIGINS=                 # comma-separated, or * to allow any origin
SENTRY_DSN=                      # optional — leave blank to disable error monitoring
```

## Testing

```bash
pytest -v
```

Tests replace the single database seam, `run()` (`tests/conftest.py`), so
they run with no network access and no real database. They're split by concern:

- `tests/test_conversions.py` — pure `to_row`/`to_contact` mapping functions
- `tests/test_auth.py` — the access-key check: missing, wrong, and unconfigured keys
- `tests/test_contacts_api.py` — CRUD endpoints, sending the right key so these
  tests focus on request/response shape and the SQL parameters
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

All endpoints require the header `X-Access-Key: <APP_ACCESS_KEY>`.

| Method | Path              | |
|--------|-------------------|---|
| GET    | `/contacts`       | List contacts |
| POST   | `/contacts`       | Create a contact |
| PUT    | `/contacts/{id}`  | Update a contact (404 if not found; 422 if the id isn't a UUID) |
| DELETE | `/contacts/{id}`  | Delete a contact |
