from datetime import datetime
from models import db


class Proposal(db.Model):
    __tablename__ = 'proposals'

    id = db.Column(db.Integer, primary_key=True)
    proposal_number = db.Column(db.String(20), nullable=False, unique=True)
    customer_name = db.Column(db.String(150), nullable=False)
    customer_address = db.Column(db.Text, nullable=False)
    customer_contact = db.Column(db.String(20))
    system_type = db.Column(db.Enum('ONGRID', 'HYBRID'), nullable=False)
    plant_capacity = db.Column(db.Numeric(8, 2), nullable=False)
    total_area = db.Column(db.Numeric(10, 2), nullable=False)
    mounting_type = db.Column(db.Enum('RCC', 'SEATMOUNT', 'CARPORT', 'GROUNDMOUNT'), nullable=False)
    tilt_angle = db.Column(db.String(20), default='15-22 degrees')
    inverter_capacity = db.Column(db.Numeric(8, 2), nullable=False)
    base_price = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    addon_total = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    subtotal = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    discount_percent = db.Column(db.Numeric(5, 2), nullable=False, default=0)
    discount_amount = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    grand_total = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    cfa_amount = db.Column(db.Numeric(12, 2), nullable=False, default=78000)
    status = db.Column(db.Enum('DRAFT', 'GENERATED', 'ACCEPTED', 'REJECTED'),
                       nullable=False, default='DRAFT')
    proposal_date = db.Column(db.Date)
    snapshot = db.Column(db.JSON)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    template_id = db.Column(db.Integer, db.ForeignKey('templates.id'))
    template_version = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    modules = db.relationship('ProposalModule', backref='proposal', lazy='dynamic',
                              cascade='all, delete-orphan')
    battery = db.relationship('ProposalBattery', backref='proposal', uselist=False,
                              cascade='all, delete-orphan')
    addons = db.relationship('ProposalAddon', backref='proposal', lazy='dynamic',
                             order_by='ProposalAddon.sequence', cascade='all, delete-orphan')
    payments = db.relationship('ProposalPayment', backref='proposal', lazy='dynamic',
                               order_by='ProposalPayment.sequence', cascade='all, delete-orphan')
    versions = db.relationship('ProposalVersion', backref='proposal', lazy='dynamic',
                               cascade='all, delete-orphan')
    files = db.relationship('ProposalFile', backref='proposal', lazy='dynamic',
                            cascade='all, delete-orphan')
    accepted_record = db.relationship('AcceptedProposal', backref='proposal', uselist=False)
    rejected_record = db.relationship('RejectedProposal', backref='proposal', uselist=False)

    def __repr__(self) -> str:
        return f'<Proposal {self.proposal_number}>'


class ProposalModule(db.Model):
    __tablename__ = 'proposal_modules'

    id = db.Column(db.Integer, primary_key=True)
    proposal_id = db.Column(db.Integer, db.ForeignKey('proposals.id'), nullable=False)
    module_type = db.Column(db.Enum('DCR', 'NDCR'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=0)
    wattage = db.Column(db.String(20))
    make = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class ProposalBattery(db.Model):
    __tablename__ = 'proposal_battery'

    id = db.Column(db.Integer, primary_key=True)
    proposal_id = db.Column(db.Integer, db.ForeignKey('proposals.id'), nullable=False, unique=True)
    capacity_kwh = db.Column(db.Numeric(8, 2))
    quantity = db.Column(db.Integer, default=1)
    make = db.Column(db.String(100))
    chemistry = db.Column(db.String(50), default='FeLiO4P')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class ProposalAddon(db.Model):
    __tablename__ = 'proposal_addons'

    id = db.Column(db.Integer, primary_key=True)
    proposal_id = db.Column(db.Integer, db.ForeignKey('proposals.id'), nullable=False)
    sequence = db.Column(db.Integer, nullable=False, default=1)
    name = db.Column(db.String(200), nullable=False)
    amount = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class ProposalPayment(db.Model):
    __tablename__ = 'proposal_payments'

    id = db.Column(db.Integer, primary_key=True)
    proposal_id = db.Column(db.Integer, db.ForeignKey('proposals.id'), nullable=False)
    sequence = db.Column(db.Integer, nullable=False)
    milestone = db.Column(db.String(200), nullable=False)
    amount = db.Column(db.Numeric(12, 2), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class ProposalVersion(db.Model):
    __tablename__ = 'proposal_versions'

    id = db.Column(db.Integer, primary_key=True)
    proposal_id = db.Column(db.Integer, db.ForeignKey('proposals.id'), nullable=False)
    version_number = db.Column(db.Integer, nullable=False, default=1)
    template_id = db.Column(db.Integer, db.ForeignKey('templates.id'))
    template_version = db.Column(db.Integer)
    generated_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    generated_at = db.Column(db.DateTime, default=datetime.utcnow)
    snapshot = db.Column(db.JSON)

    files = db.relationship('ProposalFile', backref='version', lazy='dynamic')


class ProposalFile(db.Model):
    __tablename__ = 'proposal_files'

    id = db.Column(db.Integer, primary_key=True)
    proposal_id = db.Column(db.Integer, db.ForeignKey('proposals.id'), nullable=False)
    proposal_version_id = db.Column(db.Integer, db.ForeignKey('proposal_versions.id'))
    file_name = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    file_size = db.Column(db.Integer)
    sha256 = db.Column(db.String(64))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class AcceptedProposal(db.Model):
    __tablename__ = 'accepted_proposals'

    id = db.Column(db.Integer, primary_key=True)
    proposal_id = db.Column(db.Integer, db.ForeignKey('proposals.id'), nullable=False, unique=True)
    accepted_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    accepted_at = db.Column(db.DateTime, default=datetime.utcnow)
    notes = db.Column(db.Text)


class RejectedProposal(db.Model):
    __tablename__ = 'rejected_proposals'

    id = db.Column(db.Integer, primary_key=True)
    proposal_id = db.Column(db.Integer, db.ForeignKey('proposals.id'), nullable=False, unique=True)
    rejected_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    rejected_at = db.Column(db.DateTime, default=datetime.utcnow)
    reason = db.Column(db.Text, nullable=False)
