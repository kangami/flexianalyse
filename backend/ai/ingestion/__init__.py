"""
Shared document ingestion pipeline.

Used by any agent that needs to ingest and chunk documents.
"""

from .embedder import Embedder

__all__ = [
    "DocumentExtractor",
    "ExtractionResult",
    "ExtractedChunk",
    "SUPPORTED_MIME_TYPES",
    "Embedder",
]

# The extractor pulls docling → torch/transformers/onnx (worker-only, ~GB of
# deps). Import it LAZILY on attribute access so merely importing this package
# (e.g. for the Embedder, or to enqueue a task from the API) does not require
# those libraries. `from ai.ingestion import DocumentExtractor` still works.
_LAZY_FROM_EXTRACTOR = {
    "DocumentExtractor", "ExtractionResult", "ExtractedChunk", "SUPPORTED_MIME_TYPES",
}


def __getattr__(name):
    if name in _LAZY_FROM_EXTRACTOR:
        from . import extractor
        return getattr(extractor, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
