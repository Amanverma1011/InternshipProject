import os
import hashlib
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple

from flask import current_app, render_template
from models import db
from models.proposal import Proposal, ProposalVersion, ProposalFile
from models.company import CompanySetting
from models.template import Template
from models.user import User
from services.proposal_service import build_snapshot
from services.audit_service import log_action

logger = logging.getLogger(__name__)


def get_storage_path() -> Path:
    cfg = current_app.config.get('STORAGE_PATH', 'storage/proposals')
    p = Path(cfg)
    base = p if p.is_absolute() else Path(current_app.root_path) / p
    base.mkdir(parents=True, exist_ok=True)
    return base


def generate_pdf_for_proposal(proposal: Proposal, user: User) -> Tuple[bool, str, Optional[str]]:
    try:
        from weasyprint import HTML as WeasyprintHTML
    except ImportError:
        return False, 'WeasyPrint not installed. Run: pip install weasyprint', None

    company = CompanySetting.get_all_dict()
    snapshot = build_snapshot(proposal, company)

    template = None
    if proposal.template_id:
        template = Template.query.get(proposal.template_id)
    if not template:
        template = Template.query.filter_by(
            system_type=proposal.system_type, is_active=True
        ).order_by(Template.version.desc()).first()

    html_template = f'pdf/{proposal.system_type.lower()}.html'

    try:
        html_content = render_template(
            html_template,
            proposal=proposal,
            snapshot=snapshot,
            company=company,
            modules=list(proposal.modules),
            addons=list(proposal.addons.order_by('sequence')),
            payments=list(proposal.payments.order_by('sequence')),
            battery=proposal.battery,
        )
    except Exception as e:
        logger.error(f'Template render error: {e}')
        return False, f'Template error: {str(e)}', None

    now = datetime.utcnow()
    storage_base = get_storage_path()
    year_month = now.strftime('%Y/%m')
    output_dir = storage_base / year_month
    output_dir.mkdir(parents=True, exist_ok=True)

    version_num = proposal.versions.count() + 1
    file_name = f'{proposal.proposal_number}-v{version_num}.pdf'
    file_path = output_dir / file_name

    try:
        WeasyprintHTML(string=html_content).write_pdf(str(file_path))
    except Exception as e:
        logger.error(f'WeasyPrint PDF error: {e}')
        return False, f'PDF generation failed: {str(e)}', None

    sha256 = _file_sha256(str(file_path))
    file_size = os.path.getsize(str(file_path))

    try:
        pv = ProposalVersion(
            proposal_id=proposal.id,
            version_number=version_num,
            template_id=template.id if template else None,
            template_version=template.version if template else None,
            generated_by=user.id,
            snapshot=snapshot
        )
        db.session.add(pv)
        db.session.flush()

        db.session.add(ProposalFile(
            proposal_id=proposal.id,
            proposal_version_id=pv.id,
            file_name=file_name,
            file_path=str(file_path),
            file_size=file_size,
            sha256=sha256
        ))

        proposal.status = 'GENERATED'
        proposal.template_id = template.id if template else None
        proposal.template_version = template.version if template else None
        proposal.snapshot = snapshot

        db.session.commit()
        log_action('GENERATE_PROPOSAL', 'proposal', proposal.id, {
            'proposal_number': proposal.proposal_number,
            'file': file_name, 'version': version_num
        })
        return True, '', str(file_path)

    except Exception as e:
        db.session.rollback()
        logger.error(f'DB save after PDF error: {e}')
        return False, f'Database error: {str(e)}', None


def _file_sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            h.update(chunk)
    return h.hexdigest()
