import uuid
from datetime import datetime, timezone
from config.extensions import db


class ConnectorReport(db.Model):
    """Cached 'Database Report' for a SQL connector.

    One row per connector, upserted when the report is (re)generated (chained to
    the schema crawl or triggered on demand). `data` holds the full report JSON
    (overview, critical tables, architecture, measured scores, AI summary).
    """
    __tablename__ = 'connector_reports'

    id = db.Column(db.Uuid, primary_key=True, default=uuid.uuid4)
    connector_id = db.Column(
        db.Uuid, db.ForeignKey('connectors.id', ondelete='CASCADE'),
        nullable=False, unique=True, index=True,
    )
    organization_id = db.Column(db.Uuid, db.ForeignKey('organizations.id'), nullable=False)
    status = db.Column(db.String, nullable=False, default='pending')  # pending|running|done|failed
    data = db.Column(db.JSON, nullable=True)
    generated_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
