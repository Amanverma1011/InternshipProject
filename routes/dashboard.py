from flask import Blueprint, render_template
from flask_login import login_required, current_user
from datetime import date
from models.proposal import Proposal
from models.user import User
from models import db
from sqlalchemy import func
from services.quota_service import check_quota

dashboard_bp = Blueprint('dashboard', __name__)


@dashboard_bp.route('/')
@dashboard_bp.route('/dashboard')
@login_required
def index():
    today = date.today()
    if current_user.is_master():
        total = Proposal.query.count()
        generated = Proposal.query.filter_by(status='GENERATED').count()
        accepted = Proposal.query.filter_by(status='ACCEPTED').count()
        rejected = Proposal.query.filter_by(status='REJECTED').count()
        total_users = User.query.count()
        today_gen = Proposal.query.filter(
            Proposal.status.in_(['GENERATED', 'ACCEPTED', 'REJECTED']),
            func.date(Proposal.updated_at) == today
        ).count()
        recent = Proposal.query.order_by(Proposal.updated_at.desc()).limit(10).all()
        return render_template('dashboard/index.html',
            is_master=True, total=total, generated=generated,
            accepted=accepted, rejected=rejected, total_users=total_users,
            today_generated=today_gen, recent=recent)
    else:
        _, used, remaining = check_quota(current_user, today)
        total = Proposal.query.filter_by(created_by=current_user.id).count()
        gen = Proposal.query.filter_by(created_by=current_user.id, status='GENERATED').count()
        acc = Proposal.query.filter_by(created_by=current_user.id, status='ACCEPTED').count()
        rej = Proposal.query.filter_by(created_by=current_user.id, status='REJECTED').count()
        recent = Proposal.query.filter_by(created_by=current_user.id)\
            .order_by(Proposal.updated_at.desc()).limit(10).all()
        return render_template('dashboard/index.html',
            is_master=False, quota_used=used, quota_total=10,
            quota_remaining=remaining, total=total, generated=gen,
            accepted=acc, rejected=rej, recent=recent)
