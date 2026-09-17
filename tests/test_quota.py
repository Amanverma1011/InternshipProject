"""Tests for quota service — unit (mocked) and integration (real DB via conftest)."""
import pytest
from unittest.mock import MagicMock, patch
from services.quota_service import MAX_DAILY_PROPOSALS, check_quota, enforce_quota_with_lock


# ---------------------------------------------------------------------------
# Unit tests (no DB, mocked)
# ---------------------------------------------------------------------------

def test_max_daily_limit_constant():
    assert MAX_DAILY_PROPOSALS == 10


def test_master_always_unlimited():
    master = MagicMock()
    master.role = 'MASTER'
    can_gen, used, remaining = check_quota(master)
    assert can_gen is True
    assert remaining == 999


def test_user_within_limit():
    with patch('services.quota_service.get_daily_usage', return_value=3):
        user = MagicMock()
        user.role = 'USER'
        user.id = 1
        can_gen, used, remaining = check_quota(user)
        assert can_gen is True
        assert used == 3
        assert remaining == 7


def test_user_at_limit():
    with patch('services.quota_service.get_daily_usage', return_value=10):
        user = MagicMock()
        user.role = 'USER'
        user.id = 1
        can_gen, used, remaining = check_quota(user)
        assert can_gen is False
        assert used == 10
        assert remaining == 0


def test_user_one_below_limit():
    with patch('services.quota_service.get_daily_usage', return_value=9):
        user = MagicMock()
        user.role = 'USER'
        user.id = 1
        can_gen, used, remaining = check_quota(user)
        assert can_gen is True
        assert remaining == 1


def test_user_zero_usage():
    with patch('services.quota_service.get_daily_usage', return_value=0):
        user = MagicMock()
        user.role = 'USER'
        user.id = 1
        can_gen, used, remaining = check_quota(user)
        assert can_gen is True
        assert used == 0
        assert remaining == 10


def test_enforce_quota_master_always_allowed():
    master = MagicMock()
    master.role = 'MASTER'
    allowed, err = enforce_quota_with_lock(master)
    assert allowed is True
    assert err == ''


def test_enforce_quota_user_allowed():
    with patch('services.quota_service.get_daily_usage', return_value=5):
        user = MagicMock()
        user.role = 'USER'
        user.id = 1
        # enforce_quota_with_lock needs DB; test with mocked usage
        with patch('services.quota_service.db') as mock_db:
            mock_db.session.query.return_value.filter.return_value\
                .with_for_update.return_value.scalar.return_value = 5
            allowed, err = enforce_quota_with_lock(user)
        assert allowed is True
        assert err == ''


def test_enforce_quota_user_at_limit():
    user = MagicMock()
    user.role = 'USER'
    user.id = 1
    with patch('services.quota_service.db') as mock_db:
        mock_db.session.query.return_value.filter.return_value\
            .with_for_update.return_value.scalar.return_value = 10
        allowed, err = enforce_quota_with_lock(user)
    assert allowed is False
    assert 'Daily limit reached' in err
    assert '10/10' in err


# ---------------------------------------------------------------------------
# Integration tests (real in-memory SQLite DB via conftest)
# ---------------------------------------------------------------------------

def test_check_quota_integration_new_user(app):
    """Fresh user has 0 usage and full quota."""
    from models.user import User
    from models import db
    from werkzeug.security import generate_password_hash

    with app.app_context():
        u = User(name='Quota Test', username='quotatest99',
                 password_hash=generate_password_hash('Test@999'),
                 role='USER', is_active=True)
        db.session.add(u)
        db.session.commit()

        can_gen, used, remaining = check_quota(u)
        assert can_gen is True
        assert used == 0
        assert remaining == 10
