from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash
from models.user import User
from services.audit_service import log_action
from app import limiter

auth_bp = Blueprint('auth', __name__)


def _safe_next(next_url: str) -> bool:
    """Allow only simple relative paths — blocks //evil.com and absolute URLs."""
    return (
        next_url
        and next_url.startswith('/')
        and not next_url.startswith('//')
        and not next_url.startswith('/\\')
    )


@auth_bp.route('/login', methods=['GET', 'POST'])
@limiter.limit("10 per minute; 30 per hour", error_message='Too many login attempts. Try again later.')
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        user = User.query.filter_by(username=username).first()
        if not user or not check_password_hash(user.password_hash, password):
            log_action('LOGIN_FAILED', 'user', None, {
                'username': username,
                'ip': request.remote_addr
            })
            flash('Invalid username or password.', 'danger')
            return render_template('auth/login.html')
        if not user.is_active:
            log_action('LOGIN_BLOCKED', 'user', user.id, {
                'username': username,
                'ip': request.remote_addr
            })
            flash('Your account is disabled. Contact admin.', 'danger')
            return render_template('auth/login.html')
        login_user(user, remember=False)
        log_action('LOGIN', 'user', user.id, {
            'username': user.username,
            'ip': request.remote_addr
        })
        flash(f'Welcome, {user.name}!', 'success')
        next_page = request.args.get('next', '')
        if _safe_next(next_page):
            return redirect(next_page)
        return redirect(url_for('dashboard.index'))
    return render_template('auth/login.html')


@auth_bp.route('/logout')
@login_required
def logout():
    log_action('LOGOUT', 'user', current_user.id, {'username': current_user.username})
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))
