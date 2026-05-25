"""
Docling-powered structured document parser.

Workflow:
  raw bytes → Docling → DoclingDocument
                         ├── pages
                         ├── headings (H1/H2/H3)
                         ├── tables (structured)
                         ├── layout metadata
                         └── HybridChunker
                              └── chunks with {page, heading, element_type, section}

Falls back to PyPDF2 / python-docx if Docling is unavailable or crashes.
"""
import logging
import os
import tempfile
import hashlib
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Lazy singleton – initialised once on first call
_converter = None


def _get_converter():
    """Return the Docling DocumentConverter singleton, or None if unavailable."""
    global _converter
    if _converter is not None:
        return _converter

    try:
        from docling.document_converter import DocumentConverter
        from docling.datamodel.pipeline_options import PdfPipelineOptions
        from docling.backend.pypdfium2_backend import PyPdfiumDocumentBackend
        from docling.datamodel.base_models import InputFormat
        from docling.document_converter import PdfFormatOption

        pipeline_options = PdfPipelineOptions()
        pipeline_options.do_ocr = False
        pipeline_options.do_table_structure = False  # disable TableFormer — prevents std::bad_alloc on large pages

        _converter = DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(
                    pipeline_options=pipeline_options,
                    backend=PyPdfiumDocumentBackend,
                )
            }
        )
        logger.info("Docling DocumentConverter initialised (OCR=off, TableFormer=off)")
    except Exception as exc:
        logger.warning("Docling unavailable – will fall back to basic extraction. Reason: %s", exc)
        _converter = None

    return _converter


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def parse_with_docling(
    raw_bytes: bytes,
    extension: str,
    file_name: str = "document",
) -> Optional[Tuple[List[Dict[str, Any]], str, Dict[str, Any]]]:
    """
    Parse *raw_bytes* with Docling and return structured chunks.

    Returns
    -------
    (chunks_with_meta, full_markdown, docling_metadata)  on success
    None                                                  on failure (caller must fall back)

    Each element of *chunks_with_meta*:
    {
        "text":         str,        # chunk text
        "page":         int,        # 1-indexed page number
        "chunk_id":     str,        # "<doc_hash>_chunk_0", "<doc_hash>_chunk_1", …
        "chunk_index":  int,
        "element_type": str,        # "text" | "table" | "heading" | "list_item"
        "headings":     list[str],  # parent heading hierarchy  e.g. ["Chapter 2", "Section 3"]
        "section":      str,        # "Chapter 2 > Section 3"
    }
    """
    converter = _get_converter()
    if converter is None:
        return None

    tmp_path = None
    try:
        suffix = f".{extension}" if extension else ".bin"
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(raw_bytes)
            tmp_path = tmp.name

        logger.info("Docling: parsing %s (%d bytes) …", file_name, len(raw_bytes))
        result = converter.convert(tmp_path)
        doc = result.document

        # Full markdown – preserves headings, tables, lists
        try:
            full_text = doc.export_to_markdown()
        except Exception:
            try:
                full_text = doc.export_to_text()
            except Exception:
                full_text = ""

        num_pages = len(doc.pages) if hasattr(doc, "pages") and doc.pages else 1

        docling_meta: Dict[str, Any] = {
            "parser": "docling",
            "num_pages": num_pages,
        }

        chunks_with_meta = _chunk_document(doc)

        # Ensure chunk IDs are unique across multiple uploaded documents.
        doc_prefix = hashlib.sha256(raw_bytes).hexdigest()[:16]
        for idx, chunk in enumerate(chunks_with_meta):
            chunk["chunk_id"] = f"{doc_prefix}_chunk_{idx}"
            chunk["chunk_index"] = idx

        logger.info(
            "Docling: %s → %d pages, %d chunks",
            file_name, num_pages, len(chunks_with_meta),
        )
        return chunks_with_meta, full_text, docling_meta

    except Exception as exc:
        logger.warning("Docling parsing failed for %s: %s", file_name, exc)
        return None
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except OSError:
                pass


# ---------------------------------------------------------------------------
# Internal chunking helpers
# ---------------------------------------------------------------------------

def _chunk_document(doc) -> List[Dict[str, Any]]:
    """Use Docling's HybridChunker; fall back to element iteration on error."""
    try:
        from docling.chunking import HybridChunker
        chunker = HybridChunker()
        raw_chunks = list(chunker.chunk(doc))
        return _process_hybrid_chunks(raw_chunks)
    except Exception as exc:
        logger.warning("HybridChunker failed (%s) – falling back to element iteration", exc)
        return _chunk_by_elements(doc)


def _process_hybrid_chunks(raw_chunks) -> List[Dict[str, Any]]:
    """Convert HybridChunker output to our standard chunk dict list."""
    result = []
    for i, chunk in enumerate(raw_chunks):
        try:
            text = chunk.text
        except Exception:
            continue
        if not text or not text.strip():
            continue

        page = _page_from_chunk(chunk)
        headings = _headings_from_chunk(chunk)
        section = " > ".join(headings) if headings else ""

        if i == 0:
            logger.debug(
                "[docling] chunk#0 sample – page=%s headings=%s section=%s text=%.80s",
                page, headings, section, text,
            )

        result.append({
            "text":         text,
            "page":         page,
            "chunk_id":     f"chunk_{i}",
            "chunk_index":  i,
            "element_type": _type_from_chunk(chunk),
            "headings":     headings,
            "section":      section,
        })
    return result


def _chunk_by_elements(doc) -> List[Dict[str, Any]]:
    """Fallback: walk every DocItem when HybridChunker is unavailable."""
    result = []
    idx = 0
    try:
        for item, _level in doc.iterate_items():
            text = getattr(item, "text", None) or ""
            if not text.strip():
                continue

            page = 1
            try:
                if item.prov:
                    page = item.prov[0].page_no
            except Exception:
                pass

            label = str(getattr(item, "label", "text")).lower()
            if "table" in label:
                etype = "table"
            elif "head" in label or "title" in label:
                etype = "heading"
            elif "list" in label:
                etype = "list_item"
            else:
                etype = "text"

            if idx == 0:
                logger.debug(
                    "[docling-fallback] element#0 – page=%s etype=%s text=%.80s",
                    page, etype, text,
                )

            result.append({
                "text":         text,
                "page":         page,
                "chunk_id":     f"chunk_{idx}",
                "chunk_index":  idx,
                "element_type": etype,
                "headings":     [],
                "section":      "",
            })
            idx += 1
    except Exception as exc:
        logger.warning("Element iteration failed: %s", exc)
    return result


# ---------------------------------------------------------------------------
# Attribute extractors (robust to API changes across Docling versions)
# ---------------------------------------------------------------------------

def _page_from_chunk(chunk) -> int:
    """Return the page number of a chunk, trying multiple attribute paths.

    Docling v1.x stores provenance under meta.doc_items[i].prov[j].page_no.
    Docling v2.x may expose it directly as meta.prov[j].page_no.
    """
    for path in [
        # Docling v1.x (e.g. 1.16.x): doc_items list inside meta
        lambda c: c.meta.doc_items[0].prov[0].page_no,
        # Docling v1.x alternative: iterate all doc_items
        lambda c: next(
            item.prov[0].page_no
            for item in c.meta.doc_items
            if item.prov
        ),
        # Docling v2.x: prov directly on meta
        lambda c: c.meta.prov[0].page_no,
        lambda c: c.meta.page_no,
        lambda c: c.prov[0].page_no,
    ]:
        try:
            val = path(chunk)
            if val is not None:
                page = int(val)
                if page > 0:
                    return page
        except Exception:
            pass
    return 1


def _headings_from_chunk(chunk) -> List[str]:
    """Return the heading hierarchy list for a chunk."""
    try:
        headings = chunk.meta.headings
        if headings:
            return [h for h in headings if h]
    except Exception:
        pass
    return []


def _type_from_chunk(chunk) -> str:
    """Infer element type from chunk metadata."""
    try:
        if chunk.meta.captions:
            return "table"
    except Exception:
        pass
    try:
        origin = str(chunk.meta.origin).lower()
        if "table" in origin:
            return "table"
        if "head" in origin or "title" in origin:
            return "heading"
        if "list" in origin:
            return "list_item"
    except Exception:
        pass
    return "text"
