import logging
from datetime import date, datetime
from decimal import Decimal
from typing import Dict, Any, List, Optional, Tuple

from models import db
from models.proposal import (
    Proposal, ProposalModule, ProposalBattery, ProposalAddon,
    ProposalPayment, ProposalVersion, AcceptedProposal, RejectedProposal
)
from models.company import CompanySetting
from models.template import Template
from models.user import User
from services.calculation_service import calculate_all
from services.audit_service import log_action
from sqlalchemy import func

logger = logging.getLogger(__name__)


def generate_proposal_number() -> str:
    year = datetime.utcnow().year
    last_id = db.session.query(func.max(Proposal.id)).scalar() or 0
    return f'SP-{year}-{last_id + 1:05d}'


def build_snapshot(proposal: Proposal, company: dict) -> dict:
    modules = [{'module_type': m.module_type, 'quantity': m.quantity,
                'wattage': m.wattage, 'make': m.make}
               for m in proposal.modules]
    battery = None
    if proposal.battery:
        battery = {
            'capacity_kwh': float(proposal.battery.capacity_kwh or 0),
            'quantity': proposal.battery.quantity,
            'make': proposal.battery.make,
            'chemistry': proposal.battery.chemistry
        }
    addons = [{'sequence': a.sequence, 'name': a.name, 'amount': float(a.amount)}
              for a in proposal.addons.order_by('sequence')]
    payments = [{'sequence': p.sequence, 'milestone': p.milestone, 'amount': float(p.amount)}
                for p in proposal.payments.order_by('sequence')]
    return {
        'proposal_number': proposal.proposal_number,
        'proposal_date': str(proposal.proposal_date),
        'customer_name': proposal.customer_name,
        'customer_address': proposal.customer_address,
        'customer_contact': proposal.customer_contact,
        'system_type': proposal.system_type,
        'plant_capacity': float(proposal.plant_capacity),
        'total_area': float(proposal.total_area),
        'mounting_type': proposal.mounting_type,
        'tilt_angle': proposal.tilt_angle,
        'inverter_capacity': float(proposal.inverter_capacity),
        'modules': modules,
        'battery': battery,
        'base_price': float(proposal.base_price),
        'addons': addons,
        'addon_total': float(proposal.addon_total),
        'subtotal': float(proposal.subtotal),
        'discount_percent': float(proposal.discount_percent),
        'discount_amount': float(proposal.discount_amount),
        'grand_total': float(proposal.grand_total),
        'cfa_amount': float(proposal.cfa_amount),
        'payments': payments,
        'company': company,
        'generated_at': datetime.utcnow().isoformat()
    }


def create_or_update_proposal(
    user: User,
    form_data,
    proposal_id: Optional[int] = None
) -> Tuple[Optional[Proposal], List[str]]:
    errors = []

    customer_name = (form_data.get('customer_name') or '').strip()
    customer_address = (form_data.get('customer_address') or '').strip()
    system_type = (form_data.get('system_type') or '').upper()
    mounting_type = (form_data.get('mounting_type') or '').upper()

    if not customer_name:
        errors.append('Customer name is required.')
    if not customer_address:
        errors.append('Customer address is required.')
    if system_type not in ('ONGRID', 'HYBRID'):
        errors.append('Invalid system type.')
    if mounting_type not in ('RCC', 'SEATMOUNT', 'CARPORT', 'GROUNDMOUNT'):
        errors.append('Invalid mounting type.')

    try:
        plant_capacity = float(form_data.get('plant_capacity') or 0)
        if plant_capacity <= 0:
            errors.append('Plant capacity must be greater than 0.')
    except (ValueError, TypeError):
        errors.append('Invalid plant capacity.')
        plant_capacity = 0

    try:
        base_price = float(form_data.get('base_price') or 0)
        if base_price < 0:
            errors.append('Base price cannot be negative.')
    except (ValueError, TypeError):
        errors.append('Invalid base price.')
        base_price = 0

    try:
        discount_percent = float(form_data.get('discount_percent') or 0)
        if not (0 <= discount_percent <= 100):
            errors.append('Discount must be between 0 and 100.')
    except (ValueError, TypeError):
        errors.append('Invalid discount.')
        discount_percent = 0

    # Parse add-ons
    if hasattr(form_data, 'getlist'):
        addon_names = form_data.getlist('addon_name')
        addon_amounts = form_data.getlist('addon_amount')
        pay_milestones = form_data.getlist('payment_milestone')
        pay_amounts = form_data.getlist('payment_amount')
    else:
        addon_names = form_data.get('addon_names', [])
        addon_amounts = form_data.get('addon_amounts', [])
        pay_milestones = form_data.get('payment_milestones', [])
        pay_amounts = form_data.get('payment_amounts', [])

    addons = []
    for name, amount in zip(addon_names, addon_amounts):
        name = name.strip()
        if name:
            try:
                addons.append({'name': name, 'amount': float(amount or 0)})
            except (ValueError, TypeError):
                errors.append(f'Invalid add-on amount for "{name}".')

    payments = []
    for ms, amt in zip(pay_milestones, pay_amounts):
        ms = ms.strip()
        if ms:
            try:
                payments.append({'milestone': ms, 'amount': float(amt or 0)})
            except (ValueError, TypeError):
                errors.append(f'Invalid payment amount for "{ms}".')

    if errors:
        return None, errors

    calcs, _ = calculate_all(plant_capacity, base_price, addons, discount_percent, payments)

    try:
        if proposal_id:
            proposal = Proposal.query.filter_by(id=proposal_id, created_by=user.id).first()
            if not proposal:
                return None, ['Proposal not found or access denied.']
            if proposal.status not in ('DRAFT',):
                return None, ['Only DRAFT proposals can be edited.']
        else:
            proposal = Proposal(
                proposal_number=generate_proposal_number(),
                created_by=user.id,
                status='DRAFT'
            )
            db.session.add(proposal)

        proposal.customer_name = customer_name
        proposal.customer_address = customer_address
        proposal.customer_contact = (form_data.get('customer_contact') or '').strip()
        proposal.system_type = system_type
        proposal.plant_capacity = Decimal(str(plant_capacity))
        proposal.total_area = calcs['total_area']
        proposal.mounting_type = mounting_type
        proposal.tilt_angle = form_data.get('tilt_angle') or '15-22 degrees'
        proposal.inverter_capacity = calcs['inverter_capacity']
        proposal.base_price = Decimal(str(base_price))
        proposal.addon_total = calcs['addon_total']
        proposal.subtotal = calcs['subtotal']
        proposal.discount_percent = Decimal(str(discount_percent))
        proposal.discount_amount = calcs['discount_amount']
        proposal.grand_total = calcs['grand_total']
        proposal.cfa_amount = Decimal(CompanySetting.get('cfa_amount', '78000'))
        proposal.proposal_date = date.today()

        db.session.flush()

        # Clear existing child records
        ProposalModule.query.filter_by(proposal_id=proposal.id).delete()
        ProposalBattery.query.filter_by(proposal_id=proposal.id).delete()
        ProposalAddon.query.filter_by(proposal_id=proposal.id).delete()
        ProposalPayment.query.filter_by(proposal_id=proposal.id).delete()

        settings = CompanySetting.get_all_dict()

        dcr_qty = int(form_data.get('dcr_quantity') or 0)
        ndcr_qty = int(form_data.get('ndcr_quantity') or 0)
        if dcr_qty > 0:
            db.session.add(ProposalModule(
                proposal_id=proposal.id, module_type='DCR', quantity=dcr_qty,
                wattage=settings.get('dcr_module_wattage', '580W-620W'),
                make=settings.get('module_makes', 'Rayzon Solar/Premier Energy/RenewSys/Pahal/Adani/TATA Power')
            ))
        if ndcr_qty > 0:
            db.session.add(ProposalModule(
                proposal_id=proposal.id, module_type='NDCR', quantity=ndcr_qty,
                wattage=settings.get('ndcr_module_wattage', '580W-620W'),
                make=settings.get('module_makes', 'Rayzon Solar/Premier Energy/RenewSys/Pahal/Adani/TATA Power')
            ))

        if system_type == 'HYBRID':
            try:
                bat_cap = float(form_data.get('battery_capacity_kwh') or 5)
                bat_qty = int(form_data.get('battery_quantity') or 1)
            except (ValueError, TypeError):
                bat_cap, bat_qty = 5.0, 1
            db.session.add(ProposalBattery(
                proposal_id=proposal.id,
                capacity_kwh=Decimal(str(bat_cap)),
                quantity=bat_qty,
                make=(form_data.get('battery_make') or '').strip() or None,
                chemistry=settings.get('battery_chemistry', 'FeLiO4P')
            ))

        for seq, addon in enumerate(addons, 1):
            db.session.add(ProposalAddon(
                proposal_id=proposal.id, sequence=seq,
                name=addon['name'], amount=Decimal(str(addon['amount']))
            ))

        for seq, pay in enumerate(payments, 1):
            db.session.add(ProposalPayment(
                proposal_id=proposal.id, sequence=seq,
                milestone=pay['milestone'], amount=Decimal(str(pay['amount']))
            ))

        db.session.commit()
        return proposal, []

    except Exception as e:
        db.session.rollback()
        logger.error(f'Proposal save error: {e}')
        return None, [f'Database error: {str(e)}']


def accept_proposal(proposal: Proposal, user: User, notes: str = '') -> Tuple[bool, str]:
    if proposal.status != 'GENERATED':
        return False, 'Only generated proposals can be accepted.'
    try:
        proposal.status = 'ACCEPTED'
        db.session.add(AcceptedProposal(
            proposal_id=proposal.id, accepted_by=user.id, notes=notes))
        db.session.commit()
        log_action('ACCEPT_PROPOSAL', 'proposal', proposal.id,
                   {'proposal_number': proposal.proposal_number})
        return True, ''
    except Exception as e:
        db.session.rollback()
        return False, str(e)


def reject_proposal(proposal: Proposal, user: User, reason: str) -> Tuple[bool, str]:
    if not reason.strip():
        return False, 'Rejection reason is required.'
    if proposal.status != 'GENERATED':
        return False, 'Only generated proposals can be rejected.'
    try:
        proposal.status = 'REJECTED'
        db.session.add(RejectedProposal(
            proposal_id=proposal.id, rejected_by=user.id, reason=reason.strip()))
        db.session.commit()
        log_action('REJECT_PROPOSAL', 'proposal', proposal.id,
                   {'proposal_number': proposal.proposal_number, 'reason': reason[:200]})
        return True, ''
    except Exception as e:
        db.session.rollback()
        return False, str(e)
