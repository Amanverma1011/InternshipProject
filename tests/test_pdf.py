"""Tests for PDF generation and file serving."""
import os
import pytest
from decimal import Decimal
from datetime import date

from tests.conftest import login, make_proposal
from models import db
from models.proposal import Proposal, ProposalFile, ProposalVersion
from models.user import User
from services.pdf_service import generate_pdf_for_proposal


# ---------------------------------------------------------------------------
# PDF generation via service (direct, not HTTP)
# ---------------------------------------------------------------------------

def test_pdf_generation_ongrid_success(app):
    """PDF is created on disk and DB records are written."""
    with app.app_context():
        master = User.query.filter_by(username='testmaster').first()
        p = make_proposal(master.id, system_type='ONGRID', num_suffix=20001)
        pid = p.id

        ok, err, path = generate_pdf_for_proposal(p, master)
        assert ok is True, f'PDF failed: {err}'
        assert path is not None
        assert os.path.exists(path)
        assert os.path.getsize(path) > 10000  # meaningful file

        # DB updated
        p_fresh = Proposal.query.get(pid)
        assert p_fresh.status == 'GENERATED'
        assert p_fresh.files.count() == 1
        assert p_fresh.versions.count() == 1


def test_pdf_generation_hybrid_success(app):
    with app.app_context():
        master = User.query.filter_by(username='testmaster').first()
        p = make_proposal(master.id, system_type='HYBRID', num_suffix=20002)
        pid = p.id

        from models.proposal import ProposalBattery
        db.session.add(ProposalBattery(
            proposal_id=pid, capacity_kwh=Decimal('10'), quantity=2, make='Sologix'
        ))
        db.session.commit()
        db.session.refresh(p)

        ok, err, path = generate_pdf_for_proposal(p, master)
        assert ok is True, f'PDF failed: {err}'
        assert os.path.exists(path)


def test_pdf_is_valid_pdf_bytes(app):
    """Generated file starts with %PDF magic bytes."""
    with app.app_context():
        master = User.query.filter_by(username='testmaster').first()
        p = make_proposal(master.id, num_suffix=20003)

        ok, err, path = generate_pdf_for_proposal(p, master)
        assert ok is True, err
        with open(path, 'rb') as f:
            header = f.read(4)
        assert header == b'%PDF'


def test_pdf_file_name_contains_customer_name(app):
    with app.app_context():
        master = User.query.filter_by(username='testmaster').first()
        p = make_proposal(master.id, num_suffix=20004)
        p.customer_name = 'Priya Singh'
        db.session.commit()

        ok, err, path = generate_pdf_for_proposal(p, master)
        assert ok is True, err
        assert 'Priya Singh' in os.path.basename(path)


def test_pdf_version_increments_on_regenerate(app):
    """Regenerating a GENERATED proposal creates version 2."""
    with app.app_context():
        master = User.query.filter_by(username='testmaster').first()
        p = make_proposal(master.id, num_suffix=20005)
        pid = p.id

        ok1, _, _ = generate_pdf_for_proposal(p, master)
        assert ok1

        db.session.refresh(p)
        ok2, _, _ = generate_pdf_for_proposal(p, master)
        assert ok2

        p_fresh = Proposal.query.get(pid)
        assert p_fresh.versions.count() == 2
        assert p_fresh.files.count() == 2


def test_pdf_generation_without_qrcode_still_works(app, monkeypatch):
    """If qrcode is unavailable, PDF generation should still succeed (no QR)."""
    import sys

    # Force qrcode import to fail inside pdf_service by setting sys.modules entry to None
    monkeypatch.setitem(sys.modules, 'qrcode', None)

    with app.app_context():
        master = User.query.filter_by(username='testmaster').first()
        p = make_proposal(master.id, num_suffix=20006)
        ok, err, path = generate_pdf_for_proposal(p, master)

    # monkeypatch automatically restores sys.modules after the test
    assert ok is True, f'PDF failed when qrcode missing: {err}'
    assert os.path.exists(path)


# ---------------------------------------------------------------------------
# Download via HTTP (test client)
# ---------------------------------------------------------------------------

def test_download_generated_proposal_serves_pdf(app, client):
    login(client, 'testmaster', 'Admin@1234')
    with app.app_context():
        master = User.query.filter_by(username='testmaster').first()
        p = make_proposal(master.id, num_suffix=21001)
        ok, err, _ = generate_pdf_for_proposal(p, master)
        assert ok, err
        pid = p.id

    rv = client.get(f'/proposals/{pid}/download')
    assert rv.status_code == 200
    assert rv.content_type == 'application/pdf'
    assert rv.data[:4] == b'%PDF'


def test_download_includes_correct_filename_header(app, client):
    login(client, 'testmaster', 'Admin@1234')
    with app.app_context():
        master = User.query.filter_by(username='testmaster').first()
        p = make_proposal(master.id, num_suffix=21002)
        p.customer_name = 'Ravi Sharma'
        db.session.commit()
        ok, err, _ = generate_pdf_for_proposal(p, master)
        assert ok, err
        pid = p.id

    rv = client.get(f'/proposals/{pid}/download')
    assert rv.status_code == 200
    cd = rv.headers.get('Content-Disposition', '')
    assert 'Ravi Sharma' in cd or '.pdf' in cd


def test_download_draft_returns_404(app, client):
    login(client, 'testmaster', 'Admin@1234')
    with app.app_context():
        master = User.query.filter_by(username='testmaster').first()
        p = make_proposal(master.id, status='DRAFT', num_suffix=21003)
        pid = p.id
    rv = client.get(f'/proposals/{pid}/download')
    assert rv.status_code == 404


def test_download_logs_audit_action(app, client):
    """Downloading a PDF should create a DOWNLOAD_PDF audit log entry."""
    login(client, 'testmaster', 'Admin@1234')
    with app.app_context():
        master = User.query.filter_by(username='testmaster').first()
        p = make_proposal(master.id, num_suffix=21004)
        ok, err, _ = generate_pdf_for_proposal(p, master)
        assert ok, err
        pid = p.id

    client.get(f'/proposals/{pid}/download')

    with app.app_context():
        from models.audit import AuditLog
        log = AuditLog.query.filter_by(action='DOWNLOAD_PDF',
                                       entity_id=pid).first()
        assert log is not None


# ---------------------------------------------------------------------------
# File service edge cases
# ---------------------------------------------------------------------------

def test_download_file_missing_from_disk_returns_404(app, client):
    """ProposalFile record exists but file deleted from disk → 404."""
    login(client, 'testmaster', 'Admin@1234')
    with app.app_context():
        master = User.query.filter_by(username='testmaster').first()
        p = make_proposal(master.id, num_suffix=22001)
        ok, err, path = generate_pdf_for_proposal(p, master)
        assert ok, err
        pid = p.id
        # Delete the actual file
        os.remove(path)

    rv = client.get(f'/proposals/{pid}/download')
    assert rv.status_code == 404
