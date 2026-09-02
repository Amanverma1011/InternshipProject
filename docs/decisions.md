# Key Technical Decisions

A record of non-obvious choices made during development — the why behind the what.

---

## PDF Generation: xhtml2pdf over WeasyPrint

**Decision:** Use `xhtml2pdf` for HTML-to-PDF conversion.

**Why:** WeasyPrint requires GTK/Cairo native libraries, which are painful to install on Linux servers (large dependency tree, version conflicts). `xhtml2pdf` is pure Python with no native deps, making it trivially deployable via `pip` on any VM.

**Trade-off:** xhtml2pdf has weaker CSS support than WeasyPrint. Complex layouts need care.

---

## PDF Letterhead: Python stamping over CSS `position: fixed`

**Decision:** After PDF generation, stamp the letterhead PNG on every page using `reportlab` + `pypdf` in Python.

**Why:** `position: fixed` in xhtml2pdf does not reliably repeat on multi-page documents — it only renders on page 1. The Python approach (create a letterhead PDF page in memory, then `merge_page` over every content page) guarantees the letterhead appears on all pages regardless of document length.

**Implementation:** `services/pdf_service.py → _stamp_letterhead()`

---

## Rupee Symbol: `Rs.` over `₹` (U+20B9)

**Decision:** Replace `₹` with `Rs.` in all PDF templates.

**Why:** xhtml2pdf's default embedded fonts (ReportLab Type1) do not include the Rupee glyph (Unicode U+20B9, added in 2010). It renders as a black box `■`. Switching to `Rs.` is the simplest fix that works without embedding custom fonts.

---

## Continuous PDF Flow: No Manual Page Breaks

**Decision:** Remove all `<div class="page">` divs and `page-break-after: always` from PDF templates.

**Why:** The system generates proposals of variable length (different numbers of modules, add-ons, payment milestones). Forcing fixed page breaks creates either near-empty pages or content overflow. Letting xhtml2pdf paginate naturally means the PDF is always as long as it needs to be.

---

## Authentication: Flask-Login with Bcrypt Hashing

**Decision:** Use Flask-Login for session management with Werkzeug's `generate_password_hash` (bcrypt).

**Why:** Flask-Login is the de facto standard for Flask apps — minimal, well-understood, integrates cleanly with SQLAlchemy. Werkzeug's password hashing uses bcrypt with a random salt by default. No plaintext passwords are ever stored.

---

## CSRF: Flask-WTF CSRFProtect

**Decision:** Enable CSRF protection on all state-changing endpoints via `CSRFProtect`.

**Why:** All POST forms must include a CSRF token to prevent cross-site request forgery. Flask-WTF handles token generation and validation with one line of setup. Every form in the app has `{{ csrf_token() }}` hidden input.

---

## Rate Limiting: Flask-Limiter on Login Only

**Decision:** Apply rate limits only to the `/login` endpoint (`10/minute; 30/hour`), not globally.

**Why:** Global limits cause false positives for legitimate bulk operations (generating PDFs, listing proposals). The login endpoint is the only one exposed to unauthenticated traffic and the primary brute-force target.

---

## Open Redirect Prevention

**Decision:** Validate `?next=` redirect parameter with a strict whitelist function `_safe_next()`.

**Why:** A naive `redirect(next_page)` allows attackers to craft links like `?next=//evil.com` that redirect users to external sites after login. The validation requires the URL to start with `/` and explicitly blocks `//` and `/\` prefixes.

---

## Database: MySQL over SQLite

**Decision:** MySQL 8.0 in all environments (dev and production).

**Why:** SQLite has no user-level access control, limited concurrent write support, and different behaviour for some SQL constructs. Using MySQL everywhere eliminates dev/prod parity issues. SQLAlchemy abstracts the connection, so the app code stays database-agnostic.

---

## Deployment: Gunicorn + Nginx (no Docker)

**Decision:** Deploy directly on the GCP VM using a systemd service (Gunicorn) behind Nginx. No containers.

**Why:** The project is a single-server internal tool. Docker adds complexity (image builds, registry, Compose) with no benefit at this scale. Systemd gives process supervision, auto-restart, and log routing for free. Nginx handles static files, security headers, and proxying cleanly.

---

## Security Headers: Set at Both App and Nginx Layers

**Decision:** Set `X-Frame-Options`, `X-Content-Type-Options`, `Referrer-Policy` in both Flask (`after_request`) and Nginx config.

**Why:** Flask headers apply when the app handles the request. Nginx headers apply to all responses including static files served directly. Setting both ensures no response ever leaks without headers, regardless of routing.

---

## Secrets: Generated per Deployment, Never Hardcoded

**Decision:** `setup_vm.sh` generates a random `SECRET_KEY` and `DB_PASSWORD` using Python's `secrets` module at deploy time. No credentials appear in the repository.

**Why:** Hardcoded credentials in repos (even private ones) are a known attack vector. A new random secret per deployment limits blast radius if one server is compromised.
