from datetime import datetime
from models import db


class Template(db.Model):
    __tablename__ = 'templates'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    system_type = db.Column(db.Enum('ONGRID', 'HYBRID'), nullable=False)
    version = db.Column(db.Integer, nullable=False, default=1)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    html_file = db.Column(db.String(255))
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self) -> str:
        return f'<Template {self.name} v{self.version}>'
