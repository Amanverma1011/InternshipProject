from datetime import date
from models import db
from models.proposal import Proposal
from models.user import User
from sqlalchemy import func


MAX_DAILY_PROPOSALS = 10


def get_daily_usage(user_id: int, for_date: date = None) -> int:
    if for_date is None:
        for_date = date.today()
    count = db.session.query(func.count(Proposal.id)).filter(
        Proposal.created_by == user_id,
        Proposal.status.in_(['GENERATED', 'ACCEPTED', 'REJECTED']),
        func.date(Proposal.updated_at) == for_date
    ).scalar()
    return count or 0


def check_quota(user: User, for_date: date = None):
    if user.role == 'MASTER':
        return True, 0, 999
    if for_date is None:
        for_date = date.today()
    used = get_daily_usage(user.id, for_date)
    remaining = max(0, MAX_DAILY_PROPOSALS - used)
    return remaining > 0, used, remaining


def enforce_quota_with_lock(user: User):
    if user.role == 'MASTER':
        return True, ''
    today = date.today()
    used = db.session.query(func.count(Proposal.id)).filter(
        Proposal.created_by == user.id,
        Proposal.status.in_(['GENERATED', 'ACCEPTED', 'REJECTED']),
        func.date(Proposal.updated_at) == today
    ).with_for_update().scalar() or 0
    if used >= MAX_DAILY_PROPOSALS:
        return False, f'Daily limit reached: {used}/{MAX_DAILY_PROPOSALS} proposals generated today.'
    return True, ''
