<div align="center">

# Pravah

**Every approval in motion. Every deadline in sight.**

An integrated platform for end-to-end automation and monitoring of AICTE approval workflows and institutional compliance.

![Smart India Hackathon 2026](https://img.shields.io/badge/Smart%20India%20Hackathon-2026-B3123C?style=flat-square&labelColor=0B1220)
![React](https://img.shields.io/badge/React-18-0B1220?style=flat-square&logo=react&logoColor=61DAFB)
![TypeScript](https://img.shields.io/badge/TypeScript-5-0B1220?style=flat-square&logo=typescript&logoColor=3178C6)
![Vite](https://img.shields.io/badge/Vite-0B1220?style=flat-square&logo=vite&logoColor=646CFF)
![Python](https://img.shields.io/badge/Python-3.12+-0B1220?style=flat-square&logo=python&logoColor=3776AB)
![FastAPI](https://img.shields.io/badge/FastAPI-0B1220?style=flat-square&logo=fastapi&logoColor=009688)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-0B1220?style=flat-square&logo=postgresql&logoColor=4169E1)
![Data](https://img.shields.io/badge/Demo%20data-synthetic-B3123C?style=flat-square&labelColor=0B1220)

</div>

---

## Overview

AICTE processes applications from technical institutions through several stages: scrutiny and re-scrutiny, Expert Visit Committee (EVC), SAC/SHC and others prescribed in the Approval Process Handbook (APH). Many approvals also carry time-bound undertakings and document-validity requirements such as lease renewals.

Tracking application movement, EVC scheduling, undertakings and document expiry across Regions and officials takes constant manual coordination and follow-up. **Pravah** replaces that with one configurable platform that routes applications, watches every deadline, raises alerts, escalates what is overdue, and records everything in a tamper-evident audit trail.

## What Pravah does

| Area | Capabilities |
|---|---|
| **Workflow automation** | Automatic routing through the applicable route (Only Scrutiny, Scrutiny + EVC, EVC + SAC/SHC, Only EVC), auto-advance on stage completion, authorised return/revert with recorded reasons |
| **Dashboards and pendency** | Real-time, role-based dashboards; ageing against stage timelines; Region × Stage heatmap; workload and bottleneck views |
| **EVC scheduling** | Automatic EVC queue (new institutions prioritised), schedule and completion tracking, reminders and escalation of delayed cases |
| **Undertakings** | Digital register of conditional approvals with due dates, online evidence submission, officer verification, overdue escalation |
| **Lease and document validity** | Expiry tracking, advance alerts, renewal submission and verification, overdue escalation |
| **Notifications and reports** | Configurable reminders, multi-level escalation ladder, Region-wise performance reports with CSV export |

## How it works

```
Institution submits application
        │
        ▼
 INTAKE CHECK ──incomplete──► RETURNED (reason code + remark) ──► resubmit ──┐
        │ ok                                                                  │
        ▼                                                                     │
 ROUTING ENGINE (route template from config) ◄────────────────────────────────┘
   ├─ ONLY_SCRUTINY : SCRUTINY ──────────────► DECISION
   ├─ SCRUTINY_EVC  : SCRUTINY → EVC ────────► DECISION
   ├─ EVC_SAC_SHC   : EVC → SAC/SHC ─────────► DECISION
   └─ ONLY_EVC      : EVC ───────────────────► DECISION

 DECISION (human only) ─► APPROVED │ APPROVED_WITH_UNDERTAKING │ REJECTED │ RETURNED
                                      │
                                      ▼
              Undertakings + document validity enter the compliance loop

 Compliance loop:  reminders (T-30, T-15, T-7, T-1)  →  overdue (T+0)
                   →  escalation L1 → L2 → L3  →  evidence submitted → verified → closed
```

## Architecture

```
┌────────────────────────  React dashboards (role-based)  ────────────────────────┐
│ Command · Applications · EVC Planner · Compliance · Alerts · Audit · Reports     │
└───────────────────────────────────────┬──────────────────────────────────────────┘
                                        │
┌───────────────────────────────────────▼──────────────────────────────────────────┐
│ API layer: auth, RBAC with Region scoping, validation                             │
├───────────────┬────────────────┬─────────────────┬───────────────┬───────────────┤
│ Workflow      │ Rules / Config │ SLA & Deadline  │ Compliance    │ Notification  │
│ engine        │ engine         │ engine          │ service       │ service       │
├───────────────┴────────────────┴─────────────────┴───────────────┴───────────────┤
│ Audit service (append-only, hash-chained)  │  Reporting service                   │
├──────────────────────────────────────────────────────────────────────────────────┤
│ Database │ Document storage │ Queue / cache                                       │
├──────────────────────────────────────────────────────────────────────────────────┤
│ Integration adapters for existing authorised AICTE systems                        │
└──────────────────────────────────────────────────────────────────────────────────┘
```

The prototype in this repository runs the full engine in the browser on synthetic data. The engine has no UI dependencies, so it can move behind an API unchanged.

## Design highlights

- **Injectable clock.** All deadline logic reads a simulated `now()`, so reminders and escalations can be demonstrated by jumping days ahead instead of waiting.
- **Config-driven rules.** Routes, stage timelines, reminder offsets and escalation ladders live in configuration, not in code, so they can follow the APH as it changes.
- **Idempotent alerts.** Each alert carries a dedupe key (`entity + rule + level`), so repeated scheduler runs never notify twice.
- **Tamper-evident audit trail.** Every event stores the hash of the previous one; a *Verify chain* control proves the log has not been altered.
- **Human decision gate.** Approval and rejection are permitted only for authorised roles. The system assists but never decides.
- **Region-scoped roles.** Regional officers see their Region; the Bureau sees all.

## Roles

| Role | Scope |
|---|---|
| Institution | Submit applications, respond to deficiencies, upload undertaking evidence and renewed documents |
| Regional officer | Scrutiny, return/revert, EVC scheduling, evidence verification within their Region |
| Bureau officer | All-Region dashboards, workload reassignment, decisions where authorised |
| Committee (EVC / SAC / SHC) | Assigned cases, visit and committee outcomes |
| Admin | Routes, timelines, reminder ladders, users |
| Auditor | Read-only access to audit trail and reports |

## Demo walkthrough

1. Open the **Command Dashboard** as a Bureau officer and review pendency by Region and stage.
2. Open an application, inspect its route stepper and timeline bar, then return it with a reason code.
3. In the **EVC Planner**, schedule an item from the unscheduled queue.
4. Advance the simulated clock by 10 days and watch EVC and undertaking reminders fire.
5. Advance to 25 days and watch an overdue lease escalate through L1 and L2.
6. Open the **Audit Trail** and verify the chain. Use the tamper demo to see verification fail.

Or press **Run guided demo** for a scripted version of the same scenario.

## Getting started

### Frontend

**Prerequisites:** Node.js 18+ and npm.

```bash
git clone https://github.com/Arslan-SA/pravah.git
cd pravah

# Option 1: Run from repository root
npm run dev      # starts frontend dev server
npm run build    # builds production bundle

# Option 2: Run directly in frontend/
cd frontend
npm install
npm run dev
```

### Backend

**Prerequisites:** Python 3.12+, PostgreSQL 15+.

```bash
cd backend

# 1. Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate    # macOS / Linux
# venv\Scripts\activate     # Windows

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment
cp .env.example .env
# Edit .env with your PostgreSQL credentials

# 4. Create the database
createdb aicte_flowops

# 5. Run migrations
alembic upgrade head

# 6. Bootstrap the initial administrator
python -m app.cli.create_admin --name "Dr. Initial Admin" --email "admin@aicte.gov.in"

# 7. Start the API server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 8. Run tests
pytest -v
```

### Authentication & RBAC

| Role | Scope & Permissions |
|---|---|
| `ADMIN` | User management, system configuration, global oversight |
| `AICTE_OFFICIAL` | Regional scrutiny, EVC coordination, compliance verification |
| `INSTITUTION_USER` | Submit applications, evidence uploads, compliance renewals |
| `REVIEWER` | Committee member, assigned EVC visits and expert reviews |

#### Environment Variables
```env
JWT_SECRET_KEY=aicte-flowops-development-secret-key-at-least-32-chars-long-2026
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=60
```

#### Obtaining and Using a Bearer Token
```bash
# Login
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@aicte.gov.in","password":"YourPassword@2026!"}'

# Use Bearer token for protected endpoints
curl http://localhost:8000/api/v1/auth/me \
  -H "Authorization: Bearer <ACCESS_TOKEN>"
```

## Project structure

```
pravah/
├── frontend/
│   ├── components/    # AppShell, UI components, charts, and DataTable
│   ├── data/          # Deterministic seed data and persistence
│   ├── lib/           # Statutory calculation, RBAC, dates, and CSV export
│   ├── pages/         # Role-based pages and workspaces
│   ├── store/         # State store, simulated clock, and deadline evaluation
│   ├── types.ts       # Domain types and statutory schemas
│   ├── index.css      # Design system and layout styles
│   ├── App.tsx        # Application router and protected routes
│   ├── index.tsx      # Entrypoint mounting React root
│   └── vite.config.ts # Vite configuration
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   └── v1/
│   │   │       ├── endpoints/  # Route handlers (health, ...)
│   │   │       └── router.py   # v1 API router
│   │   ├── models/             # SQLAlchemy ORM models
│   │   ├── schemas/            # Pydantic v2 schemas
│   │   ├── services/           # Business logic layer
│   │   ├── utils/              # Shared utilities
│   │   ├── config.py           # Settings via pydantic-settings
│   │   ├── database.py         # Engine, session, Base
│   │   └── main.py             # FastAPI application factory
│   ├── alembic/
│   │   ├── versions/           # Migration scripts
│   │   └── env.py              # Alembic environment config
│   ├── tests/                  # pytest test suite
│   ├── alembic.ini             # Alembic configuration
│   ├── requirements.txt        # Python dependencies
│   └── .env.example            # Environment variable template
├── package.json       # Root scripts forwarding to frontend
└── README.md
```

## Configuration

Rules live in `src/config/rules.ts`: route templates, stage timelines, reminder offsets and the escalation ladder. **All timelines in this repository are placeholders** and must be replaced with the values prescribed in the applicable APH and AICTE regulations.

## Prototype status and roadmap

| | Prototype (this repo) | Production path |
|---|---|---|
| Workflow engine, routing, auto-advance, return/revert | ✅ in-browser | Server-side state machine behind an API |
| Deadline, reminder and escalation engine | ✅ simulated clock | Persistent scheduler and queue |
| Role-based dashboards and reports | ✅ | Real authentication, Region-scoped access |
| Audit trail with chain verification | ✅ | Durable append-only store |
| Notifications | In-app feed | Email / SMS adapters |
| Integration with AICTE systems | Not included | Adapter layer for existing authorised systems |
| Document storage | Simulated | Secure object storage |

## Phase 8: Dashboard Analytics and Reporting APIs

The backend provides high-performance, database-level SQL aggregations and reporting endpoints strictly scoped by user roles. All calculations use database engines rather than fetching records into memory, ensuring zero sample hardcoding and instant responses even under heavy data load.

### Dashboard Endpoints

| Method | Endpoint | Allowed Roles | Description |
|---|---|---|---|
| `GET` | `/api/v1/dashboard/overview` | All authenticated roles | High-level summary counters, status breakdowns, pending action counts, and recent chronological transitions. |
| `GET` | `/api/v1/dashboard/applications` | All authenticated roles | Application volume metrics, status distribution, application types, academic year breakdowns, and monthly submission trends. |
| `GET` | `/api/v1/dashboard/workflow` | All authenticated roles | Active application load by workflow stage, pending ageing buckets (`<30d`, `30-60d`, `60-90d`, `>90d`), average turnaround duration, and recent transitions. |
| `GET` | `/api/v1/dashboard/compliance` | All authenticated roles | Compliance and undertaking status breakdown, fulfillment rates (`verified/total %`), overdue counts, and document validity/expiration buckets. |
| `GET` | `/api/v1/dashboard/alerts` | All authenticated roles | Alerts breakdown by read status, urgency level (`LOW`, `MEDIUM`, `HIGH`, `CRITICAL`), notification event types, and supervisor escalation records. |

#### Role Access & Isolation Rules
- **Institution User (`INSTITUTION_USER`)**:
  - Automatically and strictly isolated to records belonging to their linked `institution_id`.
  - Attempting to pass another institution's ID in query parameters immediately returns `403 Forbidden`.
  - Sees their own institution's active applications, pending clarifications, upcoming deadlines, and user-directed alerts.
- **AICTE Official (`AICTE_OFFICIAL`) & Administrator (`ADMIN`)**:
  - Full system-wide visibility across all institutions.
  - Optional `institution_id` query parameter to drill down into a single institution's analytics.
  - Access to statutory supervisor escalation logs and system-wide workload distribution.
- **Reviewer (`REVIEWER`)**:
  - Scoped strictly to applications assigned to the reviewer.
  - Unassigned reviewer sessions return clean zeroed metrics without crashing.

#### Example Overview Response (`GET /api/v1/dashboard/overview`)
```json
{
  "role": "INSTITUTION_USER",
  "institution_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "application_summary": {
    "total": 4,
    "draft": 1,
    "submitted": 1,
    "under_scrutiny": 1,
    "returned_for_clarification": 1,
    "evc_pending": 0,
    "evc_scheduled": 0,
    "under_review": 0,
    "approved": 0,
    "rejected": 0,
    "closed": 0,
    "requires_action": 1
  },
  "compliance_summary": {
    "total": 3,
    "pending": 1,
    "submitted": 1,
    "under_verification": 0,
    "verified": 1,
    "rejected": 0,
    "overdue": 0,
    "upcoming_deadlines": 1,
    "expiring_documents_30_days": 1,
    "expired_documents": 0
  },
  "alerts_summary": {
    "unread": 2,
    "total": 5,
    "critical": 0,
    "overdue": 0,
    "escalations_count": 0
  },
  "recent_activity": [
    {
      "id": "c1f7b025-a134-4b5c-b179-c5d0124ad302",
      "activity_type": "stage_transition",
      "application_id": "8f3b204e-eef0-4965-b1a9-b6973946eb2c",
      "application_number": "APP-2026-A1B2C3",
      "title": "Stage transition: Scrutiny Review Completed",
      "description": "All infrastructure norms verified",
      "status": "UNDER_SCRUTINY",
      "timestamp": "2026-10-27T10:15:00Z",
      "acted_by": "Regional Officer Sharma"
    }
  ]
}
```

---

### Reporting & Data Export Endpoints

| Method | Endpoint | Query Parameters | Description |
|---|---|---|---|
| `GET` | `/api/v1/reports/applications` | `start_date`, `end_date`, `status`, `workflow_stage`, `institution_id`, `format`, `page`, `page_size` | Application summary report with pendency days, stage progression, and status. |
| `GET` | `/api/v1/reports/compliance` | `status`, `compliance_type`, `institution_id`, `start_date`, `end_date`, `format`, `page`, `page_size` | Compliance audit report with due dates, verification status, and overdue flags. |
| `GET` | `/api/v1/reports/overdue` | `institution_id`, `entity_type` (`application` or `compliance`), `format`, `page`, `page_size` | Combined overdue and ageing tracking (>30 days pending applications and overdue compliance). |
| `GET` | `/api/v1/reports/documents` | `institution_id`, `days_window` (default 30), `document_type`, `format`, `page`, `page_size` | Document metadata, size, upload timestamp, and expiration validity status. |

#### CSV Export Usage
To export any report directly as a downloadable CSV spreadsheet, provide the query parameter `format=csv`:

```bash
# Export applications report for your institution (or all institutions if admin/official)
curl -H "Authorization: Bearer <TOKEN>" \
  "https://api.flowops.aicte.gov.in/api/v1/reports/applications?format=csv&status=SUBMITTED" \
  -o applications_report.csv

# Export overdue compliance and ageing cases
curl -H "Authorization: Bearer <TOKEN>" \
  "https://api.flowops.aicte.gov.in/api/v1/reports/overdue?format=csv" \
  -o overdue_report.csv
```

The CSV response includes:
- Content-Type: `text/csv; charset=utf-8`
- Header: `Content-Disposition: attachment; filename="<report_name>_<YYYY-MM-DD>.csv"`
- Standard headers matching tabular views, properly escaped against comma/newline injections.

---

## Phase 9: AI-Assisted Insights & Workflow Intelligence

Phase 9 introduces an AI-assisted analytical layer providing natural-language executive briefings, operational pending-work alerts, bottleneck diagnostics, and statutory compliance risk intelligence.

### AI Endpoints

| Method | Endpoint | Query Parameters | Description |
|---|---|---|---|
| `GET` | `/api/v1/ai/applications/{id}/summary` | None | Concise executive summary, completed stages, outstanding actions, document signals, and advisory recommendations. Strictly isolated by institution and reviewer assignments. |
| `GET` | `/api/v1/ai/dashboard/insights` | `institution_id` (admin/official only) | Prioritized operational intelligence covering ageing applications, multi-item deficiencies, impending deadlines, and document expiries with explainable factual references. |
| `GET` | `/api/v1/ai/workflow/bottlenecks` | `institution_id` (admin/official only) | Quantitative queue throughput diagnostics (average wait days vs configured targets, overdue volumes) paired with administrative load-balancing narrative. |
| `GET` | `/api/v1/ai/compliance/insights` | `institution_id` (admin/official only) | Statutory compliance risk breakdown (overdue items, 14-day upcoming deadlines, items awaiting scrutiny verification, expiring legal certificates, and common deficiency trends). |

### AI Provider Architecture & Configuration

The service utilizes an extensible provider abstraction (`BaseAIProvider`) supporting vendor-agnostic deployments:
- **Configured Providers**: `gemini` (Google Gemini 1.5 Flash), `openai` (GPT-4o mini), `mock` (unit testing), `fallback` (deterministic rule engine).
- **Graceful Fallback**: If `AI_ENABLED=false`, no API key is configured, or external provider calls experience network timeouts or rate limits, the system automatically falls back to the deterministic rule engine without throwing 500 errors.
- **Privacy & Security**: API keys are stored strictly server-side in environment variables and never exposed to clients. External prompts omit sensitive personally identifiable information (PII) and only pass minimal structured workflow attributes.

#### Environment Variables (`.env`)

```ini
# AI Provider Configuration
AI_ENABLED=true
AI_PROVIDER=fallback        # Options: fallback, gemini, openai, mock
AI_API_KEY=your_key_here    # Server-side API key (kept confidential)
AI_MODEL=gemini-1.5-flash    # Model identifier
AI_TEMPERATURE=0.2          # Low temperature for factual consistency
AI_TIMEOUT_SECONDS=15       # Network request timeout
AI_MAX_TOKENS=1500          # Maximum token budget
```

### AI Decision Boundaries & Safeguards

The AI intelligence subsystem operates within strict safety boundaries:
1. **Advisory Only**: AI outputs are strictly advisory (`is_ai_generated=true` / `is_ai_generated=false`) and must be reviewed by authorized human officials.
2. **No Autonomous Approvals/Rejections**: The AI engine never alters `Application.status`, never records regulatory approvals or rejections, and never closes compliance records.
3. **Fact-Grounded**: Every insight references explicit verified database identifiers and timestamps; numerical metrics (pending counts, wait days, overdue numbers) are computed via deterministic database aggregation.
4. **Mandatory Advisory Disclaimer**: Every response contains:
   > *"Advisory AI-generated insight. Requires human verification by an authorized official; does not constitute a statutory or regulatory decision."*

---

## Phase 10: Final Integration, Security Hardening, Testing & Deployment Readiness

Phase 10 consolidates, hardens, tests, and prepares both the backend and frontend for production deployment on Render and Vercel.

### 1. Security Hardening & Regulatory Decision Boundaries

- **Password Cryptography**: Passwords are securely hashed using **Argon2id** (`pwdlib[argon2]`). Complex password validation enforces at least 8 characters, upper/lower case letters, digits, and special symbols.
- **JWT Authentication & Token Lifecycle**: Signed with HMAC-SHA256 (`HS256`) including UTC issued-at (`iat`) and expiration (`exp`) timestamps. Expired, tampered, or missing tokens are strictly rejected with HTTP 401.
- **Multi-Tenant Data Isolation**:
  - `INSTITUTION_USER` accounts can only access records belonging to their own affiliated institution. Attempting to access another institution's applications, compliance records, or documents yields HTTP 404/403 to prevent ID enumeration.
  - `REVIEWER` accounts can only access applications explicitly assigned to them.
- **File Upload & Storage Security**:
  - Magic byte verification (`_detect_mime_type_from_bytes`) inspects true binary headers, preventing spoofed file extensions.
  - Allowed file types restricted strictly to `.pdf`, `.png`, `.jpg`, `.jpeg`, `.doc`, `.docx`.
  - File size restricted by `STORAGE_MAX_FILE_SIZE_MB` (default 15MB).
  - Filenames sanitized via `re.sub(r"[^a-zA-Z0-9_.-]", "_", ...)`.
  - Storage keys are isolated by tenant (`institutions/{id}/{uuid}_{filename}`) and directory traversal attacks (`../`) are detected and blocked.
- **Fail-Fast Production Safeguard**: When `APP_ENV=production`, `validate_production_security()` verifies that `JWT_SECRET_KEY` is a non-default secret with at least 32 characters, preventing deployment misconfigurations.
- **Idempotent Background Jobs**: The statutory deadline scheduler enforces deduplication keys (`COMPL_DUE_SOON:{rec_id}:{due_date}:{days}:{user_id}` and `COMPL_OVERDUE:{rec_id}:{due_date}:{user_id}`) so repeated scheduler executions never create duplicate notifications.
- **Human-in-the-Loop Decision Gate**: AI summaries and insights remain purely advisory. Final approvals, conditional approvals with undertakings, and rejections are strictly reserved for authorized human officials.

---

### 2. Deployment Guide

#### Backend Deployment (Render)

The backend is configured for deployment as a Web Service on **Render** with PostgreSQL.

1. **Blueprints / IaC (`render.yaml`)**:
   Connect the GitHub repository in the Render dashboard and deploy using the included `render.yaml` blueprint.
2. **Environment Variables on Render**:
   - `APP_ENV=production`
   - `DEBUG=false`
   - `DATABASE_URL` (linked from Render PostgreSQL service)
   - `JWT_SECRET_KEY` (secure 32+ character random string)
   - `CORS_ORIGINS=https://<your-vercel-domain>.vercel.app`
   - `STORAGE_BACKEND=local` (or `s3` for object storage)
   - `ENABLE_SCHEDULER=true`
   - `AI_ENABLED=true`
   - `AI_PROVIDER=deterministic` (or `gemini` with `AI_API_KEY`)
3. **Build & Start Commands**:
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `./start.sh` (automatically applies `alembic upgrade head` then starts `uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 2`)
   - **Health Check Path**: `/health` (responds 200 OK with `status: healthy`)

Alternatively, containerized deployments can build using `backend/Dockerfile` with non-root security user `aicte`.

#### Frontend Deployment (Vercel)

The frontend is built with React 18, TypeScript, and Vite.

1. **Connect Repository to Vercel**:
   - **Framework Preset**: Vite
   - **Root Directory**: `frontend`
   - **Build Command**: `npm run build`
   - **Output Directory**: `dist`
2. **Environment Variables**:
   - `VITE_API_BASE_URL=https://<your-render-backend>.onrender.com`
3. **SPA Routing Rewrites (`frontend/vercel.json`)**:
   Includes routing rewrites directing all non-asset paths to `/index.html`, ensuring deep links and page refreshes on `/applications`, `/dashboard`, and `/compliance` resolve correctly without 404s.

---

### 3. Local Development Setup

#### Backend Setup

```bash
cd backend

# 1. Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment
cp .env.example .env
# Edit .env with your local PostgreSQL credentials

# 4. Apply database migrations
alembic upgrade head

# 5. Start development API server
uvicorn app.main:app --reload --port 8000
```
Interactive API documentation will be available at `http://localhost:8000/docs`.

#### Frontend Setup

```bash
cd frontend

# 1. Install dependencies
npm install

# 2. Start Vite development server
npm run dev
```
The application will launch on `http://localhost:3000` (with automatic `/api` proxying to `http://127.0.0.1:8000`).

---

### 4. Running Automated Tests

```bash
cd backend
source venv/bin/activate

# Run the complete test suite across all 10 phases
pytest

# Run with verbose test-by-test breakdown
pytest -v

# Run Phase 10 security hardening and integration tests specifically
pytest -v tests/test_phase10_security_and_integration.py
```

---

### 5. Safe Demonstration Accounts

The platform includes configured demo profiles across all four primary administrative roles:

| Role | Email | Password | Access Scope |
|---|---|---|---|
| **AICTE Administrator** | `admin@aicte-india.org` | `flowops2026` / `password` | System-wide configuration, reminder rules, bottleneck analytics, global reports |
| **Regional Officer** | `officer@aicte.gov.in` | `flowops2026` / `password` | Regional scrutiny, EVC scheduling, compliance verification, regional dashboards |
| **Institution Official** | `institute@college.edu` | `flowops2026` / `password` | Application drafting/submission, undertaking evidence uploads, document renewals |
| **Committee Reviewer** | `committee@aicte.gov.in` | `flowops2026` / `password` | Assigned application scrutiny, EVC inspections, observation reports |

---

### 6. Known Limitations & Production Assumptions

1. **Document Storage**: Configured by default to `local` disk storage in `./storage/uploads`. For multi-instance horizontal scaling, set `STORAGE_BACKEND=s3` and configure AWS S3 / Cloudflare R2 bucket credentials.
2. **Statutory Rules & Deadlines**: The platform models statutory workflows and deadline alerts via configurable rules (`WorkflowTransition`, `ReminderRule`, `WorkflowStage.target_completion_days`) rather than hardcoding AICTE regulations, allowing officials to update rules per annual APH guidelines.
3. **External Email / SMS Delivery**: Notifications are generated and stored in the database with real-time web delivery; external SMTP / SMS gateway adapters can be connected via the `NotificationService` dispatch hook.
4. **AI Output Advisory Nature**: All AI executive briefings and workflow diagnostics are advisory and require human official review prior to any statutory action.

---

## Regulatory safeguard

Pravah is designed to function in accordance with the applicable AICTE regulations, the Approval Process Handbook and authorised administrative procedures. Alerts, summaries and workflow actions support the approval process. They do not replace statutory scrutiny, verification, inspections or decisions that must be taken by the competent authority.

## Team

**Team Synthetix** · Smart India Hackathon 2026

<!-- Add member names and roles here -->

## License

Released for Smart India Hackathon 2026.

