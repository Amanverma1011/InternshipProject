"""Tests for user management routes (master-only)."""
import pytest
from tests.conftest import login, post_form
from models import db
from models.user import User


# ---------------------------------------------------------------------------
# List users
# ---------------------------------------------------------------------------

def test_list_users_master(client):
    login(client, 'testmaster', 'Admin@1234')
    rv = client.get('/users')
    assert rv.status_code == 200
    assert b'testuser1' in rv.data


def test_list_users_regular_user_gets_403(client):
    login(client, 'testuser1', 'User@1111')
    rv = client.get('/users')
    assert rv.status_code == 403


def test_list_users_unauthenticated_redirects(client):
    rv = client.get('/users', follow_redirects=False)
    assert rv.status_code == 302
    assert 'login' in rv.headers.get('Location', '').lower()


# ---------------------------------------------------------------------------
# Create user
# ---------------------------------------------------------------------------

def test_create_user_success(client):
    login(client, 'testmaster', 'Admin@1234')
    rv = post_form(client, '/users/new', {
        'name': 'New Person',
        'username': 'newperson',
        'password': 'NewPass@99',
        'role': 'USER',
    }, ref_url='/users/new')
    assert rv.status_code == 200
    assert b'created' in rv.data.lower()


def test_create_user_non_master_gets_403(client):
    login(client, 'testuser1', 'User@1111')
    rv = post_form(client, '/users/new', {
        'name': 'Sneaky User',
        'username': 'sneaky',
        'password': 'Sneaky@123',
        'role': 'USER',
    })
    assert rv.status_code == 403


def test_create_user_duplicate_username(client):
    login(client, 'testmaster', 'Admin@1234')
    rv = post_form(client, '/users/new', {
        'name': 'Duplicate',
        'username': 'testuser1',  # already exists
        'password': 'Test@1234',
        'role': 'USER',
    }, ref_url='/users/new')
    assert b'already exists' in rv.data


def test_create_user_empty_username(client):
    login(client, 'testmaster', 'Admin@1234')
    rv = post_form(client, '/users/new', {
        'name': 'No Username',
        'username': '',
        'password': 'Test@1234',
        'role': 'USER',
    }, ref_url='/users/new')
    assert b'required' in rv.data.lower()


def test_create_user_empty_name(client):
    login(client, 'testmaster', 'Admin@1234')
    rv = post_form(client, '/users/new', {
        'name': '',
        'username': 'noname99',
        'password': 'Test@1234',
        'role': 'USER',
    }, ref_url='/users/new')
    assert b'required' in rv.data.lower()


def test_create_user_short_password(client):
    login(client, 'testmaster', 'Admin@1234')
    rv = post_form(client, '/users/new', {
        'name': 'Short PW',
        'username': 'shortpw',
        'password': 'abc',
        'role': 'USER',
    }, ref_url='/users/new')
    assert b'6 characters' in rv.data or b'at least' in rv.data.lower()


def test_create_master_user(client):
    login(client, 'testmaster', 'Admin@1234')
    rv = post_form(client, '/users/new', {
        'name': 'Second Master',
        'username': 'master2',
        'password': 'Master@9999',
        'role': 'MASTER',
    }, ref_url='/users/new')
    assert rv.status_code == 200
    assert b'created' in rv.data.lower()


# ---------------------------------------------------------------------------
# Toggle user active/inactive
# ---------------------------------------------------------------------------

def test_toggle_user_deactivate(app, client):
    login(client, 'testmaster', 'Admin@1234')
    with app.app_context():
        u = User.query.filter_by(username='testuser1').first()
        uid = u.id

    rv = post_form(client, f'/users/{uid}/toggle', {}, ref_url='/users')
    assert rv.status_code == 200
    assert b'disabled' in rv.data.lower() or b'enabled' in rv.data.lower()


def test_toggle_master_own_account_blocked(app, client):
    login(client, 'testmaster', 'Admin@1234')
    with app.app_context():
        master = User.query.filter_by(username='testmaster').first()
        mid = master.id
    rv = post_form(client, f'/users/{mid}/toggle', {}, ref_url='/users')
    assert b'Cannot change your own' in rv.data


def test_toggle_nonmaster_gets_403(app, client):
    login(client, 'testuser1', 'User@1111')
    with app.app_context():
        u2 = User.query.filter_by(username='testuser2').first()
        uid = u2.id
    rv = post_form(client, f'/users/{uid}/toggle', {})
    assert rv.status_code == 403


# ---------------------------------------------------------------------------
# Reset password
# ---------------------------------------------------------------------------

def test_reset_password_success(app, client):
    login(client, 'testmaster', 'Admin@1234')
    with app.app_context():
        u = User.query.filter_by(username='testuser1').first()
        uid = u.id
    rv = post_form(client, f'/users/{uid}/reset-password',
                   {'new_password': 'NewPass@999'}, ref_url='/users')
    assert rv.status_code == 200
    assert b'reset' in rv.data.lower()


def test_reset_password_too_short(app, client):
    login(client, 'testmaster', 'Admin@1234')
    with app.app_context():
        u = User.query.filter_by(username='testuser1').first()
        uid = u.id
    rv = post_form(client, f'/users/{uid}/reset-password',
                   {'new_password': 'abc'}, ref_url='/users')
    assert b'6 characters' in rv.data or b'at least' in rv.data.lower()


def test_reset_password_non_master_gets_403(app, client):
    login(client, 'testuser1', 'User@1111')
    with app.app_context():
        u2 = User.query.filter_by(username='testuser2').first()
        uid = u2.id
    rv = post_form(client, f'/users/{uid}/reset-password',
                   {'new_password': 'NewPass@999'})
    assert rv.status_code == 403


def test_reset_password_nonexistent_user(client):
    login(client, 'testmaster', 'Admin@1234')
    rv = post_form(client, '/users/999999/reset-password',
                   {'new_password': 'NewPass@999'}, ref_url='/users')
    assert rv.status_code == 404
