"""Tests for the /api/calculate JSON endpoint."""
import json
import pytest
from tests.conftest import login, post_json_csrf, post_form


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def api_calculate(client, payload):
    """POST /api/calculate with CSRF header (works logged-in or anon)."""
    return post_json_csrf(client, '/api/calculate', payload)


# ---------------------------------------------------------------------------
# Authentication guard
# ---------------------------------------------------------------------------

def test_api_calculate_requires_login(client):
    # Not logged in: CSRF passes, login_required fires → 302
    rv = api_calculate(client, {'plant_capacity': 5, 'base_price': 275000,
                                'addons': [], 'discount_percent': 0, 'payments': []})
    assert rv.status_code == 302


# ---------------------------------------------------------------------------
# Valid requests
# ---------------------------------------------------------------------------

def test_api_calculate_basic(client):
    login(client, 'testmaster', 'Admin@1234')
    rv = api_calculate(client, {
        'plant_capacity': 5, 'base_price': 275000,
        'addons': [], 'discount_percent': 0, 'payments': [],
    })
    assert rv.status_code == 200
    data = rv.get_json()
    assert data['total_area'] == 400.0
    assert data['inverter_capacity'] == 5.0
    assert data['grand_total'] == 275000.0
    assert data['addon_total'] == 0.0
    assert data['discount_amount'] == 0.0
    assert data['errors'] == []


def test_api_calculate_with_addons(client):
    login(client, 'testmaster', 'Admin@1234')
    rv = api_calculate(client, {
        'plant_capacity': 5, 'base_price': 200000,
        'addons': [{'name': 'Earthing', 'amount': 10000},
                   {'name': 'AMC', 'amount': 5000}],
        'discount_percent': 0, 'payments': [],
    })
    assert rv.status_code == 200
    data = rv.get_json()
    assert data['addon_total'] == 15000.0
    assert data['grand_total'] == 215000.0


def test_api_calculate_with_discount(client):
    login(client, 'testmaster', 'Admin@1234')
    rv = api_calculate(client, {
        'plant_capacity': 5, 'base_price': 100000,
        'addons': [], 'discount_percent': 10, 'payments': [],
    })
    assert rv.status_code == 200
    data = rv.get_json()
    assert data['discount_amount'] == 10000.0
    assert data['grand_total'] == 90000.0


def test_api_calculate_payment_match(client):
    login(client, 'testmaster', 'Admin@1234')
    rv = api_calculate(client, {
        'plant_capacity': 5, 'base_price': 275000,
        'addons': [], 'discount_percent': 0,
        'payments': [{'milestone': 'Signing', 'amount': 275000}],
    })
    assert rv.status_code == 200
    data = rv.get_json()
    assert data['errors'] == []
    assert data['payment_total'] == 275000.0


def test_api_calculate_payment_mismatch(client):
    login(client, 'testmaster', 'Admin@1234')
    rv = api_calculate(client, {
        'plant_capacity': 5, 'base_price': 275000,
        'addons': [], 'discount_percent': 0,
        'payments': [{'milestone': 'Signing', 'amount': 100000}],
    })
    assert rv.status_code == 200
    data = rv.get_json()
    assert len(data['errors']) == 1
    assert 'does not match' in data['errors'][0]


def test_api_calculate_100_percent_discount(client):
    login(client, 'testmaster', 'Admin@1234')
    rv = api_calculate(client, {
        'plant_capacity': 5, 'base_price': 275000,
        'addons': [], 'discount_percent': 100, 'payments': [],
    })
    assert rv.status_code == 200
    data = rv.get_json()
    assert data['grand_total'] == 0.0


def test_api_calculate_large_system(client):
    login(client, 'testmaster', 'Admin@1234')
    rv = api_calculate(client, {
        'plant_capacity': 100, 'base_price': 5500000,
        'addons': [], 'discount_percent': 0, 'payments': [],
    })
    assert rv.status_code == 200
    data = rv.get_json()
    assert data['total_area'] == 8000.0
    assert data['inverter_capacity'] == 100.0


# ---------------------------------------------------------------------------
# Error cases
# ---------------------------------------------------------------------------

def test_api_calculate_no_body(client):
    # JSON null is parsed as Python None → route returns 400 "No data".
    # This exercises the same code path as a missing/empty body while
    # avoiding werkzeug test-client quirks with truly empty bodies.
    login(client, 'testmaster', 'Admin@1234')
    rv = api_calculate(client, None)
    assert rv.status_code == 400
    data = rv.get_json()
    assert data is not None
    assert data.get('error') == 'No data'


def test_api_calculate_non_json_content_type(client):
    # Flask 3.x returns 415 for wrong media type; older versions return 400.
    # post_form sends application/x-www-form-urlencoded with CSRF in form data.
    login(client, 'testmaster', 'Admin@1234')
    rv = post_form(client, '/api/calculate', {'plant_capacity': '5'},
                   ref_url='/proposals/new')
    assert rv.status_code in (400, 415)


def test_api_calculate_missing_fields_use_defaults(client):
    """Empty JSON body {} should use defaults (0) and return 200."""
    login(client, 'testmaster', 'Admin@1234')
    rv = api_calculate(client, {})
    assert rv.status_code == 200
    data = rv.get_json()
    assert data is not None
    assert 'grand_total' in data


def test_api_calculate_invalid_capacity_type(client):
    login(client, 'testmaster', 'Admin@1234')
    rv = api_calculate(client, {
        'plant_capacity': 'not_a_number', 'base_price': 100000,
        'addons': [], 'discount_percent': 0, 'payments': [],
    })
    assert rv.status_code == 400
    assert 'error' in rv.get_json()
