# AGENTS.md — Cooperative Gig Services Platform

> **For AI coding agents working in this repository.**
> Read this file in full before making any changes.

---

## Project Name

**Cooperative Gig Services Platform for Household & Community Services**

---

## Project Vision

A cooperative-owned digital marketplace that connects customers with verified household and community service workers.
The platform is governed by a **labour cooperative**, not a private company. This distinction shapes every design and feature decision.

### Platform Flow

```
Customer
  ↓
Web / WhatsApp / Voice
  ↓
Service Request
  ↓
Verified Worker Pool
  ↓
AI-Assisted Matching (rule-based scoring, explainable)
  ↓
Worker Selection / Cooperative Allocation
  ↓
Booking → Service → Payment → Rating & Feedback
  ↓
Cooperative Analytics
```

---

## Primary User Roles

| Role | Responsibilities |
|------|-----------------|
| **Customer** | Browse services, create requests, book workers, pay, rate |
| **Worker** | Register, build profile, set availability, accept jobs, track earnings |
| **Cooperative Admin** | Manage workers, verify workers, allocate jobs, monitor analytics |

---

## Technology Stack

| Layer | Technology |
|-------|-----------|
| Frontend Framework | React + Vite |
| Frontend Language | JavaScript (ES2022+) |
| Frontend Styling | Tailwind CSS |
| Frontend Routing | React Router |
| Backend Framework | Python + FastAPI |
| Database | SQLite |
| ORM | SQLAlchemy |
| Validation | Pydantic (v2) |
| Authentication | JWT (python-jose) + bcrypt |
| Dev tooling | uvicorn (dev server) |

---

## Repository Structure

```
cooperative-platform/          ← Root
│
├── frontend/
│   ├── src/
│   │   ├── components/       ← Reusable UI components
│   │   ├── pages/            ← Route-level page components
│   │   ├── layouts/          ← Shared layout wrappers
│   │   ├── services/         ← API call functions (axios)
│   │   ├── hooks/            ← Custom React hooks
│   │   ├── utils/            ← Pure helper functions
│   │   └── data/             ← Static/seed data for dev
│   ├── public/
│   ├── index.html
│   ├── vite.config.js
│   ├── tailwind.config.js
│   └── package.json
│
├── backend/
│   ├── app/
│   │   ├── models/           ← SQLAlchemy ORM models
│   │   ├── schemas/          ← Pydantic request/response schemas
│   │   ├── routes/           ← FastAPI route handlers (thin layer)
│   │   ├── services/         ← Business logic
│   │   ├── database/         ← DB engine, session, migrations
│   │   ├── auth/             ← JWT creation, password hashing, dependencies
│   │   └── main.py           ← FastAPI app entry point
│   ├── tests/
│   ├── requirements.txt
│   └── .env.example
│
├── AGENTS.md                 ← This file
├── PROJECT_STATUS.md
├── README.md
└── .gitignore
```

---

## Database Entities (Planned)

| Entity | Key Fields |
|--------|-----------|
| User | id, name, email, phone, password_hash, role, created_at |
| Cooperative | id, name, location, description, admin_id |
| Worker | id, user_id, cooperative_id, profession, skills, experience, location, availability, verification_status, rating, workload |
| Service | id, name, category, description |
| ServiceRequest | id, customer_id, service_id, location, date, time, description, status |
| Booking | id, request_id, worker_id, status, amount, payment_status |
| Rating | id, booking_id, customer_id, worker_id, rating, feedback |

> Do NOT create all tables in Mission 0. Build entities as each phase requires them.

---

## AI Matching Concept (Phase 5)

The matching engine ranks eligible workers using a **transparent rule-based scoring system**.

| Factor | Weight |
|--------|--------|
| Skill Match | 30% |
| Distance | 20% |
| Availability | 20% |
| Rating | 10% |
| Experience | 10% |
| Workload Fairness | 10% |

**Rules:**
1. First eliminate ineligible workers (unavailable, unverified, wrong skills).
2. Score remaining workers.
3. Return ranked results with an explanation of each score component.
4. **Never present this as a trained ML model.** It is an explainable rule-based scoring engine.

---

## Coding Rules

### General

1. Inspect the repository before making any changes.
2. Do NOT overwrite existing files blindly.
3. Do NOT create duplicate implementations of the same feature.
4. Do NOT install unnecessary packages.
5. Keep frontend and backend logically separated — no mixing of concerns.
6. Use clear, descriptive naming conventions throughout.

### Backend

7. Keep business logic in `services/`, not in route handlers.
8. Keep route handlers thin — they validate input and call services.
9. Use Pydantic schemas for all API request/response validation.
10. Use SQLAlchemy models for all database entities.
11. **Never store plain-text passwords.** Use bcrypt.
12. **Never put secrets or API keys into source code.** Use `.env` files.
13. Backend must enforce authorization. Do NOT rely on frontend-only route protection.
14. Every new route must have at least one test in `backend/tests/`.

### Frontend

15. Keep business logic out of React components where possible — use `hooks/` and `services/`.
16. Components in `components/` must be reusable; page-specific logic goes in `pages/`.
17. API calls must go through `services/` layer, never directly from components.

### AI Matching

18. AI matching must remain explainable and auditable.
19. Do NOT pretend that a rule-based scoring system is a trained ML model.
20. Matching decisions should be fully logged and inspectable by the cooperative admin.

### Git / Repository

21. We are working directly on the `main` branch.
22. Keep the repository in a working state after every milestone.
23. Do NOT push to GitHub unless explicitly instructed by the developer.
24. Do NOT move to the next phase until the current phase is functional and verified.

---

## Architecture Constraints (Hackathon)

We have approximately 12 hours for a working prototype. Therefore:

**WORKING PROTOTYPE > COMPLEX ARCHITECTURE**

Do NOT introduce:
- Microservices
- Kubernetes / Docker (unless genuinely required)
- Complex ML pipelines
- Blockchain
- Complex payment infrastructure
- Production-scale distributed systems
- Unnecessary third-party dependencies

---

## Environment Files

- Backend secrets live in `backend/.env` (not committed).
- Copy `backend/.env.example` to `backend/.env` and fill in values.
- Frontend environment variables use `frontend/.env` (prefixed with `VITE_`).

---

## Mission Checklist Reference

See `PROJECT_STATUS.md` for the live phase checklist.
