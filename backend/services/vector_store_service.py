"""
Service de gestion des vector stores
"""
import logging
from typing import Dict, List, Optional
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document
from config.models import OPENAI_API_KEY

logger = logging.getLogger(__name__)

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


