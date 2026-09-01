from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user
from werkzeug.security import generate_password_hash
from models.user import User
from models import db
from services.audit_service import log_action

users_bp = Blueprint('users', __name__)


def _require_master():
    if not current_user.is_master():
        abort(403)


@users_bp.route('/users')
@login_required
def list_users():
    _require_master()
    users = User.query.order_by(User.created_at.desc()).all()
    return render_template('users/list.html', users=users)


@users_bp.route('/users/new', methods=['GET', 'POST'])
@login_required
def create_user():
    _require_master()
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        role = request.form.get('role', 'USER')
        errors = []
        if not name: errors.append('Name is required.')
        if not username: errors.append('Username is required.')
        if not password: errors.append('Password is required.')
        if len(password) < 6: errors.append('Password must be at least 6 characters.')
        if role not in ('MASTER', 'USER'): role = 'USER'
        if User.query.filter_by(username=username).first():
            errors.append(f'Username "{username}" already exists.')
        if errors:
            for e in errors: flash(e, 'danger')
            return render_template('users/create.html', form_data=request.form)
        user = User(name=name, username=username,
                    password_hash=generate_password_hash(password),
                    role=role, is_active=True)
        db.session.add(user)
        db.session.commit()
        log_action('CREATE_USER', 'user', user.id, {'username': username, 'role': role})
        flash(f'User "{username}" created.', 'success')
        return redirect(url_for('users.list_users'))
    return render_template('users/create.html', form_data={})


@users_bp.route('/users/<int:user_id>/toggle', methods=['POST'])
@login_required
def toggle_user(user_id):
    _require_master()
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash('Cannot change your own account status.', 'danger')
        return redirect(url_for('users.list_users'))
    user.is_active = not user.is_active
    db.session.commit()
    action = 'ENABLE_USER' if user.is_active else 'DISABLE_USER'
    log_action(action, 'user', user.id, {'username': user.username})
    flash(f'User "{user.username}" {"enabled" if user.is_active else "disabled"}.', 'success')
    return redirect(url_for('users.list_users'))


@users_bp.route('/users/<int:user_id>/reset-password', methods=['POST'])
@login_required
def reset_password(user_id):
    _require_master()
    user = User.query.get_or_404(user_id)
    new_password = request.form.get('new_password', '')
    if len(new_password) < 6:
        flash('Password must be at least 6 characters.', 'danger')
        return redirect(url_for('users.list_users'))
    user.password_hash = generate_password_hash(new_password)
    db.session.commit()
    log_action('RESET_PASSWORD', 'user', user.id, {'username': user.username})
    flash(f'Password reset for "{user.username}".', 'success')
    return redirect(url_for('users.list_users'))
