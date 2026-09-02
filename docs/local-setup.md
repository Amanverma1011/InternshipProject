# Local Development Setup

## Prerequisites

- Python 3.10+
- MySQL 8.0+
- Git

---

## 1. Clone the repository

```bash
git clone https://github.com/Amanverma1011/InternshipProject.git
cd InternshipProject
```

## 2. Create a virtual environment

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate
```

## 3. Install dependencies

```bash
pip install -r requirements.txt
```

## 4. Set up the database

Log into MySQL as root and run the schema:

```bash
mysql -u root -p < database/schema.sql
```

This creates the `sologix_proposals` database and a `sologix_app` user with the default password `SologixApp2026!`.

## 5. Configure environment variables

Copy the example file and fill in your values:

```bash
cp .env.example .env
```

Minimum required `.env` for local dev:

```env
FLASK_ENV=development
SECRET_KEY=any-random-string-for-dev
DB_HOST=127.0.0.1
DB_PORT=3306
DB_NAME=sologix_proposals
DB_USER=sologix_app
DB_PASSWORD=SologixApp2026!
STORAGE_PATH=storage/proposals
SESSION_COOKIE_SECURE=false
```

## 6. Seed the database

```bash
python database/seed_auto.py
```

Default master credentials created:
- **Username:** `master`
- **Password:** `Admin@1234`

## 7. Run the development server

```bash
python app.py
```

App runs at `http://127.0.0.1:5000`.

---

## Running tests

```bash
pytest tests/
```

---

## Placing the letterhead

Put your A4-sized letterhead PNG at:

```
static/images/letterhead.png
```

It is stamped on every generated PDF page via Python (reportlab + pypdf). The file is not committed to git since it contains company branding.
