from flask import Blueprint, render_template, abort
from flask_login import login_required, current_user
from models.template import Template
from models.audit import AuditLog

templates_bp = Blueprint('templates', __name__)


@templates_bp.route('/templates')
@login_required
def list_templates():
    if not current_user.is_master():
        abort(403)
    templates = Template.query.order_by(Template.system_type, Template.version.desc()).all()
    return render_template('templates_mgmt/list.html', templates=templates)


@templates_bp.route('/audit-logs')
@login_required
def audit_logs():
    if not current_user.is_master():
        abort(403)
    logs = AuditLog.query.order_by(AuditLog.created_at.desc()).limit(200).all()
    return render_template('templates_mgmt/audit.html', logs=logs)
