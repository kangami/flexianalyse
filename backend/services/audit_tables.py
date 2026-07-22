"""Detect audit / log / system tables by name.

Used at crawl time to tag `connector_schema_tables.is_audit`, and by the diagram
to filter live-introspected tables. Deliberately CONSERVATIVE: hiding a real
business table (so the agent can't answer about it) is worse than leaving an audit
table in, and the connector toggle is the safety valve. We match on whole
name-tokens (split on `_`/non-word and camelCase), never substrings — so `catalog`
isn't caught by `log`, `blog` isn't caught by `log`, `temperature` isn't `temp`.
"""
import re

# Known framework/system bookkeeping tables — always safe to treat as non-business.
_SYSTEM_TABLES = {
    "alembic_version", "flyway_schema_history", "schema_migrations",
    "ar_internal_metadata", "spatial_ref_sys", "geometry_columns",
    "geography_columns", "django_migrations", "knex_migrations",
    "knex_migrations_lock", "__migrationhistory",
}

# A name whose token set intersects these is treated as audit/log.
_AUDIT_TOKENS = {
    "audit", "audits", "auditlog", "auditlogs",
    "log", "logs", "logging",
    "hist", "history", "histories",
    "journal", "journals", "changelog", "changelogs",
    "archive", "archives", "archived",
    "bak", "backup", "backups",
    "staging", "stg", "tmp", "temp",
}

_PREFIXES = ("sys_", "tmp_", "temp_", "stg_", "bak_", "audit_", "log_", "hist_", "z_")
_SUFFIXES = (
    "_audit", "_audits", "_log", "_logs", "_hist", "_history",
    "_journal", "_archive", "_bak", "_backup", "_stg", "_tmp",
)


def _tokens(name: str) -> set:
    lowered = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", name or "").lower()
    return {t for t in re.split(r"[_\W]+", lowered) if t}


def is_audit_table(name: str) -> bool:
    n = (name or "").strip().lower()
    if not n:
        return False
    if n in _SYSTEM_TABLES:
        return True
    if n.startswith(_PREFIXES) or n.endswith(_SUFFIXES):
        return True
    return bool(_tokens(name) & _AUDIT_TOKENS)
