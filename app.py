import os
import logging
from flask import Flask, request, g
from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from models import db, login_manager
from config import get_config

csrf = CSRFProtect()
limiter = Limiter(key_func=get_remote_address, default_limits=[])


def create_app(config_class=None):
    app = Flask(__name__)

    if config_class is None:
        config_class = get_config()

    app.config.from_object(config_class)

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s %(levelname)s %(name)s %(message)s'
    )

    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    limiter.init_app(app)

    # Import all models to register them with SQLAlchemy
    from models.user import User
    from models.company import CompanySetting
    from models.template import Template
    from models.proposal import (
        Proposal, ProposalModule, ProposalBattery,
        ProposalAddon, ProposalPayment, ProposalVersion,
        ProposalFile, AcceptedProposal, RejectedProposal
    )
    from models.audit import AuditLog

    # Register blueprints
    from routes.auth import auth_bp
    from routes.dashboard import dashboard_bp
    from routes.proposals import proposals_bp
    from routes.users import users_bp
    from routes.templates import templates_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(proposals_bp)
    app.register_blueprint(users_bp)
    app.register_blueprint(templates_bp)

    # Security headers on every response
    @app.after_request
    def set_security_headers(response):
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response.headers['Permissions-Policy'] = 'geolocation=(), microphone=(), camera=()'
        return response

    # Ensure storage exists
    os.makedirs(app.config.get('STORAGE_PATH', 'storage/proposals'), exist_ok=True)

    return app


if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        db.create_all()
    # Never run with debug=True in production — use gunicorn
    app.run(host='127.0.0.1', port=5000, debug=False)
