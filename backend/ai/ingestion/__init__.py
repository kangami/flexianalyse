"""
Shared document ingestion pipeline.

Used by any agent that needs to ingest and chunk documents.
"""

from .extractor import DocumentExtractor, ExtractionResult, ExtractedChunk, SUPPORTED_MIME_TYPES
from .embedder import Embedder

__all__ = [
    "DocumentExtractor",
    "ExtractionResult",
    "ExtractedChunk",
    "SUPPORTED_MIME_TYPES",
    "Embedder",
]
