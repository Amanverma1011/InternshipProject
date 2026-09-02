# Architecture

## Overview

The Sologix Solar Proposal System is a single-server Flask web application backed by MySQL. It follows a classic MVC structure: SQLAlchemy models, Flask route handlers (controllers), and Jinja2 templates (views).

```
Browser → Nginx (port 8080) → Gunicorn (127.0.0.1:8000) → Flask app → MySQL
```

---

## Directory Structure

```
.
├── app.py                  # App factory — wires extensions, blueprints, security headers
├── config.py               # Config classes (Dev / Production), env var loading
├── wsgi.py                 # Gunicorn entrypoint: application = create_app()
│
├── models/                 # SQLAlchemy ORM models
│   ├── user.py             # User (MASTER / USER roles), password hashing
│   ├── proposal.py         # Proposal + related tables (modules, battery, addons, payments, files)
│   ├── template.py         # PDF template metadata
│   ├── company.py          # Company settings (key-value store)
│   └── audit.py            # Audit log entries
│
├── routes/                 # Flask blueprints (one per domain)
│   ├── auth.py             # Login / logout, rate limiting, open-redirect protection
│   ├── dashboard.py        # Dashboard stats
│   ├── proposals.py        # Create, list, detail, generate PDF, accept/reject
│   ├── users.py            # User management (MASTER only)
│   └── templates.py        # PDF template management, audit log view
│
├── services/               # Business logic (called from routes)
│   ├── pdf_service.py      # HTML → PDF (xhtml2pdf), letterhead stamping (reportlab + pypdf)
│   ├── proposal_service.py # Proposal creation, snapshot building
│   ├── calculation_service.py # Price calculations, quota checks
│   ├── audit_service.py    # Structured audit log writer
│   ├── file_service.py     # PDF file storage (dated directory structure)
│   └── quota_service.py    # Per-user monthly proposal quota
│
├── templates/              # Jinja2 HTML templates
│   ├── base.html           # Shared layout: navbar, flash messages, Bootstrap
│   ├── auth/               # Login page (standalone, no base)
│   ├── dashboard/          # Stats overview
│   ├── proposals/          # List, create, detail, preview
│   ├── users/              # Create user, list users
│   ├── templates_mgmt/     # PDF template list, edit, audit
│   └── pdf/                # PDF-only templates (ongrid.html, hybrid.html)
│
├── static/
│   ├── css/app.css         # Custom styles (orange brand theme over Bootstrap 5)
│   ├── js/proposal.js      # Dynamic form JS (add/remove rows)
│   └── images/             # logo.jpg, letterhead.png, favicon.ico
│
├── database/
│   ├── schema.sql          # Full DB schema (CREATE TABLE, CREATE USER, grants)
│   ├── seed_auto.py        # Seeds master user + templates (reads env vars)
│   └── seed.py             # Interactive seed script for dev
│
├── deploy/
│   └── setup_vm.sh         # Full GCP VM bootstrap script
│
├── tests/
│   ├── test_auth.py        # Login / logout / rate limit tests
│   ├── test_calculations.py # Price calc unit tests
│   └── test_quota.py       # Quota enforcement tests
│
└── docs/                   # This documentation
```

---

## Data Model (simplified)

```
User
 └─ Proposal (created_by → User)
     ├─ ProposalModule       (DCR / NDCR panels)
     ├─ ProposalBattery      (optional, Hybrid only)
     ├─ ProposalAddon        (extra line items)
     ├─ ProposalPayment      (payment milestone schedule)
     ├─ ProposalVersion      (each PDF generation creates a version)
     │   └─ ProposalFile     (path to the generated PDF)
     ├─ AcceptedProposal     (set when status → ACCEPTED)
     └─ RejectedProposal     (set when status → REJECTED, includes reason)

Template                     (PDF template metadata, system_type: ONGRID / HYBRID)
CompanySetting               (key-value store for company info, bank details, defaults)
AuditLog                     (action, entity_type, entity_id, user_id, ip, details JSON)
```

---

## Request Flow — Generating a PDF

1. User submits the proposal form → `POST /proposals/<id>/generate`
2. `routes/proposals.py` validates the form and calls `proposal_service.build_snapshot()`
3. Snapshot (a JSON-serialisable dict of all proposal data) is stored on the `Proposal` row
4. `pdf_service.generate_pdf()` renders the appropriate Jinja2 template (`pdf/ongrid.html` or `pdf/hybrid.html`) with the snapshot
5. `xhtml2pdf` converts the rendered HTML to a PDF byte stream
6. PDF is saved to disk via `file_service` under `storage/proposals/YYYY/MM/`
7. `_stamp_letterhead()` opens the saved PDF with `pypdf`, creates an in-memory letterhead page with `reportlab`, and merges it under every content page
8. A `ProposalVersion` and `ProposalFile` record are written to the database
9. User is redirected to the proposal detail page; PDF is available for download

---

## Security Layers

| Layer | Mechanism |
|---|---|
| Authentication | Flask-Login, bcrypt password hashing |
| Session integrity | Signed cookies (`SECRET_KEY`), `SESSION_COOKIE_HTTPONLY`, `SESSION_COOKIE_SAMESITE=Lax` |
| CSRF | Flask-WTF `CSRFProtect` — token on every POST form |
| Brute force | Flask-Limiter — 10 req/min, 30 req/hr on `/login` |
| Open redirect | `_safe_next()` — validates `?next=` starts with `/`, blocks `//` and `/\` |
| HTTP headers | `X-Frame-Options: DENY`, `X-Content-Type-Options`, `Referrer-Policy` (Flask + Nginx) |
| Role access | `@login_required` on all routes; MASTER-only routes check `current_user.is_master()` |
| Audit trail | Every login (success/fail), user action, and proposal status change logged to `audit_logs` |

---

## Infrastructure (GCP)

```
GCP VM (asia-south1-c, Ubuntu 24.04)
├── MySQL 8.0                 (local, bound to 127.0.0.1)
├── Gunicorn                  (2 workers, bound to 127.0.0.1:8000)
│   └── solar-proposal.service (systemd, runs as www-data, auto-restart)
└── Nginx
    ├── :80   → inventory app (pre-existing)
    └── :8080 → solar-proposal app (proxy to Gunicorn)
```

Secrets (`SECRET_KEY`, `DB_PASSWORD`) live in `/opt/solar-proposal/.env` (`chmod 640`, owned `root:www-data`). They are generated randomly at deploy time and never committed to git.
