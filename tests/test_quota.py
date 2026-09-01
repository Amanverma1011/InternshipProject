"""Tests for quota service."""
import pytest
from unittest.mock import MagicMock, patch
from services.quota_service import MAX_DAILY_PROPOSALS


def test_max_daily_limit():
    assert MAX_DAILY_PROPOSALS == 10


def test_master_unlimited():
    from services.quota_service import check_quota
    master = MagicMock()
    master.role = 'MASTER'
    can_gen, used, remaining = check_quota(master)
    assert can_gen is True
    assert remaining == 999


def test_user_within_limit():
    from services.quota_service import check_quota
    with patch('services.quota_service.get_daily_usage', return_value=3):
        user = MagicMock()
        user.role = 'USER'
        user.id = 1
        can_gen, used, remaining = check_quota(user)
        assert can_gen is True
        assert used == 3
        assert remaining == 7


def test_user_at_limit():
    from services.quota_service import check_quota
    with patch('services.quota_service.get_daily_usage', return_value=10):
        user = MagicMock()
        user.role = 'USER'
        user.id = 1
        can_gen, used, remaining = check_quota(user)
        assert can_gen is False
        assert remaining == 0


def test_user_exceeds_limit():
    from services.quota_service import check_quota
    with patch('services.quota_service.get_daily_usage', return_value=10):
        user = MagicMock()
        user.role = 'USER'
        user.id = 1
        can_gen, used, remaining = check_quota(user)
        assert can_gen is False
        assert remaining == 0
