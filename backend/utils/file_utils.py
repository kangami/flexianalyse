"""
Utilitaires pour l'extraction de texte depuis différents formats de fichiers
"""
from docx import Document as DocxDocument
import PyPDF2
from io import BytesIO
import logging

logger = logging.getLogger(__name__)


def extract_text_from_docx(file):
    """Extrait le texte d'un fichier DOCX"""
    try:
        doc = DocxDocument(BytesIO(file.read()))
        return "\n".join([paragraph.text for paragraph in doc.paragraphs])
    except Exception as e:
        logger.error(f"Error extracting text from DOCX: {e}")
        return f"Error: Could not extract text from DOCX file. {str(e)}"


def extract_text_from_pdf(file):
    """Extrait le texte d'un fichier PDF"""
    try:
        pdf_reader = PyPDF2.PdfReader(BytesIO(file.read()))
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text() + "\n"
        return text
    except Exception as e:
        logger.error(f"Error extracting text from PDF: {e}")
        return f"Error: Could not extract text from PDF file. {str(e)}"


