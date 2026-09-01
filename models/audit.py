from datetime import datetime
from models import db


class AuditLog(db.Model):
    __tablename__ = 'audit_logs'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    action = db.Column(db.String(50), nullable=False)
    entity_type = db.Column(db.String(50))
    entity_id = db.Column(db.Integer)
    details = db.Column(db.JSON)
    ip_address = db.Column(db.String(45))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self) -> str:
        return f'<AuditLog {self.action} by user {self.user_id}>'
