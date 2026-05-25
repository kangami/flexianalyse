"""
Service de recherche en ligne et re-ranking de documents
"""
import os
import json
import re
import requests
import logging
from typing import List
from langchain_core.documents import Document
from config.models import DEFAULT_MODEL
from services.api_clients import call_openai_api

logger = logging.getLogger(__name__)


def perform_online_search(query: str, language: str = 'en') -> str:
    """Wrapper pour la recherche en ligne"""
    return search_serpapi(query, language)


def search_serpapi(query: str, language: str = 'en') -> str:
    """
    SerpAPI - 100 recherches gratuites/mois
    Inscription: https://serpapi.com/
    """
    api_key = os.getenv("SERPAPI_KEY")
    if not api_key:
        return "Clé API manquante"
    
    try:
        url = "https://serpapi.com/search"
        params = {
            'api_key': api_key,
            'engine': 'google',
            'q': query,
            'hl': language,
            'num': 5,
            'no_cache': 'true'
        }
        
        response = requests.get(url, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()
        
        results = []
        
        # Réponse directe (featured snippet)
        if data.get('answer_box'):
            answer = data['answer_box']
            if answer.get('answer'):
                results.append(f"**Réponse directe**: {answer['answer']}")
            if answer.get('snippet'):
                results.append(f"**Information**: {answer['snippet']}")
        
        # Résultats organiques
        if data.get('organic_results'):
            for result in data['organic_results'][:5]:
                title = result.get('title', '')
                snippet = result.get('snippet', '')
                link = result.get('link', '')
                
                if title and snippet:
                    results.append(f"**{title}**\n{snippet}\nSource: {link}")
        
        return "\n\n".join(results) if results else "Aucun résultat trouvé."
        
    except Exception as e:
        raise Exception(f"Erreur SerpAPI: {str(e)}")


async def rerank_documents_with_llm(query: str, documents: List[Document], model: str = DEFAULT_MODEL) -> List[Document]:
    """
    Re-rank les documents avec un LLM pour améliorer la pertinence sémantique.
    """
    try:
        if len(documents) <= 5:
            return documents
        
        docs_summary = []
        for i, doc in enumerate(documents):
            file_name = doc.metadata.get("fileName") or doc.metadata.get("file_name") or f"document_{i}"
            content_snippet = doc.page_content[:500]
            docs_summary.append(f"[{i}] Fichier: {file_name}\nContenu: {content_snippet}...")
        
        rerank_prompt = f"""Tu dois classer ces documents par ordre de pertinence pour répondre à cette question: "{query}"

Documents à classer:
{chr(10).join(docs_summary)}

Retourne UNIQUEMENT une liste JSON des indices (nombres entre crochets) dans l'ordre de pertinence décroissante.
Format: [3, 1, 5, 2, 0, 4, ...]

Réponds UNIQUEMENT avec le JSON, sans explication."""
        
        rerank_response = call_openai_api(rerank_prompt, model)
        
        json_match = re.search(r'\[.*?\]', rerank_response)
        if json_match:
            ranked_indices = json.loads(json_match.group())
            valid_indices = [idx for idx in ranked_indices if 0 <= idx < len(documents)]
            if len(valid_indices) == len(documents):
                reranked = [documents[idx] for idx in valid_indices]
                logger.info(f"✅ Re-ranking réussi: {len(reranked)} documents reclassés")
                return reranked
        
        logger.warning("Re-ranking JSON invalide, utilisation de l'ordre original")
        return documents
        
    except Exception as e:
        logger.warning(f"Erreur lors du re-ranking: {str(e)}, utilisation de l'ordre original")
        return documents


