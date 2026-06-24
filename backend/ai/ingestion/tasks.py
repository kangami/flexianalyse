"""
Backward-compatibility shim.

Ingestion tasks have been moved to the office_manager agent:
    ai.agents.office_manager.ingestion.tasks
"""

from ai.agents.office_manager.ingestion.tasks import (  # noqa: F401
    trigger_ingestion_for_connector,
    ingest_batch,
    ingest_single_file,
)

__all__ = [
    "trigger_ingestion_for_connector",
    "ingest_batch",
    "ingest_single_file",
]
