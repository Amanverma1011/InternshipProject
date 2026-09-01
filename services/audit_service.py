import logging
from typing import Optional, Dict, Any
from flask import request
from flask_login import current_user
from models import db
from models.audit import AuditLog

logger = logging.getLogger(__name__)


def log_action(
    action: str,
    entity_type: Optional[str] = None,
    entity_id: Optional[int] = None,
    details: Optional[Dict[str, Any]] = None,
    user_id: Optional[int] = None
) -> None:
    try:
        uid = user_id
        if uid is None:
            try:
                if current_user and current_user.is_authenticated:
                    uid = current_user.id
            except Exception:
                pass

        ip = None
        try:
            ip = request.remote_addr
        except RuntimeError:
            pass

        log = AuditLog(
            user_id=uid,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            details=details,
            ip_address=ip
        )
        db.session.add(log)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        logger.error(f'Audit log failed: {e}')
