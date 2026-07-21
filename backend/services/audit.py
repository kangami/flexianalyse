"""Audit trail — records who did what, when.

Two entry points:
  - record(...)         : write one audit row for a specific event. Resilient:
                          an audit failure must NEVER break the request it audits.
  - audit_request(resp) : an after_request hook that logs every mutating call
                          (POST/PUT/PATCH/DELETE) with actor / org / path / status,
                          for broad automatic coverage.

The actor and organisation come from the request context populated by the
blueprints' before_request auth (services/request_context).
"""
import logging

from flask import request

from config.extensions import db
from models.audit_log import AuditLog, AuditAction
from services.request_context import current_user_id, current_organization_id

logger = logging.getLogger(__name__)

_METHOD_ACTION = {
    "POST": AuditAction.CREATE,
    "PUT": AuditAction.UPDATE,
    "PATCH": AuditAction.UPDATE,
    "DELETE": AuditAction.DELETE,
}

# Noisy / irrelevant paths we don't want to record (health checks, etc.).
_SKIP_SUFFIXES = ("/health", "/servers/status")


def record(action, resource=None, tool=None, metadata=None, org_id=None, user_id=None) -> None:
    """Write one audit row. Never raises — auditing must not break the action."""
    try:
        db.session.add(AuditLog(
            organization_id=org_id or current_organization_id(),
            user_id=user_id or current_user_id(),
            action=str(action) if action else None,
            resource=resource,
            tool=tool,
            audit_metadata=metadata or {},
        ))
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        logger.warning("Audit record failed (%s %s): %s", action, resource, e)


def audit_request(response):
    """after_request hook: record mutating requests automatically."""
    try:
        method = request.method
        if method in ("GET", "HEAD", "OPTIONS"):
            return response
        path = request.path or ""
        if any(path.endswith(s) for s in _SKIP_SUFFIXES):
            return response
        record(
            action=_METHOD_ACTION.get(method, AuditAction.UPDATE),
            resource=path,
            metadata={
                "method": method,
                "path": path,
                "status": getattr(response, "status_code", None),
                "ip": request.headers.get("X-Forwarded-For", request.remote_addr),
            },
        )
    except Exception as e:  # never let auditing break the response
        logger.warning("audit_request hook failed: %s", e)
    return response
