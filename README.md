<div align="center">

# Pravah

**Every approval in motion. Every deadline in sight.**

An integrated platform for end-to-end automation and monitoring of AICTE approval workflows and institutional compliance.

![Smart India Hackathon 2026](https://img.shields.io/badge/Smart%20India%20Hackathon-2026-B3123C?style=flat-square&labelColor=0B1220)
![React](https://img.shields.io/badge/React-18-0B1220?style=flat-square&logo=react&logoColor=61DAFB)
![TypeScript](https://img.shields.io/badge/TypeScript-5-0B1220?style=flat-square&logo=typescript&logoColor=3178C6)
![Vite](https://img.shields.io/badge/Vite-0B1220?style=flat-square&logo=vite&logoColor=646CFF)
![Tailwind](https://img.shields.io/badge/Tailwind-0B1220?style=flat-square&logo=tailwindcss&logoColor=38BDF8)
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

**Prerequisites:** Node.js 18+ and npm.

```bash
git clone https://github.com/Arslan-SA/pravah.git
cd pravah
npm install
npm run dev      # start the app
npm test         # run engine tests
npm run build    # production build
```

## Project structure

Indicative layout:

```
pravah/
├── src/
│   ├── engine/        # framework-free workflow, deadline, alert and audit logic
│   ├── config/        # routes, timelines, reminder offsets, escalation ladder
│   ├── data/          # deterministic synthetic seed data
│   ├── components/    # dashboards, planner, tracker, audit viewer
│   └── store/         # UI state
├── tests/             # routing, auto-advance, alert idempotency, escalation, audit chain
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
