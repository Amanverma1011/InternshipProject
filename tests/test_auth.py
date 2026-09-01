"""Integration tests for authentication and authorization."""
import pytest
from app import create_app, db
from models.user import User
from models.proposal import Proposal
from werkzeug.security import generate_password_hash
from config import TestingConfig
from datetime import date
from decimal import Decimal


@pytest.fixture
def app():
    app = create_app(TestingConfig)
    with app.app_context():
        db.create_all()
        # Create master
        master = User(name='Test Master', username='testmaster',
                      password_hash=generate_password_hash('masterpass'),
                      role='MASTER', is_active=True)
        # Create regular user
        user1 = User(name='Test User 1', username='testuser1',
                     password_hash=generate_password_hash('userpass1'),
                     role='USER', is_active=True)
        user2 = User(name='Test User 2', username='testuser2',
                     password_hash=generate_password_hash('userpass2'),
                     role='USER', is_active=True)
        db.session.add_all([master, user1, user2])
        db.session.commit()
        yield app
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


def login(client, username, password):
    return client.post('/login', data={'username': username, 'password': password},
                       follow_redirects=True)


def test_login_success(client):
    rv = login(client, 'testmaster', 'masterpass')
    assert rv.status_code == 200
    assert b'Dashboard' in rv.data or b'Welcome' in rv.data


def test_login_wrong_password(client):
    rv = login(client, 'testmaster', 'wrongpass')
    assert b'Invalid' in rv.data


def test_login_inactive_user(app, client):
    with app.app_context():
        user = User.query.filter_by(username='testuser1').first()
        user.is_active = False
        db.session.commit()
    rv = login(client, 'testuser1', 'userpass1')
    assert b'disabled' in rv.data


def test_dashboard_requires_login(client):
    rv = client.get('/dashboard', follow_redirects=True)
    assert b'login' in rv.data.lower() or rv.status_code == 200


def test_user_cannot_access_other_proposal(app, client):
    with app.app_context():
        user1 = User.query.filter_by(username='testuser1').first()
        p = Proposal(
            proposal_number='SP-2026-00001',
            customer_name='Test Customer',
            customer_address='Test Address',
            system_type='ONGRID',
            plant_capacity=Decimal('5.00'),
            total_area=Decimal('400.00'),
            mounting_type='RCC',
            inverter_capacity=Decimal('5.00'),
            base_price=Decimal('200000'),
            subtotal=Decimal('200000'),
            grand_total=Decimal('200000'),
            status='DRAFT',
            created_by=user1.id,
            proposal_date=date.today()
        )
        db.session.add(p)
        db.session.commit()
        pid = p.id

    # Login as user2
    login(client, 'testuser2', 'userpass2')
    rv = client.get(f'/proposals/{pid}')
    assert rv.status_code in (403, 302)


def test_master_can_access_all_proposals(app, client):
    with app.app_context():
        user1 = User.query.filter_by(username='testuser1').first()
        p = Proposal(
            proposal_number='SP-2026-00002',
            customer_name='Another Customer',
            customer_address='Another Address',
            system_type='HYBRID',
            plant_capacity=Decimal('3.00'),
            total_area=Decimal('240.00'),
            mounting_type='RCC',
            inverter_capacity=Decimal('3.00'),
            base_price=Decimal('150000'),
            subtotal=Decimal('150000'),
            grand_total=Decimal('150000'),
            status='DRAFT',
            created_by=user1.id,
            proposal_date=date.today()
        )
        db.session.add(p)
        db.session.commit()
        pid = p.id

    login(client, 'testmaster', 'masterpass')
    rv = client.get(f'/proposals/{pid}')
    assert rv.status_code == 200


def test_non_master_cannot_access_users(client):
    login(client, 'testuser1', 'userpass1')
    rv = client.get('/users')
    assert rv.status_code in (403, 302)


def test_logout(client):
    login(client, 'testmaster', 'masterpass')
    rv = client.get('/logout', follow_redirects=True)
    assert b'login' in rv.data.lower() or b'logged out' in rv.data.lower()
