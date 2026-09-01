from pathlib import Path
from typing import Optional
from flask import send_file, abort
from models.proposal import Proposal, ProposalFile


def get_latest_pdf(proposal: Proposal) -> Optional[ProposalFile]:
    return proposal.files.order_by(ProposalFile.created_at.desc()).first()


def send_proposal_pdf(proposal: Proposal, user) -> object:
    if not user.is_master() and proposal.created_by != user.id:
        abort(403)
    pf = get_latest_pdf(proposal)
    if not pf:
        abort(404)
    file_path = Path(pf.file_path)
    if not file_path.exists():
        abort(404)
    return send_file(
        str(file_path),
        mimetype='application/pdf',
        as_attachment=True,
        download_name=pf.file_name
    )
