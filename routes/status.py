from flask import Blueprint, render_template, abort
from flask_login import login_required, current_user
from models.audit import AuditLog
from models.user import User

status_bp = Blueprint('status', __name__)


@status_bp.route('/audit-logs')
@login_required
def audit_logs():
    if not current_user.is_master():
        abort(403)
    logs = AuditLog.query.order_by(AuditLog.created_at.desc()).limit(200).all()
    users_map = {u.id: u for u in User.query.all()}
    return render_template('status/audit_logs.html', logs=logs, users_map=users_map)
