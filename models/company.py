from datetime import datetime
from models import db


class CompanySetting(db.Model):
    __tablename__ = 'company_settings'

    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), nullable=False, unique=True)
    value = db.Column(db.Text, nullable=False)
    description = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    @classmethod
    def get(cls, key: str, default: str = '') -> str:
        setting = cls.query.filter_by(key=key).first()
        return setting.value if setting else default

    @classmethod
    def get_all_dict(cls) -> dict:
        settings = cls.query.all()
        return {s.key: s.value for s in settings}

    def __repr__(self) -> str:
        return f'<CompanySetting {self.key}>'
