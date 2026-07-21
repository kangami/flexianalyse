"""Audit log — read-only listing for the current organisation.

Scoped to the caller's organisation (validated by the api_v2 before_request).
Rows are written automatically by services/audit.py (after_request hook) and by
explicit record() calls on sensitive operations.
"""
from flask import jsonify, request

from models.audit_log import AuditLog
from services.request_context import current_organization_id


def register(api_bp):

    @api_bp.route("/audit-logs", methods=["GET"])
    def list_audit_logs():
        """Recent audit entries for the current org (newest first)."""
        org_id = current_organization_id()
        if not org_id:
            return jsonify({"error": "Aucune organisation associée"}), 400
        try:
            limit = min(int(request.args.get("limit", 100)), 500)
        except (TypeError, ValueError):
            limit = 100
        rows = (
            AuditLog.query
            .filter_by(organization_id=org_id)
            .order_by(AuditLog.created_at.desc())
            .limit(limit)
            .all()
        )
        return jsonify({"data": [
            {
                "id": str(r.id),
                "action": r.action,
                "resource": r.resource,
                "tool": r.tool,
                "user_id": str(r.user_id) if r.user_id else None,
                "metadata": r.audit_metadata or {},
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ]})
