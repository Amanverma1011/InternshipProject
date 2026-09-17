"""Shared fixtures and helpers for the test suite.

Uses MySQL sologix_test database (same tech stack as production).

One-time setup on GCP server (run as root, once):
    mysql -u root -p <<'SQL'
    CREATE DATABASE IF NOT EXISTS sologix_test
        CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
    GRANT ALL PRIVILEGES ON sologix_test.* TO 'sologix_app'@'localhost';
    FLUSH PRIVILEGES;
    SQL
"""
import json
import os
import re
import shutil
import tempfile
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import text
from werkzeug.datastructures import MultiDict
from werkzeug.security import generate_password_hash

from app import create_app
from config import TestingProdConfig
from models import db as _db
from models.company import CompanySetting
from models.proposal import (
    Proposal, ProposalModule, ProposalBattery,
    ProposalAddon, ProposalPayment,
)
from models.template import Template
from models.user import User

# ---------------------------------------------------------------------------
# CSRF helpers
# ---------------------------------------------------------------------------

_CSRF_RE = re.compile(rb'name="csrf_token"\s+value="([^"]+)"')


def _extract_csrf(html_bytes):
    m = _CSRF_RE.search(html_bytes)
    return m.group(1).decode() if m else ''


def get_csrf(client, url='/login'):
    """Return CSRF token from the given page (follows redirects)."""
    rv = client.get(url, follow_redirects=True)
    return _extract_csrf(rv.data)


# ---------------------------------------------------------------------------
# Auth helpers (importable by test modules)
# ---------------------------------------------------------------------------

def login(client, username, password):
    token = get_csrf(client, '/login')
    return client.post('/login', data={
        'username': username, 'password': password, 'csrf_token': token,
    }, follow_redirects=True)


def logout(client):
    return client.get('/logout', follow_redirects=True)


def post_form(client, url, data, ref_url=None):
    """GET ref_url to grab CSRF token, then POST url with that token.

    ref_url defaults to /proposals/new — accessible to any logged-in user
    and falls through to /login for unauthenticated requests, both of which
    render a CSRF-bearing form.

    If ref_url returns a page with no CSRF form (e.g. an ACCEPTED/REJECTED
    proposal detail page whose action buttons are hidden, or a 403 page),
    falls back to /proposals/new which always has one for authenticated users.
    """
    ref = ref_url or '/proposals/new'
    rv = client.get(ref, follow_redirects=True)
    token = _extract_csrf(rv.data)
    if not token:
        rv = client.get('/proposals/new', follow_redirects=True)
        token = _extract_csrf(rv.data)
    if isinstance(data, list):
        full = MultiDict(data + [('csrf_token', token)])
    else:
        full = {**data, 'csrf_token': token}
    return client.post(url, data=full, follow_redirects=True)


def post_anon(client, url, data):
    """POST without being logged in but with a valid CSRF token.

    Gets CSRF from /login (no auth required), then POSTs without following
    the redirect — callers typically assert status_code == 302.
    """
    token = get_csrf(client, '/login')
    if isinstance(data, list):
        full = MultiDict(data + [('csrf_token', token)])
    else:
        full = {**data, 'csrf_token': token}
    return client.post(url, data=full, follow_redirects=False)


def post_json_csrf(client, url, payload):
    """POST JSON with X-CSRFToken header (for /api/* endpoints).

    Works whether the user is logged in or not: /proposals/new falls through
    to /login for anon users, and both pages have a CSRF token in their form.
    """
    token = get_csrf(client, '/proposals/new')
    return client.post(
        url,
        data=json.dumps(payload),
        content_type='application/json',
        headers={'X-CSRFToken': token},
    )


# ---------------------------------------------------------------------------
# Session-level: ensure sologix_test database exists
# ---------------------------------------------------------------------------

@pytest.fixture(scope='session', autouse=True)
def mysql_test_db():
    """Create sologix_test DB if the app user has CREATE privilege.

    If the DB was pre-created manually (see module docstring), the
    IF NOT EXISTS makes this a no-op.
    """
    import pymysql
    kw = dict(
        host=os.getenv('DB_HOST', '127.0.0.1'),
        port=int(os.getenv('DB_PORT', '3306')),
        user=os.getenv('DB_USER', 'sologix_app'),
        password=os.getenv('DB_PASSWORD', ''),
        charset='utf8mb4',
    )
    try:
        conn = pymysql.connect(**kw)
        with conn.cursor() as cur:
            cur.execute(
                'CREATE DATABASE IF NOT EXISTS sologix_test '
                'CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci'
            )
        conn.commit()
        conn.close()
    except Exception:
        # Insufficient privilege or DB already exists — continue anyway.
        pass
    yield


# ---------------------------------------------------------------------------
# App + DB — function-scoped so each test gets a clean MySQL database state
# ---------------------------------------------------------------------------

@pytest.fixture
def app(tmp_path, mysql_test_db):
    """Function-scoped Flask app pointing at sologix_test MySQL database.

    Creates all tables, seeds base data, yields the app, then drops all
    tables.  Never touches the production sologix_proposals database.
    """
    cfg = TestingProdConfig()
    cfg.STORAGE_PATH = str(tmp_path / 'solar_test_storage')
    os.makedirs(cfg.STORAGE_PATH, exist_ok=True)

    application = create_app(cfg)
    with application.app_context():
        _db.create_all()
        _seed_base_data()
    yield application
    with application.app_context():
        _db.session.remove()
        # MySQL FK constraints block naive drop_all ordering — disable checks
        # on the same connection used for the DROP statements.
        with _db.engine.begin() as conn:
            conn.execute(text('SET FOREIGN_KEY_CHECKS = 0'))
            _db.metadata.drop_all(conn)
            conn.execute(text('SET FOREIGN_KEY_CHECKS = 1'))


@pytest.fixture
def client(app):
    return app.test_client()


# ---------------------------------------------------------------------------
# Seed helpers
# ---------------------------------------------------------------------------

def _seed_base_data():
    master = User(name='Test Master', username='testmaster',
                  password_hash=generate_password_hash('Admin@1234'),
                  role='MASTER', is_active=True)
    user1 = User(name='Test User One', username='testuser1',
                 password_hash=generate_password_hash('User@1111'),
                 role='USER', is_active=True)
    user2 = User(name='Test User Two', username='testuser2',
                 password_hash=generate_password_hash('User@2222'),
                 role='USER', is_active=True)
    inactive = User(name='Inactive User', username='inactive',
                    password_hash=generate_password_hash('Inactive@1'),
                    role='USER', is_active=False)
    _db.session.add_all([master, user1, user2, inactive])
    _db.session.flush()

    ongrid_tpl = Template(name='Ongrid v1', system_type='ONGRID', version=1,
                          is_active=True, html_file='pdf/ongrid.html',
                          created_by=master.id)
    hybrid_tpl = Template(name='Hybrid v1', system_type='HYBRID', version=1,
                          is_active=True, html_file='pdf/hybrid.html',
                          created_by=master.id)
    _db.session.add_all([ongrid_tpl, hybrid_tpl])

    for key, value in _COMPANY_SETTINGS.items():
        _db.session.add(CompanySetting(key=key, value=value))

    _db.session.commit()


_COMPANY_SETTINGS = {
    'company_name': 'Sologix Energy Private Limited',
    'bank_account_number': '125009426214',
    'bank_account_name': 'Sologix Energy Private Limited',
    'bank_name': 'Canara Bank, Chutia, Ranchi - 834001',
    'bank_ifsc': 'CNRB0001969',
    'bank_upi_id': '8287766474@okbizaxis',
    'cfa_amount': '78000',
    'tilt_angle': '15-22 degrees',
    'dcr_module_wattage': '580W-620W',
    'ndcr_module_wattage': '580W-620W',
    'inverter_makes': 'Growatt / Deye',
    'mounting_structure_make': 'HDGI',
    'earthing_quantity': '3 nos.',
    'lightning_arrestor_quantity': '1 no.',
    'warranty_module_defect': '12 Years warranty on solar modules',
    'warranty_module_performance': '30 Years linear performance guarantee',
    'warranty_inverter': '8 years warranty on inverters.',
    'payment_reminder': 'Do not forget to collect receipt.',
    'company_signatory': '2nd Floor, STPI, Namkum, Ranchi- 834010',
}


# ---------------------------------------------------------------------------
# Proposal builder (creates directly in DB — no HTTP)
# ---------------------------------------------------------------------------

def make_proposal(user_id, system_type='ONGRID', capacity=5.0,
                  base_price=275000.0, status='DRAFT',
                  num_suffix=None, include_payments=True):
    """Insert a Proposal + modules + optional payments into the current DB session."""
    import random
    if num_suffix is None:
        num_suffix = random.randint(10000, 99999)

    p = Proposal(
        proposal_number=f'SP-TEST-{num_suffix:05d}',
        customer_name='Test Customer',
        customer_address='123 Test Street, Ranchi - 834001',
        customer_contact='9876543210',
        system_type=system_type,
        plant_capacity=Decimal(str(capacity)),
        total_area=Decimal(str(capacity * 80)),
        mounting_type='RCC',
        tilt_angle='15-22 degrees',
        inverter_capacity=Decimal(str(capacity)),
        base_price=Decimal(str(base_price)),
        addon_total=Decimal('0'),
        subtotal=Decimal(str(base_price)),
        discount_percent=Decimal('0'),
        discount_amount=Decimal('0'),
        grand_total=Decimal(str(base_price)),
        cfa_amount=Decimal('78000'),
        status=status,
        proposal_date=date.today(),
        created_by=user_id,
    )
    _db.session.add(p)
    _db.session.flush()

    _db.session.add(ProposalModule(
        proposal_id=p.id, module_type='DCR',
        quantity=9, wattage='580W-620W', make='Rayzon Solar'
    ))

    if include_payments:
        half = Decimal(str(base_price)) / 2
        _db.session.add(ProposalPayment(
            proposal_id=p.id, sequence=1,
            milestone='Signing of Proposal', amount=half
        ))
        _db.session.add(ProposalPayment(
            proposal_id=p.id, sequence=2,
            milestone='On Commissioning', amount=half
        ))

    _db.session.commit()
    return p
