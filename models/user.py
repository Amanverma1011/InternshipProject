from datetime import datetime
from flask_login import UserMixin
from models import db, login_manager


class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    username = db.Column(db.String(50), nullable=False, unique=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.Enum('MASTER', 'USER'), nullable=False, default='USER')
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    proposals = db.relationship('Proposal', backref='creator', lazy='dynamic',
                                foreign_keys='Proposal.created_by')
    audit_logs = db.relationship('AuditLog', backref='user', lazy='dynamic',
                                 foreign_keys='AuditLog.user_id')

    def is_master(self) -> bool:
        return self.role == 'MASTER'

    def get_id(self) -> str:
        return str(self.id)

    def __repr__(self) -> str:
        return f'<User {self.username} ({self.role})>'


@login_manager.user_loader
def load_user(user_id: str):
    return User.query.get(int(user_id))
