"""
Document Extractor using Docling.

Handles extraction of content from all supported file types :
  - PDF (with OCR for scanned pages)
  - DOCX, PPTX
  - XLSX, CSV
  - HTML, Markdown
  - Plain text, code files

Returns structured chunks ready for embedding.
"""

import hashlib
import io
import logging
import os
import tempfile
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.chunking import HybridChunker
from langchain_text_splitters import RecursiveCharacterTextSplitter

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Supported MIME types
# ---------------------------------------------------------------------------

SUPPORTED_MIME_TYPES = {
    # Documents
    'application/pdf':                                                              'pdf',
    'application/vnd.google-apps.document':                                         'gdoc',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document':      'docx',
    'application/msword':                                                           'docx',

    # Spreadsheets
    'application/vnd.google-apps.spreadsheet':                                      'sheet',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet':            'xlsx',
    'text/csv':                                                                     'csv',

    # Presentations
    'application/vnd.google-apps.presentation':                                     'pptx',
    'application/vnd.openxmlformats-officedocument.presentationml.presentation':    'pptx',

    # Text / Code
    'text/plain':       'text',
    'text/markdown':    'text',
    'text/html':        'html',
    'application/json': 'text',
    'text/x-python':    'text',
    'text/javascript':  'text',
}

EXCLUDED_PREFIXES = ('video/', 'audio/', 'image/gif', 'image/mp4', 'image/webp')

EXCLUDED_EXTENSIONS = {
    # Archives et binaires
    'apk', 'ipa', 'exe', 'dll', 'so', 'dylib',
    'zip', 'tar', 'gz', 'rar', '7z', 'bz2',
    'jar', 'war', 'ear', 'class',
    # Images
    'jpg', 'jpeg', 'png', 'gif', 'bmp', 'ico',
    'tiff', 'webp', 'svg', 'psd', 'ai',
    # Fonts
    'ttf', 'otf', 'woff', 'woff2', 'eot',
    # Données binaires
    'bin', 'dat', 'db', 'sqlite', 'pkl',
    # Compiled
    'pyc', 'pyo', 'o', 'a',
}

# Use semantic chunking for rich formats, fixed for flat text
SEMANTIC_FORMATS = {'pdf', 'docx', 'gdoc', 'pptx', 'html'}
FIXED_FORMATS    = {'text', 'csv', 'xlsx', 'sheet'}

FIXED_CHUNK_SIZE    = int(os.getenv('CHUNK_SIZE', '500'))
FIXED_CHUNK_OVERLAP = int(os.getenv('CHUNK_OVERLAP', '50'))


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class ExtractedChunk:
    content: str
    chunk_index: int
    chunk_type: str                     # 'text', 'table', 'title', 'code'
    page_number: Optional[int] = None
    section_title: Optional[str] = None
    token_count: Optional[int] = None
    chunk_metadata: dict = field(default_factory=dict)


@dataclass
class ExtractionResult:
    resource_title: str
    file_format: str
    content_hash: str
    chunks: list[ExtractedChunk]
    raw_size_bytes: int
    error: Optional[str] = None

    @property
    def success(self) -> bool:
        return self.error is None and len(self.chunks) > 0


# ---------------------------------------------------------------------------
# Extractor
# ---------------------------------------------------------------------------

class DocumentExtractor:
    """
    Extracts and chunks content from any supported document type.
    Uses Docling for rich formats (PDF/DOCX/PPTX) and simple splitters for flat text.
    """

    def __init__(self):
        # Docling converter — OCR enabled for scanned PDFs
        pdf_options = PdfPipelineOptions()
        pdf_options.do_ocr = True                    # OCR scanned pages
        pdf_options.do_table_structure = True        # extract tables as structured data
        #pdf_options.ocr_options.use_gpu = False      # CPU fallback (safe default)

        self._converter = DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(pipeline_options=pdf_options)
            }
        )

        self._hybrid_chunker = HybridChunker(
            tokenizer="BAAI/bge-small-en-v1.5",  # tokenizer for chunk sizing
            max_tokens=FIXED_CHUNK_SIZE,
            merge_peers=True,
        )

        self._fixed_splitter = RecursiveCharacterTextSplitter(
            chunk_size=FIXED_CHUNK_SIZE * 4,     # ~chars, not tokens
            chunk_overlap=FIXED_CHUNK_OVERLAP * 4,
            separators=["\n\n", "\n", " ", ""],
        )

    # =========================================================================
    # PUBLIC
    # =========================================================================

    def extract(
        self,
        raw_content: bytes,
        mime_type: str,
        filename: str,
    ) -> ExtractionResult:
        """
        Main entry point — extract and chunk a document.

        Args:
            raw_content : raw bytes of the file
            mime_type   : MIME type string
            filename    : original filename (used for extension fallback)

        Returns:
            ExtractionResult with chunks ready for embedding
        """
        file_format = self._detect_format(mime_type, filename)

        if file_format is None:
            return ExtractionResult(
                resource_title=filename,
                file_format='unsupported',
                content_hash='',
                chunks=[],
                raw_size_bytes=len(raw_content),
                error=f"Unsupported MIME type: {mime_type}"
            )

        content_hash = hashlib.sha256(raw_content).hexdigest()

        try:
            if file_format in SEMANTIC_FORMATS:
                chunks = self._extract_semantic(raw_content, file_format, filename)
            else:
                chunks = self._extract_fixed(raw_content, file_format, filename)

            if not chunks:
                return ExtractionResult(
                    resource_title=filename,
                    file_format=file_format,
                    content_hash=content_hash,
                    chunks=[],
                    raw_size_bytes=len(raw_content),
                    error="No extractable text found in document (empty or unreadable)",
                )

            return ExtractionResult(
                resource_title=filename,
                file_format=file_format,
                content_hash=content_hash,
                chunks=chunks,
                raw_size_bytes=len(raw_content),
            )

        except Exception as e:
            logger.error(f"Extraction failed for {filename}: {e}", exc_info=True)
            return ExtractionResult(
                resource_title=filename,
                file_format=file_format,
                content_hash=content_hash,
                chunks=[],
                raw_size_bytes=len(raw_content),
                error=str(e)
            )

    # =========================================================================
    # SEMANTIC EXTRACTION (PDF, DOCX, PPTX, HTML)
    # =========================================================================

    def _extract_semantic(
        self,
        raw_content: bytes,
        file_format: str,
        filename: str,
    ) -> list[ExtractedChunk]:
        """Use Docling HybridChunker for structure-aware chunking.
        Falls back to markdown export + fixed splitter when the chunker
        yields nothing (scanned PDFs, simple layouts, etc.).
        """

        # Write to temp file — Docling needs a file path
        suffix = f".{file_format}" if file_format not in ('gdoc',) else '.docx'
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(raw_content)
            tmp_path = tmp.name

        try:
            result = self._converter.convert(tmp_path)
            doc = result.document

            # --- Pass 1: HybridChunker (semantic, structure-aware) ---
            chunks: list[ExtractedChunk] = []
            try:
                for i, chunk in enumerate(self._hybrid_chunker.chunk(doc)):
                    text = chunk.text.strip()
                    if not text:
                        continue

                    page_num = None
                    section = None
                    chunk_type = 'text'

                    if hasattr(chunk, 'meta'):
                        meta = chunk.meta
                        if hasattr(meta, 'headings') and meta.headings:
                            section = meta.headings[-1]
                        if hasattr(meta, 'doc_items'):
                            for item in meta.doc_items:
                                # Page number lives in provenance (prov)
                                if page_num is None:
                                    prov = getattr(item, 'prov', None)
                                    if prov:
                                        page_num = getattr(prov[0], 'page_no', None)
                                label = getattr(item, 'label', '')
                                if 'table' in str(label).lower():
                                    chunk_type = 'table'
                                    break
                                elif 'title' in str(label).lower() or 'heading' in str(label).lower():
                                    chunk_type = 'title'
                                    break
                                elif 'code' in str(label).lower():
                                    chunk_type = 'code'
                                    break

                    chunks.append(ExtractedChunk(
                        content=text,
                        chunk_index=i,
                        chunk_type=chunk_type,
                        page_number=page_num,
                        section_title=section,
                        token_count=len(text.split()),
                        chunk_metadata={'filename': filename, 'format': file_format}
                    ))
            except Exception as e:
                logger.warning(f"HybridChunker failed for {filename}: {e}")

            # --- Pass 2: markdown export fallback ---
            if not chunks:
                logger.info(
                    f"HybridChunker yielded 0 chunks for {filename}, "
                    f"trying markdown fallback"
                )
                try:
                    md = doc.export_to_markdown()
                    if md.strip():
                        raw_chunks = self._fixed_splitter.split_text(md)
                        for i, chunk_text in enumerate(raw_chunks):
                            chunk_text = chunk_text.strip()
                            if chunk_text:
                                chunks.append(ExtractedChunk(
                                    content=chunk_text,
                                    chunk_index=i,
                                    chunk_type='text',
                                    token_count=len(chunk_text.split()),
                                    chunk_metadata={
                                        'filename': filename,
                                        'format': file_format,
                                        'extraction': 'markdown_fallback',
                                    }
                                ))
                        logger.info(
                            f"Markdown fallback: {filename} → {len(chunks)} chunks"
                        )
                except Exception as e:
                    logger.error(f"Markdown fallback failed for {filename}: {e}")

            logger.info(f"Semantic extraction: {filename} → {len(chunks)} chunks")
            return chunks

        finally:
            os.unlink(tmp_path)

    # =========================================================================
    # FIXED EXTRACTION (CSV, XLSX, plain text, code)
    # =========================================================================

    def _extract_fixed(
        self,
        raw_content: bytes,
        file_format: str,
        filename: str,
    ) -> list[ExtractedChunk]:
        """Use RecursiveCharacterTextSplitter for flat/tabular content."""

        text = self._decode_to_text(raw_content, file_format, filename)
        if not text:
            return []

        raw_chunks = self._fixed_splitter.split_text(text)
        chunks = []
        for i, chunk_text in enumerate(raw_chunks):
            chunk_text = chunk_text.strip()
            if not chunk_text:
                continue
            chunks.append(ExtractedChunk(
                content=chunk_text,
                chunk_index=i,
                chunk_type='table' if file_format in ('csv', 'xlsx', 'sheet') else 'text',
                token_count=len(chunk_text.split()),
                chunk_metadata={'filename': filename, 'format': file_format}
            ))

        logger.info(f"Fixed extraction: {filename} → {len(chunks)} chunks")
        return chunks

    def _decode_to_text(self, raw_content: bytes, file_format: str, filename: str) -> str:
        """Convert raw bytes to plain text for flat formats."""
        try:
            if file_format == 'csv':
                return raw_content.decode('utf-8', errors='replace')

            elif file_format in ('xlsx', 'sheet'):
                import openpyxl
                wb = openpyxl.load_workbook(io.BytesIO(raw_content), read_only=True, data_only=True)
                lines = []
                for sheet in wb.worksheets:
                    lines.append(f"## Sheet: {sheet.title}")
                    for row in sheet.iter_rows(values_only=True):
                        row_text = '\t'.join(str(c) if c is not None else '' for c in row)
                        if row_text.strip():
                            lines.append(row_text)
                return '\n'.join(lines)

            else:
                # text, markdown, json, code
                return raw_content.decode('utf-8', errors='replace')

        except Exception as e:
            logger.error(f"Decode failed for {filename}: {e}")
            return ''

    # =========================================================================
    # HELPERS
    # =========================================================================

    def _detect_format(self, mime_type: str, filename: str) -> Optional[str]:
        """Detect file format from MIME type, fallback to extension."""

        # Check excluded types first
        for prefix in EXCLUDED_PREFIXES:
            if mime_type.startswith(prefix):
                return None

        # Check excluded extensions
        ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
        if ext in EXCLUDED_EXTENSIONS:
            logger.info(f"Excluded extension: {filename}")
            return None

        # Check supported types
        if mime_type in SUPPORTED_MIME_TYPES:
            return SUPPORTED_MIME_TYPES[mime_type]

        # Fallback to file extension
        ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
        ext_map = {
            'pdf': 'pdf', 'docx': 'docx', 'doc': 'docx',
            'pptx': 'pptx', 'ppt': 'pptx',
            'xlsx': 'xlsx', 'xls': 'xlsx',
            'csv': 'csv', 'txt': 'text',
            'md': 'text', 'html': 'html',
            'py': 'text', 'js': 'text', 'ts': 'text',
            'json': 'text', 'yaml': 'text', 'yml': 'text',
        }
        return ext_map.get(ext)
