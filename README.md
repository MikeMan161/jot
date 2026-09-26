<div align="center">

# jot

**Personal finance tracking that takes one sentence.**

Type *"spent $40 on groceries yesterday"* and Jot parses it into a categorized transaction — no forms, no dropdowns, no thirteen-field modal.

[**Live app →**](https://spendwithjot.com) · [**API docs →**](https://api.spendwithjot.com/docs)

![Status](https://img.shields.io/badge/status-live-success)
![License](https://img.shields.io/badge/license-MIT-blue)
![Python](https://img.shields.io/badge/python-3.12-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)
![React](https://img.shields.io/badge/React-61DAFB?logo=react&logoColor=black)
![TypeScript](https://img.shields.io/badge/TypeScript-3178C6?logo=typescript&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-4169E1?logo=postgresql&logoColor=white)
![AWS](https://img.shields.io/badge/AWS-232F3E?logo=amazonaws&logoColor=white)

</div>

---

<div align="center">
  <img src="docs/screenshots/demo.gif" alt="Logging a transaction in one sentence" width="800">
</div>

---

## What it is

Jot is a full-stack personal finance app built around one idea: **budgeting apps fail because logging a transaction is tedious.** Every extra field is a reason to skip it, and a budget you stop updating is worse than no budget at all.

So the primary input is a sentence. An LLM layer parses natural language into a structured transaction: amount, merchant, category, date — validated server-side before it touches the database.

The budgeting model follows Ramit Sethi's Conscious Spending Plan: four buckets with user-set target percentages rather than a line-item budget for every category.

| Bucket | Typical target |
|---|---|
| Fixed Costs | 50–60% |
| Investments | 10% |
| Savings | 5–10% |
| Guilt-Free Spending | 20–35% |

Targets are guidance, not limits. Jot does not scold you for spending, the whole point of naming a bucket "guilt-free" is that money in it is already accounted for.

**Jot never connects to a bank.** There is no account linking and no money movement. It is an advisory and tracking layer, deliberately.

---

## Try it

The live app is at **[spendwithjot.com](https://spendwithjot.com)**.

The interactive API documentation is public at **[api.spendwithjot.com/docs](https://api.spendwithjot.com/docs)** — every endpoint, schema, and auth flow is browsable there.

---

## Stack

| Layer | Technology |
|---|---|
| Frontend | React + TypeScript (Vite), Tailwind CSS, shadcn/ui |
| Backend | FastAPI (Python), gunicorn + uvicorn workers |
| Database | PostgreSQL 18 |
| Auth | JWT (bcrypt password hashing) |
| AI layer | Anthropic API |
| Frontend hosting | S3 (private) + CloudFront |
| Backend hosting | Elastic Beanstalk (EC2 behind an ALB) |
| Database hosting | Amazon RDS |
| DNS / TLS | Route 53 + ACM |

---

## Architecture

```
Browser
  │
  ├── https://spendwithjot.com ──────→ CloudFront ──→ S3 (private, OAC)
  │                                                    └─ React production build
  │
  └── https://api.spendwithjot.com ──→ ALB (TLS) ───→ EC2
                                                       ├─ nginx  :80
                                                       └─ gunicorn/uvicorn :8000
                                                            └─ FastAPI
                                                                 ├──→ RDS PostgreSQL
                                                                 └──→ Anthropic API
```

TLS terminates at the load balancer; the application itself only ever speaks plain HTTP on the instance. The React bundle is fully static — all authentication and data access happens through the API over HTTPS.

---

## Engineering decisions

**Ownership checks return 404, never 403.** Authentication (*is this a valid user?*) and authorization (*does this row belong to them?*) are separate concerns — the first lives in a `get_current_user` dependency, the second in each route handler. Both failure modes return 404. A 403 would confirm to an attacker that a resource exists.

**UUID primary keys everywhere.** Sequential integer IDs let anyone enumerate `/transactions/1`, `/transactions/2`, and measure how many users you have.

**All money is `NUMERIC(10,2)`, never a float.** Binary floating point cannot represent `0.10` exactly. In a finance app, that is not an acceptable rounding error.

**Soft delete on financial records, hard cascade on accounts.** Deleting a transaction sets `deleted_at` — financial history should be recoverable. Deleting an *account* cascades and actually removes the rows, because a user asking to be deleted should be deleted.

**Transactions survive category deletion.** `transactions.category_id` is `ON DELETE SET NULL`. Removing a category should never silently destroy spending history.

**Buckets are fixed at four and seeded atomically on registration.** There is no `POST /buckets` or `DELETE /buckets`. The four-bucket model *is* the product thesis — making it user-editable would turn Jot into a generic category tracker with extra steps.

**Debts are modeled as payments against Fixed Costs, not a parallel ledger.** A debt payment is money leaving your account this month. Storing it separately would make the bucket percentages lie.

**No secret falls back to a dev default.** This behaved correctly in production: a missing `DATABASE_URL` is read at import and produced an immediate startup error naming the exact file and line, instead of a green health check on an environment that would fail later under real traffic. The auth secrets are read at call time, so a missing one surfaces at the first login rather than at boot.

**The health check queries the database.** `/health` runs `SELECT 1` rather than returning a static string, so the load balancer's view of "healthy" reflects the actual stack rather than just "the web server is up."

**RDS is decoupled from the Elastic Beanstalk environment lifecycle.** Provisioning the database through `eb create --database` puts it inside the environment's CloudFormation stack — tearing down the environment would take the data with it. The database is a standalone resource.

**The load balancer exists for TLS, not scale.** Min and max instances are both 1. It was added only when HTTPS on a custom domain required it, and deliberately deferred until then because it roughly doubles the monthly run rate.

**bcrypt is called directly instead of through passlib.** passlib's internal version check crashes on startup against bcrypt 4.x. Dropping the wrapper is a two-line change and removes a dependency.

**`Base.metadata.create_all()` shipped before Alembic.** This was a sequencing decision with a stated trigger condition, not an omission: `create_all` is sufficient for an empty database, and it becomes insufficient the moment a column needs to change on live data. That condition fired when demo accounts needed a `users.is_demo` column, and **Alembic is now the source of truth for schema changes** (`backend/alembic/`).

**Alembic was adopted by baselining, not by autogenerating.** The first revision is deliberately empty and was applied with `alembic stamp head`: the seven tables already existed, so the baseline records "everything up to here is already present" rather than trying to recreate it. `--autogenerate` is intentionally not used yet — the models and the original hand-written DDL have drifted in harmless ways (bare `String` in the models, `VARCHAR(255)` in the DDL), and autogenerate would emit column-type rewrites against live data alongside any real change. Revisions are hand-written until that drift is reconciled. One consequence: a brand-new empty database still needs `database/migrations/001_create_tables.sql` to bootstrap, because `alembic upgrade head` starts *after* the baseline.

**Rate limiting is split across two mechanisms.** Per-minute burst limits live in process memory via `slowapi` (correct here because gunicorn runs a single worker, so one process holds every counter), and a per-user daily cap on the AI endpoint lives in Postgres (`ai_usage`). The split is deliberate: memory resets on every redeploy, and the Anthropic bill does not. Limits are applied as per-route decorators rather than through `SlowAPIMiddleware`, so the 429 is raised inside the route and still passes through the CORS middleware — a limit breach raised in middleware comes back without CORS headers and the browser misreports it as a CORS failure.

---

## Data model

Seven tables in PostgreSQL:

| Table | Holds |
|---|---|
| `users` | Account, credentials, currency preference |
| `buckets` | The four spending buckets and their target percentages |
| `categories` | User categories, each belonging to a bucket; defaults seeded on signup |
| `transactions` | Individual spending records |
| `income` | Income events with source and frequency |
| `savings_goals` | Named goals with target and current amounts, scoped to a bucket |
| `debts` | Balance, APR, minimum payment, due date |

Every table uses UUID primary keys, timezone-aware timestamps, and `NUMERIC(10,2)` for monetary columns. Financial records carry a `deleted_at` column for soft deletion.

---

## Running locally

### Prerequisites

- Python 3.12+
- Node.js 20+
- PostgreSQL 18
- An [Anthropic API key](https://console.anthropic.com/) for the natural-language input feature

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Copy the template and fill in the values — it lists every variable the backend reads:

```bash
cp .env.example .env
```

Generate `SECRET_KEY` with `python -c "import secrets; print(secrets.token_hex(32))"`.

Then, from `backend/`:

```bash
uvicorn app.main:app --reload
```

The API serves on `http://localhost:8000`, with interactive docs at `/docs`. Tables are created on first startup.

> `gunicorn` is Linux-only — it depends on `fcntl`. Use `uvicorn` locally even though production runs gunicorn.

### Frontend

```bash
cd frontend/financial-tracker-client
npm install
```

No configuration is needed — the API URL falls back to `http://localhost:8000`. To point the dev server at a different backend, create `.env` in the same directory:

```env
VITE_API_URL=http://localhost:8000
```

Production builds read the committed `.env.production` instead.

Then:

```bash
npm run dev
```

The app serves on `http://localhost:5173`. The backend must be running simultaneously.

> `VITE_API_URL` is inlined into the bundle at **build** time, not read at runtime. Changing it requires a rebuild.

---

## Repository structure

```
Financial-Dashboard/
├── backend/
│   ├── app/
│   │   ├── main.py           # FastAPI entry point, CORS, router registration
│   │   ├── database.py       # Engine, SessionLocal, Base, get_db()
│   │   ├── auth.py           # Password hashing, JWT creation and verification
│   │   ├── dependencies.py   # get_current_user — protects authenticated routes
│   │   ├── models/           # SQLAlchemy models
│   │   ├── schemas/          # Pydantic schemas, one file per resource
│   │   ├── routers/          # auth, users, buckets, categories, transactions,
│   │   │                     #   debts, income, savings_goals, ai
│   │   └── services/
│   │       └── ai.py         # Natural-language transaction parsing
│   ├── alembic/              # Migrations — source of truth for schema changes
│   ├── alembic.ini           # URL deliberately blank; env.py reads DATABASE_URL
│   ├── Procfile              # ASGI worker override for Elastic Beanstalk
│   └── requirements.txt
├── database/
│   ├── migrations/           # Original DDL — still needed to bootstrap an empty database
│   └── erd.drawio            # Entity-relationship diagram
├── frontend/
│   └── financial-tracker-client/
│       ├── src/
│       │   ├── api/          # Typed API client — config, auth, resources
│       │   ├── components/
│       │   ├── pages/
│       │   └── hooks/
│       └── vite.config.ts
└── README.md
```

---

## Roadmap

**Near term**
- Reconcile model/DDL drift so Alembic `--autogenerate` is safe to run
- Backfill the empty baseline revision with real `CREATE TABLE` statements, so a fresh database can be built from `alembic upgrade head` alone
- Migrating auth to httpOnly cookies + refresh-token flow
- Route-level code splitting to cut the initial bundle
- CloudFront SPA error mapping so deep links survive a refresh
- Empty-state UI across list views

**Later**
- CSV and bank-statement import
- Ghost subscription detection — flagging recurring charges you've forgotten
- Automation checklist — concrete transfer amounts derived from income and bucket targets
- Mid-month check-in view comparing actuals against targets
- FRED API integration for economic benchmarking
- Multi-factor authentication
- Mobile: React Native or PWA

---

## About

Built by **Michael Rivera**, CS student at the University of North Florida.

[LinkedIn](https://linkedin.com/in/riveramike/) · [Dev notes](https://mikeman161.github.io/dev-notes) · Michael.A.Rivera.Dev@gmail.com

Written from schema to production deployment as a solo project. Design decisions, architecture, and tradeoffs are documented above because the reasoning is the interesting part.

