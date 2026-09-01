import os
from flask import Blueprint, render_template, abort, request, flash, redirect, url_for, current_app
from flask_login import login_required, current_user
from models.template import Template
from models.audit import AuditLog
from services.audit_service import log_action

templates_bp = Blueprint('templates', __name__)


@templates_bp.route('/templates')
@login_required
def list_templates():
    if not current_user.is_master():
        abort(403)
    templates = Template.query.order_by(Template.system_type, Template.version.desc()).all()
    return render_template('templates_mgmt/list.html', templates=templates)


@templates_bp.route('/templates/<int:template_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_template_html(template_id):
    if not current_user.is_master():
        abort(403)
    template = Template.query.get_or_404(template_id)
    template_file = os.path.join(current_app.root_path, 'templates', template.html_file)

    if request.method == 'POST':
        html_content = request.form.get('html_content', '')
        try:
            with open(template_file, 'w', encoding='utf-8') as f:
                f.write(html_content)
            log_action('EDIT_TEMPLATE', 'template', template.id, {'name': template.name})
            flash('Template HTML saved successfully.', 'success')
        except Exception as e:
            flash(f'Failed to save: {str(e)}', 'danger')
        return redirect(url_for('templates.edit_template_html', template_id=template_id))

    try:
        with open(template_file, 'r', encoding='utf-8') as f:
            html_content = f.read()
    except FileNotFoundError:
        html_content = ''
        flash('Template file not found on disk.', 'warning')

    return render_template('templates_mgmt/edit.html', template=template, html_content=html_content)


@templates_bp.route('/audit-logs')
@login_required
def audit_logs():
    if not current_user.is_master():
        abort(403)
    logs = AuditLog.query.order_by(AuditLog.created_at.desc()).limit(200).all()
    return render_template('templates_mgmt/audit.html', logs=logs)
