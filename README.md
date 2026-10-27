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

## Regulatory safeguard

Pravah is designed to function in accordance with the applicable AICTE regulations, the Approval Process Handbook and authorised administrative procedures. Alerts, summaries and workflow actions support the approval process. They do not replace statutory scrutiny, verification, inspections or decisions that must be taken by the competent authority.

## Team

**Team Synthetix** · Smart India Hackathon 2026

<!-- Add member names and roles here -->

## License

Released for Smart India Hackathon 2026. Add a license of your choice (for example MIT) before making the repository public.
