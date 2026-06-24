"""
Backward-compatibility shim.

The document extractor has been moved to the shared ingestion pipeline:
    ai.ingestion.extractor

Import from there directly:
    from ai.ingestion.extractor import DocumentExtractor, ExtractionResult, ExtractedChunk
"""

# Re-export everything so existing imports keep working without changes.
from ai.ingestion.extractor import (  # noqa: F401
    DocumentExtractor,
    ExtractionResult,
    ExtractedChunk,
    SUPPORTED_MIME_TYPES,
    EXCLUDED_PREFIXES,
    SEMANTIC_FORMATS,
    FIXED_FORMATS,
)

__all__ = [
    "DocumentExtractor",
    "ExtractionResult",
    "ExtractedChunk",
    "SUPPORTED_MIME_TYPES",
]

# ── Everything below this line has been removed ──────────────────────────────
# See: backend/ai/ingestion/extractor.py