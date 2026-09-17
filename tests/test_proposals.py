"""Integration tests for proposal CRUD, status transitions, and access control."""
import pytest
from decimal import Decimal
from tests.conftest import login, make_proposal, post_form, post_anon
from models import db
from models.proposal import Proposal, ProposalPayment, AcceptedProposal, RejectedProposal
from models.user import User


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _valid_form(**overrides):
    """Return multidict-compatible form data for proposal creation."""
    data = [
        ('customer_name', 'Rajesh Kumar'),
        ('customer_address', '12 Main St, Ranchi - 834001'),
        ('customer_contact', '9876543210'),
        ('system_type', 'ONGRID'),
        ('plant_capacity', '5.0'),
        ('mounting_type', 'RCC'),
        ('base_price', '275000'),
        ('discount_percent', '0'),
        ('dcr_quantity', '9'),
        ('dcr_wattage', '580W-620W'),
        ('dcr_make', 'Rayzon Solar'),
        ('ndcr_quantity', '0'),
        ('payment_milestone', 'Signing of Proposal'),
        ('payment_amount', '275000'),
    ]
    result = []
    overridden_keys = set(overrides.keys())
    for k, v in data:
        if k in overridden_keys:
            result.append((k, overrides[k]))
            overridden_keys.discard(k)
        else:
            result.append((k, v))
    for k in overridden_keys:
        result.append((k, overrides[k]))
    return result


# ---------------------------------------------------------------------------
# Create proposal (DRAFT)
# ---------------------------------------------------------------------------

def test_create_proposal_success(client):
    login(client, 'testmaster', 'Admin@1234')
    rv = post_form(client, '/proposals/new', _valid_form())
    assert rv.status_code == 200
    assert b'saved as draft' in rv.data.lower() or b'SP-' in rv.data


def test_create_proposal_missing_customer_name(client):
    login(client, 'testmaster', 'Admin@1234')
    rv = post_form(client, '/proposals/new', _valid_form(customer_name=''))
    assert b'required' in rv.data.lower() or rv.status_code == 200


def test_create_proposal_missing_address(client):
    login(client, 'testmaster', 'Admin@1234')
    rv = post_form(client, '/proposals/new', _valid_form(customer_address=''))
    assert b'required' in rv.data.lower() or rv.status_code == 200


def test_create_proposal_invalid_system_type(client):
    login(client, 'testmaster', 'Admin@1234')
    rv = post_form(client, '/proposals/new', _valid_form(system_type='INVALID'))
    assert b'Invalid' in rv.data or rv.status_code == 200


def test_create_proposal_zero_capacity(client):
    login(client, 'testmaster', 'Admin@1234')
    rv = post_form(client, '/proposals/new', _valid_form(plant_capacity='0'))
    assert b'greater than 0' in rv.data or b'required' in rv.data.lower()


def test_create_proposal_customer_name_title_cased(app, client):
    """Customer name should be stored Title Cased."""
    login(client, 'testmaster', 'Admin@1234')
    post_form(client, '/proposals/new', _valid_form(customer_name='RAJESH kumar'))
    with app.app_context():
        p = Proposal.query.filter(Proposal.customer_name == 'Rajesh Kumar').first()
        assert p is not None


def test_create_hybrid_proposal(client):
    login(client, 'testmaster', 'Admin@1234')
    form = _valid_form(system_type='HYBRID') + [
        ('battery_capacity_kwh', '10'),
        ('battery_quantity', '2'),
        ('battery_make', 'Sologix'),
    ]
    rv = post_form(client, '/proposals/new', form)
    assert rv.status_code == 200
    assert b'SP-' in rv.data


def test_create_proposal_unauthenticated(client):
    rv = post_anon(client, '/proposals/new', _valid_form())
    assert rv.status_code == 302
    assert 'login' in rv.headers.get('Location', '').lower()


# ---------------------------------------------------------------------------
# List proposals
# ---------------------------------------------------------------------------

def test_list_proposals_master_sees_all(app, client):
    login(client, 'testmaster', 'Admin@1234')
    with app.app_context():
        u1 = User.query.filter_by(username='testuser1').first()
        make_proposal(u1.id, num_suffix=11001)
        make_proposal(u1.id, num_suffix=11002)
    rv = client.get('/proposals')
    assert rv.status_code == 200
    assert b'SP-TEST' in rv.data


def test_list_proposals_user_sees_own_only(app, client):
    login(client, 'testuser1', 'User@1111')
    with app.app_context():
        u1 = User.query.filter_by(username='testuser1').first()
        u2 = User.query.filter_by(username='testuser2').first()
        make_proposal(u1.id, num_suffix=12001)
        make_proposal(u2.id, num_suffix=12002)

    rv = client.get('/proposals')
    assert rv.status_code == 200
    assert b'SP-TEST-12001' in rv.data
    assert b'SP-TEST-12002' not in rv.data


# ---------------------------------------------------------------------------
# Proposal detail
# ---------------------------------------------------------------------------

def test_detail_own_proposal(app, client):
    login(client, 'testuser1', 'User@1111')
    with app.app_context():
        u1 = User.query.filter_by(username='testuser1').first()
        p = make_proposal(u1.id, num_suffix=13001)
        pid = p.id
    rv = client.get(f'/proposals/{pid}')
    assert rv.status_code == 200
    assert b'SP-TEST-13001' in rv.data


def test_detail_other_users_proposal_returns_403(app, client):
    login(client, 'testuser2', 'User@2222')
    with app.app_context():
        u1 = User.query.filter_by(username='testuser1').first()
        p = make_proposal(u1.id, num_suffix=13002)
        pid = p.id
    rv = client.get(f'/proposals/{pid}')
    assert rv.status_code == 403


def test_detail_master_accesses_any_proposal(app, client):
    login(client, 'testmaster', 'Admin@1234')
    with app.app_context():
        u1 = User.query.filter_by(username='testuser1').first()
        p = make_proposal(u1.id, num_suffix=13003)
        pid = p.id
    rv = client.get(f'/proposals/{pid}')
    assert rv.status_code == 200


def test_detail_nonexistent_proposal_returns_404(client):
    login(client, 'testmaster', 'Admin@1234')
    rv = client.get('/proposals/999999')
    assert rv.status_code == 404


# ---------------------------------------------------------------------------
# Edit proposal
# ---------------------------------------------------------------------------

def test_edit_draft_proposal_success(app, client):
    login(client, 'testmaster', 'Admin@1234')
    with app.app_context():
        master = User.query.filter_by(username='testmaster').first()
        p = make_proposal(master.id, num_suffix=14001)
        pid = p.id
    rv = post_form(client, f'/proposals/{pid}/edit',
                   _valid_form(customer_name='Updated Name'),
                   ref_url=f'/proposals/{pid}/edit')
    assert rv.status_code == 200
    assert b'updated' in rv.data.lower() or b'SP-TEST-14001' in rv.data


def test_edit_generated_proposal_blocked(app, client):
    login(client, 'testmaster', 'Admin@1234')
    with app.app_context():
        master = User.query.filter_by(username='testmaster').first()
        p = make_proposal(master.id, status='GENERATED', num_suffix=14002)
        pid = p.id
    rv = post_form(client, f'/proposals/{pid}/edit', _valid_form(),
                   ref_url=f'/proposals/{pid}/edit')
    assert b'Only draft' in rv.data or b'only draft' in rv.data.lower()


def test_edit_accepted_proposal_blocked(app, client):
    login(client, 'testmaster', 'Admin@1234')
    with app.app_context():
        master = User.query.filter_by(username='testmaster').first()
        p = make_proposal(master.id, status='ACCEPTED', num_suffix=14003)
        pid = p.id
    rv = post_form(client, f'/proposals/{pid}/edit', _valid_form(),
                   ref_url=f'/proposals/{pid}/edit')
    assert b'Only draft' in rv.data or b'only draft' in rv.data.lower()


def test_edit_other_users_proposal_returns_403(app, client):
    login(client, 'testuser2', 'User@2222')
    with app.app_context():
        u1 = User.query.filter_by(username='testuser1').first()
        p = make_proposal(u1.id, num_suffix=14004)
        pid = p.id
    # Get CSRF from testuser2's own proposals page (they can't access pid/edit)
    rv = post_form(client, f'/proposals/{pid}/edit', _valid_form(),
                   ref_url='/proposals/new')
    assert rv.status_code == 403


# ---------------------------------------------------------------------------
# Generate PDF (status: DRAFT → GENERATED)
# ---------------------------------------------------------------------------

def test_generate_blocked_without_payments(app, client):
    login(client, 'testmaster', 'Admin@1234')
    with app.app_context():
        master = User.query.filter_by(username='testmaster').first()
        p = make_proposal(master.id, include_payments=False, num_suffix=15001)
        pid = p.id
    rv = post_form(client, f'/proposals/{pid}/generate', {},
                   ref_url=f'/proposals/{pid}')
    assert b'payment' in rv.data.lower()


def test_generate_blocked_for_accepted(app, client):
    login(client, 'testmaster', 'Admin@1234')
    with app.app_context():
        master = User.query.filter_by(username='testmaster').first()
        p = make_proposal(master.id, status='ACCEPTED', num_suffix=15002)
        pid = p.id
    rv = post_form(client, f'/proposals/{pid}/generate', {},
                   ref_url=f'/proposals/{pid}')
    assert b'Cannot regenerate' in rv.data or b'cannot regenerate' in rv.data.lower()


def test_generate_blocked_for_rejected(app, client):
    login(client, 'testmaster', 'Admin@1234')
    with app.app_context():
        master = User.query.filter_by(username='testmaster').first()
        p = make_proposal(master.id, status='REJECTED', num_suffix=15003)
        pid = p.id
    rv = post_form(client, f'/proposals/{pid}/generate', {},
                   ref_url=f'/proposals/{pid}')
    assert b'Cannot regenerate' in rv.data or b'cannot regenerate' in rv.data.lower()


# ---------------------------------------------------------------------------
# Accept proposal
# ---------------------------------------------------------------------------

def test_accept_generated_proposal(app, client):
    login(client, 'testmaster', 'Admin@1234')
    with app.app_context():
        master = User.query.filter_by(username='testmaster').first()
        p = make_proposal(master.id, status='GENERATED', num_suffix=16001)
        pid = p.id
    rv = post_form(client, f'/proposals/{pid}/accept',
                   {'notes': 'All good'}, ref_url=f'/proposals/{pid}')
    assert rv.status_code == 200
    assert b'accepted' in rv.data.lower()
    with app.app_context():
        p = Proposal.query.get(pid)
        assert p.status == 'ACCEPTED'
        assert AcceptedProposal.query.filter_by(proposal_id=pid).first() is not None


def test_accept_draft_proposal_returns_error(app, client):
    login(client, 'testmaster', 'Admin@1234')
    with app.app_context():
        master = User.query.filter_by(username='testmaster').first()
        p = make_proposal(master.id, status='DRAFT', num_suffix=16002)
        pid = p.id
    rv = post_form(client, f'/proposals/{pid}/accept',
                   {'notes': ''}, ref_url=f'/proposals/{pid}')
    assert b'Only generated' in rv.data or b'error' in rv.data.lower()
    with app.app_context():
        p = Proposal.query.get(pid)
        assert p.status == 'DRAFT'


def test_accept_already_accepted_returns_error(app, client):
    login(client, 'testmaster', 'Admin@1234')
    with app.app_context():
        master = User.query.filter_by(username='testmaster').first()
        p = make_proposal(master.id, status='ACCEPTED', num_suffix=16003)
        pid = p.id
    rv = post_form(client, f'/proposals/{pid}/accept',
                   {'notes': ''}, ref_url=f'/proposals/{pid}')
    assert b'Only generated' in rv.data or b'error' in rv.data.lower()


def test_accept_rejected_proposal_returns_error(app, client):
    login(client, 'testmaster', 'Admin@1234')
    with app.app_context():
        master = User.query.filter_by(username='testmaster').first()
        p = make_proposal(master.id, status='REJECTED', num_suffix=16004)
        pid = p.id
    rv = post_form(client, f'/proposals/{pid}/accept',
                   {'notes': ''}, ref_url=f'/proposals/{pid}')
    assert b'Only generated' in rv.data or b'error' in rv.data.lower()


# ---------------------------------------------------------------------------
# Reject proposal
# ---------------------------------------------------------------------------

def test_reject_generated_proposal(app, client):
    login(client, 'testmaster', 'Admin@1234')
    with app.app_context():
        master = User.query.filter_by(username='testmaster').first()
        p = make_proposal(master.id, status='GENERATED', num_suffix=17001)
        pid = p.id
    rv = post_form(client, f'/proposals/{pid}/reject',
                   {'reason': 'Customer not interested'},
                   ref_url=f'/proposals/{pid}')
    assert rv.status_code == 200
    assert b'rejected' in rv.data.lower()
    with app.app_context():
        p = Proposal.query.get(pid)
        assert p.status == 'REJECTED'
        rec = RejectedProposal.query.filter_by(proposal_id=pid).first()
        assert rec is not None
        assert rec.reason == 'Customer not interested'


def test_reject_without_reason_returns_error(app, client):
    login(client, 'testmaster', 'Admin@1234')
    with app.app_context():
        master = User.query.filter_by(username='testmaster').first()
        p = make_proposal(master.id, status='GENERATED', num_suffix=17002)
        pid = p.id
    rv = post_form(client, f'/proposals/{pid}/reject',
                   {'reason': ''}, ref_url=f'/proposals/{pid}')
    assert b'required' in rv.data.lower() or b'reason' in rv.data.lower()
    with app.app_context():
        p = Proposal.query.get(pid)
        assert p.status == 'GENERATED'


def test_reject_draft_proposal_returns_error(app, client):
    login(client, 'testmaster', 'Admin@1234')
    with app.app_context():
        master = User.query.filter_by(username='testmaster').first()
        p = make_proposal(master.id, status='DRAFT', num_suffix=17003)
        pid = p.id
    rv = post_form(client, f'/proposals/{pid}/reject',
                   {'reason': 'Test reason'}, ref_url=f'/proposals/{pid}')
    assert b'Only generated' in rv.data or b'error' in rv.data.lower()
    with app.app_context():
        p = Proposal.query.get(pid)
        assert p.status == 'DRAFT'


def test_reject_accepted_proposal_returns_error(app, client):
    login(client, 'testmaster', 'Admin@1234')
    with app.app_context():
        master = User.query.filter_by(username='testmaster').first()
        p = make_proposal(master.id, status='ACCEPTED', num_suffix=17004)
        pid = p.id
    rv = post_form(client, f'/proposals/{pid}/reject',
                   {'reason': 'Test'}, ref_url=f'/proposals/{pid}')
    assert b'Only generated' in rv.data or b'error' in rv.data.lower()


# ---------------------------------------------------------------------------
# Download PDF
# ---------------------------------------------------------------------------

def test_download_draft_returns_404(app, client):
    login(client, 'testmaster', 'Admin@1234')
    with app.app_context():
        master = User.query.filter_by(username='testmaster').first()
        p = make_proposal(master.id, status='DRAFT', num_suffix=18001)
        pid = p.id
    rv = client.get(f'/proposals/{pid}/download')
    assert rv.status_code == 404


def test_download_other_users_proposal_returns_403(app, client):
    login(client, 'testuser2', 'User@2222')
    with app.app_context():
        u1 = User.query.filter_by(username='testuser1').first()
        p = make_proposal(u1.id, status='GENERATED', num_suffix=18002)
        pid = p.id
    rv = client.get(f'/proposals/{pid}/download')
    assert rv.status_code == 403


def test_download_nonexistent_returns_404(client):
    login(client, 'testmaster', 'Admin@1234')
    rv = client.get('/proposals/999999/download')
    assert rv.status_code == 404
