"""
Service de gestion des vector stores
"""
import hashlib
import logging
import os
from typing import Dict, List, Optional
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document
from config.models import OPENAI_API_KEY

logger = logging.getLogger(__name__)

# Directory where per-document FAISS indices are persisted
FAISS_INDEX_DIR = os.getenv(
    "FAISS_INDEX_DIR",
    os.path.join(os.path.dirname(__file__), "..", "faiss_indices"),
)

# Variable globale pour stocker les vector stores par session
vector_stores: Dict[str, FAISS] = {}

# Initialize embeddings
try:
    embeddings = OpenAIEmbeddings(api_key=OPENAI_API_KEY, model="text-embedding-3-small")
    logger.info("Embeddings: text-embedding-3-small")
except Exception as e:
    embeddings = OpenAIEmbeddings(api_key=OPENAI_API_KEY, model="text-embedding-ada-002")
    logger.info("Embeddings: text-embedding-ada-002 (fallback)")

vector_store = None


def compute_document_hash(raw_bytes: bytes) -> str:
    """Retourne le SHA-256 hex du contenu brut du document."""
    return hashlib.sha256(raw_bytes).hexdigest()


def get_index_path(doc_hash: str) -> str:
    """Retourne le chemin du répertoire FAISS pour un hash de document donné."""
    return os.path.join(FAISS_INDEX_DIR, doc_hash)


def save_faiss_index(vs: FAISS, index_path: str) -> None:
    """Sauvegarde un FAISS index sur disque."""
    try:
        os.makedirs(index_path, exist_ok=True)
        vs.save_local(index_path)
        logger.info("FAISS index saved to %s", index_path)
    except Exception as exc:
        logger.warning("Failed to save FAISS index to %s: %s", index_path, exc)


def load_faiss_index(index_path: str) -> Optional[FAISS]:
    """Charge un FAISS index depuis le disque si disponible."""
    faiss_file = os.path.join(index_path, "index.faiss")
    if os.path.isdir(index_path) and os.path.exists(faiss_file):
        try:
            vs = FAISS.load_local(index_path, embeddings, allow_dangerous_deserialization=True)
            logger.info("FAISS index loaded from %s", index_path)
            return vs
        except Exception as exc:
            logger.warning("Failed to load FAISS index from %s: %s", index_path, exc)
    return None


def get_vector_store(session_id: str = 'default') -> Optional[FAISS]:
    """Récupère le vector store pour une session donnée"""
    return vector_stores.get(session_id)


def create_vector_store(documents: List[Document], session_id: str = 'default') -> FAISS:
    """Crée un nouveau vector store pour une session"""
    vector_store = FAISS.from_documents(documents, embeddings)
    vector_stores[session_id] = vector_store
    return vector_store


def add_documents_to_vector_store(documents: List[Document], session_id: str = 'default'):
    """Ajoute des documents à un vector store existant"""
    if session_id in vector_stores:
        vector_stores[session_id].add_documents(documents)
    else:
        create_vector_store(documents, session_id)


