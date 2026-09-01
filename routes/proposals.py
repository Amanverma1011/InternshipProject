from flask import Blueprint, render_template, redirect, url_for, flash, request, abort, jsonify
from flask_login import login_required, current_user
from models.proposal import Proposal
from models import db
from services.proposal_service import create_or_update_proposal, accept_proposal, reject_proposal
from services.pdf_service import generate_pdf_for_proposal
from services.file_service import send_proposal_pdf
from services.quota_service import check_quota, enforce_quota_with_lock
from services.audit_service import log_action
from services.calculation_service import calculate_all

proposals_bp = Blueprint('proposals', __name__)

SYSTEM_TYPES = ['ONGRID', 'HYBRID']
MOUNTING_TYPES = ['RCC', 'SEATMOUNT', 'CARPORT', 'GROUNDMOUNT']


def _get_proposal_or_403(proposal_id: int) -> Proposal:
    proposal = Proposal.query.get_or_404(proposal_id)
    if not current_user.is_master() and proposal.created_by != current_user.id:
        abort(403)
    return proposal


@proposals_bp.route('/proposals')
@login_required
def list_proposals():
    if current_user.is_master():
        proposals = Proposal.query.order_by(Proposal.created_at.desc()).all()
    else:
        proposals = Proposal.query.filter_by(created_by=current_user.id)\
            .order_by(Proposal.created_at.desc()).all()
    return render_template('proposals/list.html', proposals=proposals)


@proposals_bp.route('/proposals/new', methods=['GET', 'POST'])
@login_required
def create():
    if request.method == 'POST':
        proposal, errors = create_or_update_proposal(current_user, request.form)
        if errors:
            for e in errors:
                flash(e, 'danger')
            return render_template('proposals/create.html', form_data=request.form,
                                   system_types=SYSTEM_TYPES, mounting_types=MOUNTING_TYPES,
                                   edit_mode=False)
        log_action('CREATE_PROPOSAL', 'proposal', proposal.id,
                   {'proposal_number': proposal.proposal_number})
        flash(f'Proposal {proposal.proposal_number} saved as draft.', 'success')
        return redirect(url_for('proposals.detail', proposal_id=proposal.id))
    return render_template('proposals/create.html', form_data={},
                           system_types=SYSTEM_TYPES, mounting_types=MOUNTING_TYPES,
                           edit_mode=False)


@proposals_bp.route('/proposals/<int:proposal_id>')
@login_required
def detail(proposal_id):
    proposal = _get_proposal_or_403(proposal_id)
    modules = list(proposal.modules)
    addons = list(proposal.addons.order_by('sequence'))
    payments = list(proposal.payments.order_by('sequence'))
    has_pdf = proposal.files.count() > 0
    return render_template('proposals/detail.html',
                           proposal=proposal, modules=modules,
                           addons=addons, payments=payments, has_pdf=has_pdf)


@proposals_bp.route('/proposals/<int:proposal_id>/edit', methods=['GET', 'POST'])
@login_required
def edit(proposal_id):
    proposal = _get_proposal_or_403(proposal_id)
    if proposal.status != 'DRAFT':
        flash('Only draft proposals can be edited.', 'warning')
        return redirect(url_for('proposals.detail', proposal_id=proposal_id))
    if request.method == 'POST':
        updated, errors = create_or_update_proposal(current_user, request.form, proposal_id)
        if errors:
            for e in errors:
                flash(e, 'danger')
        else:
            flash('Proposal updated.', 'success')
            return redirect(url_for('proposals.detail', proposal_id=proposal_id))
    return render_template('proposals/create.html',
                           form_data=proposal,
                           edit_mode=True,
                           proposal=proposal,
                           modules=list(proposal.modules),
                           addons=list(proposal.addons.order_by('sequence')),
                           payments=list(proposal.payments.order_by('sequence')),
                           battery=proposal.battery,
                           system_types=SYSTEM_TYPES,
                           mounting_types=MOUNTING_TYPES)


@proposals_bp.route('/proposals/<int:proposal_id>/generate', methods=['POST'])
@login_required
def generate(proposal_id):
    proposal = _get_proposal_or_403(proposal_id)
    if proposal.status not in ('DRAFT', 'GENERATED'):
        flash('Cannot regenerate PDF for this proposal status.', 'warning')
        return redirect(url_for('proposals.detail', proposal_id=proposal_id))

    # Validate payment total matches grand total
    addons = [{'amount': float(a.amount)} for a in proposal.addons]
    payments_list = [{'amount': float(p.amount)} for p in proposal.payments]
    _, calc_errors = calculate_all(
        float(proposal.plant_capacity), float(proposal.base_price),
        addons, float(proposal.discount_percent), payments_list
    )
    if calc_errors:
        for e in calc_errors:
            flash(e, 'danger')
        return redirect(url_for('proposals.detail', proposal_id=proposal_id))

    if not payments_list:
        flash('Add at least one payment stage before generating PDF.', 'danger')
        return redirect(url_for('proposals.detail', proposal_id=proposal_id))

    if proposal.status == 'DRAFT':
        allowed, err = enforce_quota_with_lock(current_user)
        if not allowed:
            flash(err, 'danger')
            return redirect(url_for('proposals.detail', proposal_id=proposal_id))

    success, error, _ = generate_pdf_for_proposal(proposal, current_user)
    if success:
        flash(f'PDF generated: {proposal.proposal_number}', 'success')
    else:
        flash(f'PDF generation failed: {error}', 'danger')
    return redirect(url_for('proposals.detail', proposal_id=proposal_id))


@proposals_bp.route('/proposals/<int:proposal_id>/download')
@login_required
def download(proposal_id):
    proposal = _get_proposal_or_403(proposal_id)
    log_action('DOWNLOAD_PDF', 'proposal', proposal.id,
               {'proposal_number': proposal.proposal_number})
    return send_proposal_pdf(proposal, current_user)


@proposals_bp.route('/proposals/<int:proposal_id>/accept', methods=['POST'])
@login_required
def accept(proposal_id):
    proposal = _get_proposal_or_403(proposal_id)
    notes = request.form.get('notes', '')
    ok, err = accept_proposal(proposal, current_user, notes)
    flash('Proposal accepted.' if ok else f'Error: {err}', 'success' if ok else 'danger')
    return redirect(url_for('proposals.detail', proposal_id=proposal_id))


@proposals_bp.route('/proposals/<int:proposal_id>/reject', methods=['POST'])
@login_required
def reject(proposal_id):
    proposal = _get_proposal_or_403(proposal_id)
    reason = request.form.get('reason', '').strip()
    if not reason:
        flash('Rejection reason is required.', 'danger')
        return redirect(url_for('proposals.detail', proposal_id=proposal_id))
    ok, err = reject_proposal(proposal, current_user, reason)
    flash('Proposal rejected.' if ok else f'Error: {err}', 'warning' if ok else 'danger')
    return redirect(url_for('proposals.detail', proposal_id=proposal_id))


@proposals_bp.route('/api/calculate', methods=['POST'])
@login_required
def api_calculate():
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data'}), 400
    try:
        plant_capacity = float(data.get('plant_capacity', 0))
        base_price = float(data.get('base_price', 0))
        addons = data.get('addons', [])
        discount_percent = float(data.get('discount_percent', 0))
        payments = data.get('payments', [])
        calcs, errors = calculate_all(plant_capacity, base_price, addons, discount_percent, payments)
        return jsonify({
            'total_area': float(calcs['total_area']),
            'inverter_capacity': float(calcs['inverter_capacity']),
            'addon_total': float(calcs['addon_total']),
            'subtotal': float(calcs['subtotal']),
            'discount_amount': float(calcs['discount_amount']),
            'grand_total': float(calcs['grand_total']),
            'payment_total': float(calcs['payment_total']),
            'errors': errors
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 400
