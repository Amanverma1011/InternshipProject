import os
import logging
from flask import Flask
from models import db, login_manager
from config import get_config


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

    # Ensure storage exists
    os.makedirs(app.config.get('STORAGE_PATH', 'storage/proposals'), exist_ok=True)

    return app


if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', port=5000, debug=True)
