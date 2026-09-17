"""Security tests — access control, injection, XSS, edge cases."""
import pytest
from tests.conftest import login, make_proposal, post_form, post_anon, get_csrf
from models import db
from models.proposal import Proposal
from models.user import User


# ---------------------------------------------------------------------------
# Unauthenticated access to every protected route
# ---------------------------------------------------------------------------

PROTECTED_ROUTES_GET = [
    '/dashboard',
    '/',
    '/proposals',
    '/proposals/new',
    '/proposals/1',
    '/proposals/1/edit',
    '/users',
    '/users/new',
]

PROTECTED_ROUTES_POST = [
    ('/proposals/new', {}),
    ('/proposals/1/generate', {}),
    ('/proposals/1/accept', {'notes': ''}),
    ('/proposals/1/reject', {'reason': 'Test'}),
    ('/users/new', {}),
    ('/users/1/toggle', {}),
    ('/users/1/reset-password', {'new_password': 'Test@1234'}),
]


@pytest.mark.parametrize('path', PROTECTED_ROUTES_GET)
def test_unauthenticated_get_redirects_to_login(client, path):
    rv = client.get(path, follow_redirects=False)
    assert rv.status_code == 302
    assert 'login' in rv.headers.get('Location', '').lower()


@pytest.mark.parametrize('path,data', PROTECTED_ROUTES_POST)
def test_unauthenticated_post_redirects_to_login(client, path, data):
    # post_anon provides a valid CSRF token so CSRF check passes;
    # login_required then fires and returns 302 → /login
    rv = post_anon(client, path, data)
    assert rv.status_code == 302
    assert 'login' in rv.headers.get('Location', '').lower()


# ---------------------------------------------------------------------------
# Cross-user access (user cannot touch another user's proposal)
# ---------------------------------------------------------------------------

def test_user2_cannot_view_user1_proposal(app, client):
    with app.app_context():
        u1 = User.query.filter_by(username='testuser1').first()
        p = make_proposal(u1.id, num_suffix=90001)
        pid = p.id
    login(client, 'testuser2', 'User@2222')
    rv = client.get(f'/proposals/{pid}')
    assert rv.status_code == 403


def test_user2_cannot_edit_user1_proposal(app, client):
    with app.app_context():
        u1 = User.query.filter_by(username='testuser1').first()
        p = make_proposal(u1.id, num_suffix=90002)
        pid = p.id
    login(client, 'testuser2', 'User@2222')
    rv = post_form(client, f'/proposals/{pid}/edit', {})
    assert rv.status_code == 403


def test_user2_cannot_generate_user1_proposal(app, client):
    with app.app_context():
        u1 = User.query.filter_by(username='testuser1').first()
        p = make_proposal(u1.id, num_suffix=90003)
        pid = p.id
    login(client, 'testuser2', 'User@2222')
    rv = post_form(client, f'/proposals/{pid}/generate', {},
                   ref_url=f'/proposals/{pid}')
    assert rv.status_code == 403


def test_user2_cannot_accept_user1_proposal(app, client):
    with app.app_context():
        u1 = User.query.filter_by(username='testuser1').first()
        p = make_proposal(u1.id, status='GENERATED', num_suffix=90004)
        pid = p.id
    login(client, 'testuser2', 'User@2222')
    rv = post_form(client, f'/proposals/{pid}/accept', {'notes': ''},
                   ref_url=f'/proposals/{pid}')
    assert rv.status_code == 403


def test_user2_cannot_reject_user1_proposal(app, client):
    with app.app_context():
        u1 = User.query.filter_by(username='testuser1').first()
        p = make_proposal(u1.id, status='GENERATED', num_suffix=90005)
        pid = p.id
    login(client, 'testuser2', 'User@2222')
    rv = post_form(client, f'/proposals/{pid}/reject', {'reason': 'Hack'},
                   ref_url=f'/proposals/{pid}')
    assert rv.status_code == 403


def test_user2_cannot_download_user1_proposal(app, client):
    with app.app_context():
        u1 = User.query.filter_by(username='testuser1').first()
        p = make_proposal(u1.id, status='GENERATED', num_suffix=90006)
        pid = p.id
    login(client, 'testuser2', 'User@2222')
    rv = client.get(f'/proposals/{pid}/download')
    assert rv.status_code == 403


# ---------------------------------------------------------------------------
# Non-master cannot access user management
# ---------------------------------------------------------------------------

def test_regular_user_cannot_list_users(client):
    login(client, 'testuser1', 'User@1111')
    rv = client.get('/users')
    assert rv.status_code == 403


def test_regular_user_cannot_create_user(client):
    login(client, 'testuser1', 'User@1111')
    rv = post_form(client, '/users/new', {
        'name': 'Hack', 'username': 'hack', 'password': 'Hack@123', 'role': 'USER',
    }, ref_url='/proposals/new')
    assert rv.status_code == 403


def test_regular_user_cannot_toggle_user(app, client):
    login(client, 'testuser1', 'User@1111')
    with app.app_context():
        u2 = User.query.filter_by(username='testuser2').first()
        uid = u2.id
    rv = post_form(client, f'/users/{uid}/toggle', {})
    assert rv.status_code == 403


def test_regular_user_cannot_reset_password(app, client):
    login(client, 'testuser1', 'User@1111')
    with app.app_context():
        u2 = User.query.filter_by(username='testuser2').first()
        uid = u2.id
    rv = post_form(client, f'/users/{uid}/reset-password',
                   {'new_password': 'Hack@1234'})
    assert rv.status_code == 403


# ---------------------------------------------------------------------------
# 404 on nonexistent resources
# ---------------------------------------------------------------------------

def test_nonexistent_proposal_returns_404(client):
    login(client, 'testmaster', 'Admin@1234')
    rv = client.get('/proposals/999999')
    assert rv.status_code == 404


def test_download_nonexistent_proposal_returns_404(client):
    login(client, 'testmaster', 'Admin@1234')
    rv = client.get('/proposals/999999/download')
    assert rv.status_code == 404


def test_nonexistent_user_toggle_returns_404(client):
    login(client, 'testmaster', 'Admin@1234')
    rv = post_form(client, '/users/999999/toggle', {}, ref_url='/users')
    assert rv.status_code == 404


def test_nonexistent_user_reset_password_returns_404(client):
    login(client, 'testmaster', 'Admin@1234')
    rv = post_form(client, '/users/999999/reset-password',
                   {'new_password': 'Test@1234'}, ref_url='/users')
    assert rv.status_code == 404


# ---------------------------------------------------------------------------
# XSS — customer name stored and rendered safely
# ---------------------------------------------------------------------------

def test_xss_customer_name_escaped_in_detail(app, client):
    """Script tags in customer_name must be escaped in the HTML response."""
    login(client, 'testmaster', 'Admin@1234')
    with app.app_context():
        master = User.query.filter_by(username='testmaster').first()
        p = make_proposal(master.id, num_suffix=91001)
        p.customer_name = '<script>alert("xss")</script>'
        db.session.commit()
        pid = p.id
    rv = client.get(f'/proposals/{pid}')
    assert b'<script>alert' not in rv.data
    assert b'&lt;script&gt;' in rv.data or b'alert' not in rv.data


# ---------------------------------------------------------------------------
# CSRF is enabled in both test and production configs
# ---------------------------------------------------------------------------

def test_csrf_enabled_in_test_config(app):
    assert app.config['WTF_CSRF_ENABLED'] is True


def test_csrf_enabled_in_production_config():
    from config import ProductionConfig
    assert ProductionConfig.WTF_CSRF_ENABLED is True


# ---------------------------------------------------------------------------
# open_redirect via next= param
# ---------------------------------------------------------------------------

def test_open_redirect_via_next_blocked(client):
    token = get_csrf(client, '/login')
    rv = client.post('/login?next=http://evil.com', data={
        'username': 'testmaster', 'password': 'Admin@1234', 'csrf_token': token,
    })
    location = rv.headers.get('Location', '')
    assert 'evil.com' not in location


def test_open_redirect_double_slash_blocked(client):
    token = get_csrf(client, '/login')
    rv = client.post('/login?next=//evil.com', data={
        'username': 'testmaster', 'password': 'Admin@1234', 'csrf_token': token,
    })
    location = rv.headers.get('Location', '')
    assert 'evil.com' not in location


# ---------------------------------------------------------------------------
# Inactive user cannot log in even with correct password
# ---------------------------------------------------------------------------

def test_inactive_user_blocked_after_deactivation(app, client):
    with app.app_context():
        u = User.query.filter_by(username='testuser1').first()
        u.is_active = False
        db.session.commit()
    rv = login(client, 'testuser1', 'User@1111')
    assert b'disabled' in rv.data
    # Restore
    with app.app_context():
        u = User.query.filter_by(username='testuser1').first()
        u.is_active = True
        db.session.commit()
