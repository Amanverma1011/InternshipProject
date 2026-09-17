"""Integration tests for authentication and authorization."""
import pytest
from tests.conftest import login, logout, get_csrf


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------

def test_login_success_master(client):
    rv = login(client, 'testmaster', 'Admin@1234')
    assert rv.status_code == 200
    assert b'Dashboard' in rv.data or b'Welcome' in rv.data


def test_login_success_user(client):
    rv = login(client, 'testuser1', 'User@1111')
    assert rv.status_code == 200
    assert b'Dashboard' in rv.data or b'Welcome' in rv.data


def test_login_wrong_password(client):
    rv = login(client, 'testmaster', 'wrongpassword')
    assert b'Invalid' in rv.data


def test_login_wrong_username(client):
    rv = login(client, 'nobody', 'Admin@1234')
    assert b'Invalid' in rv.data


def test_login_empty_username(client):
    rv = login(client, '', 'Admin@1234')
    assert b'Invalid' in rv.data


def test_login_empty_password(client):
    rv = login(client, 'testmaster', '')
    assert b'Invalid' in rv.data


def test_login_inactive_user(client):
    rv = login(client, 'inactive', 'Inactive@1')
    assert b'disabled' in rv.data


def test_login_case_sensitive_username(client):
    """Usernames are case-sensitive."""
    rv = login(client, 'TESTMASTER', 'Admin@1234')
    assert b'Invalid' in rv.data


def test_login_redirects_to_dashboard(client):
    token = get_csrf(client, '/login')
    rv = client.post('/login', data={
        'username': 'testmaster', 'password': 'Admin@1234', 'csrf_token': token,
    })
    assert rv.status_code == 302
    assert 'dashboard' in rv.headers.get('Location', '').lower()


def test_login_already_authenticated_redirects(client):
    login(client, 'testmaster', 'Admin@1234')
    rv = client.get('/login', follow_redirects=True)
    assert b'Dashboard' in rv.data or rv.status_code == 200


# ---------------------------------------------------------------------------
# Logout
# ---------------------------------------------------------------------------

def test_logout(client):
    login(client, 'testmaster', 'Admin@1234')
    rv = logout(client)
    assert b'logged out' in rv.data.lower() or b'login' in rv.data.lower()


def test_logout_requires_login(client):
    rv = client.get('/logout')
    assert rv.status_code == 302


def test_session_cleared_after_logout(client):
    login(client, 'testmaster', 'Admin@1234')
    logout(client)
    rv = client.get('/proposals', follow_redirects=False)
    assert rv.status_code == 302
    assert 'login' in rv.headers.get('Location', '').lower()


# ---------------------------------------------------------------------------
# Protected route access (unauthenticated)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize('path', [
    '/dashboard',
    '/proposals',
    '/proposals/new',
    '/proposals/1',
    '/users',
])
def test_protected_routes_require_login(client, path):
    rv = client.get(path, follow_redirects=False)
    assert rv.status_code == 302
    assert 'login' in rv.headers.get('Location', '').lower()


# ---------------------------------------------------------------------------
# next_url redirect
# ---------------------------------------------------------------------------

def test_next_url_after_login(client):
    """After login with a ?next= param, redirects there."""
    token = get_csrf(client, '/login')
    rv = client.post('/login?next=/proposals', data={
        'username': 'testmaster', 'password': 'Admin@1234', 'csrf_token': token,
    })
    assert rv.status_code == 302
    assert '/proposals' in rv.headers.get('Location', '')


def test_next_url_rejects_absolute(client):
    """Absolute URL in next= should not redirect off-site."""
    token = get_csrf(client, '/login')
    rv = client.post('/login?next=http://evil.com', data={
        'username': 'testmaster', 'password': 'Admin@1234', 'csrf_token': token,
    })
    location = rv.headers.get('Location', '')
    assert 'evil.com' not in location
