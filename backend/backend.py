import os
import json
import requests
from flask import Flask, request, jsonify, Response, stream_with_context
from flask.helpers import make_response
from flask_cors import CORS
from dotenv import load_dotenv
from docx import Document as DocxDocument
import PyPDF2
from io import BytesIO
from openai import OpenAI
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document
from typing import Dict, List, Optional, Any
import aiocache
import asyncio
import logging
import time
import re
from datetime import datetime
from auth import register_auth_routes, init_database
from config import AuthConfig, FlaskConfig

# Load environment variables
load_dotenv()

# Debug: Vérifier le chargement des variables d'environnement
print(f"GOOGLE_CLIENT_ID chargé: {os.getenv('GOOGLE_CLIENT_ID')[:20] + '...' if os.getenv('GOOGLE_CLIENT_ID') else 'NON CHARGÉ'}")
print(f"OPENAI_API_KEY chargé: {'✅' if os.getenv('OPENAI_API_KEY') else '❌'}")

# Variable globale pour stocker les vector stores par session
vector_stores = {}

# Logger setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Enhanced model configuration
MODEL_CONFIG = {
    "gpt-3.5-turbo": {
        "name": "GPT-3.5 Turbo",
        "provider": "OpenAI",
        "model_id": "gpt-3.5-turbo",
        "max_tokens": 500,
        "description": "Fast and efficient for most tasks",
        "cost_tier": "low",
        "api_type": "chat"
    },
    "gpt-4o": {
        "name": "GPT-4o",
        "provider": "OpenAI", 
        "model_id": "gpt-4o",
        "max_tokens": 500,
        "description": "Advanced reasoning and analysis",
        "cost_tier": "high",
        "api_type": "chat"
    },
    "gpt-5": {
        "name": "GPT-5",
        "provider": "OpenAI",
        "model_id": "gpt-5",
        "max_tokens": 500,
        "description": "Complex reasoning, broad world knowledge, and code-heavy tasks",
        "cost_tier": "premium",
        "api_type": "responses",
        "reasoning_effort": "medium",  # minimal, low, medium, high
        "verbosity": "medium"  # low, medium, high
    },
    "gpt-5-mini": {
        "name": "GPT-5 Mini",
        "provider": "OpenAI",
        "model_id": "gpt-5-mini",
        "max_tokens": 500,
        "description": "Cost-optimized reasoning and chat; balances speed, cost, and capability",
        "cost_tier": "medium",
        "api_type": "responses",
        "reasoning_effort": "low",
        "verbosity": "low"
    },
    "gpt-5-nano": {
        "name": "GPT-5 Nano",
        "provider": "OpenAI",
        "model_id": "gpt-5-nano",
        "max_tokens": 500,
        "description": "High-throughput tasks, simple instruction-following or classification",
        "cost_tier": "low",
        "api_type": "responses",
        "reasoning_effort": "minimal",
        "verbosity": "low"
    },
    "mistral": {
        "name": "Mistral Medium",
        "provider": "Mistral AI",
        "model_id": "mistral-medium-latest",
        "max_tokens": 500,
        "description": "Efficient multilingual model",
        "cost_tier": "medium",
        "api_type": "chat"
    },
    "llama3": {
        "name": "Llama 3.2",
        "provider": "Local",
        "model_id": "llama3.2",
        "max_tokens": 500,
        "description": "Open-source local model",
        "cost_tier": "free",
        "api_type": "ollama"
    },
    # Keep compatibility with your existing naming
    "openai": {
        "name": "OpenAI GPT",
        "provider": "OpenAI",
        "model_id": "gpt-4o",
        "max_tokens": 500,
        "description": "Legacy OpenAI model",
        "cost_tier": "medium",
        "api_type": "chat"
    }
}

# Config constants
OLLAMA_API_URL = "http://localhost:11434/api/generate"
OLLAMA_MODELS = ["llama3.2", "llama3"]
DEFAULT_MODEL = "mistral"  # Set Mistral as default (switched from GPT-3.5-Turbo due to API credit limit)
MISTRAL_MODEL = "mistral-medium-latest"
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")

if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY environment variable not set")

# Flask setup
app = Flask(__name__)
CORS(app, resources={r"/*": {
    "origins": ["http://flexianalyse.com", "http://localhost:5173", "https://flexianalyse.com"],
    "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    "allow_headers": ["Content-Type", "Authorization", "Session-ID"]
}})

# Ajouter un handler pour les requêtes OPTIONS (CORS preflight)
@app.before_request
def handle_preflight():
    if request.method == "OPTIONS":
        response = make_response()
        response.headers.add("Access-Control-Allow-Origin", "*")
        response.headers.add('Access-Control-Allow-Headers', "Content-Type,Authorization,Session-ID")
        response.headers.add('Access-Control-Allow-Methods', "GET,PUT,POST,DELETE,OPTIONS")
        return response

# Initialize clients and components
openai_client = OpenAI(api_key=OPENAI_API_KEY)
# Utiliser le modèle d'embedding le plus récent disponible
try:
    embeddings = OpenAIEmbeddings(api_key=OPENAI_API_KEY, model="text-embedding-3-small")
    logger.info("Embeddings: text-embedding-3-small (meilleure qualité sémantique)")
except Exception as e:
    embeddings = OpenAIEmbeddings(api_key=OPENAI_API_KEY, model="text-embedding-ada-002")
    logger.info("Embeddings: text-embedding-ada-002 (fallback)")
vector_store = None

# Cache setup
cache = aiocache.SimpleMemoryCache()

# Description file path
DESCRIPTIONS_FILE = os.path.join(os.path.dirname(__file__), "file_descriptions.json")
if not os.path.exists(DESCRIPTIONS_FILE):
    with open(DESCRIPTIONS_FILE, 'w') as f:
        json.dump([], f)

translations = {
    'en': {
        # Existing keys
        'analyze': 'Analyze',
        'content_of_file': "the content of the file",
        'and_provide': "and provide a description of its purpose.",
        'content': "Content",
        'description': "Description",
        'template': "I want an answer like: The file text.js aims to .....",
        'project_structure': 'Project structure',
        'file': 'File',
        'other_file': 'Other file',
        'question': 'Question',
        'emoji': 'Add some relevant emojis when it necessary to make it pleasant to read 😊📄✨',
        
        # New keys for local query mode
        'local_analysis_mode': '🔒 LOCAL ANALYSIS MODE - Analyze ONLY the context provided below.',
        'no_external_search': 'Do NOT perform external searches or reference information not provided.',
        'main_file': 'Main file',
        'file_content': 'File content',
        'directory_context': 'Directory context',
        'no_other_files': 'No other files in context.',
        'instructions': 'Instructions',
        'base_response_only': '- Base your response ONLY on the code/content provided above',
        'missing_info_clarify': '- If information is not in the provided context, state it clearly',
        'no_speculation': '- Do not speculate on elements not present in the files',
        'focus_local_analysis': '- Focus on analyzing the local code/content',
        'error_local_analysis': 'Error during local analysis',
        'cached_result': 'Using cached result',
        'analyzing': 'Analyzing',
        'with_context': 'with context',
        'files_in_directory': 'files in directory',
        
        # Query analysis keys
        'analyze_query_prompt': 'Analyze this question and determine if it requires recent/current information that your model might not have in its training data.',
        'query_label': 'Question',
        'json_response_format': 'Respond in JSON format ONLY',
        'needs_search_field': 'needs_search',
        'reason_field': 'reason',
        'search_keywords_field': 'search_keywords',
        'cutoff_relevance_field': 'estimated_cutoff_relevance',
        'short_explanation': 'short explanation',
        'keyword_or_null': 'or null',
        'examples_need_search': 'Examples of questions requiring search',
        'current_prices_stocks': '- Current prices, recent stock prices',
        'recent_events_news': '- Recent events, news',
        'new_software_versions': '- New software/technology versions',
        'recent_statistics_data': '- Recent statistics, government data',
        'recent_people_companies': '- Information about recent people/companies',
        'examples_no_search': 'Examples of questions NOT requiring search',
        'general_concepts': '- General concepts, established theories',
        'programming_syntax': '- Programming, language syntax',
        'history_facts': '- History, historical facts',
        'math_science': '- Mathematics, fundamental sciences',
        'analysis_error': 'Analysis error',
        'query_analysis_error': 'Error during query analysis',
        'automatic_analysis_failed': 'Automatic analysis inconclusive',
        'error_analysis_fallback': 'Analysis error, searching for safety',
        'analyzing_query': 'Analyzing query',
        'search_needed': 'Search needed',
        'no_search_needed': 'No search needed',
        'json_parse_failed': 'Failed to parse JSON response',
        'fallback_analysis': 'Using fallback analysis',

        # NEW KEYS FOR ONLINE MODE
        'online_mode_title': '🤖 Answer this question using your training knowledge.',
        'recent_info_mention': 'If you think more recent information could enrich your response, mention it at the end.',
        'online_instructions_title': 'Instructions:',
        'give_best_answer': '- Give your best answer based on your knowledge',
        'be_precise_dates': '- Be precise about dates/versions you know',
        'mention_recent_useful': '- Mention if more recent info would be useful',
        'enrichment_title': '🔄 RESPONSE ENRICHMENT',
        'initial_response': 'Your initial response:',
        'new_info_found': 'New information found:',
        'enrichment_instructions': 'Instructions:',
        'combine_intelligently': '- Intelligently combine your initial response with new info',
        'update_obsolete': '- Update obsolete parts if necessary',
        'distinguish_info': '- Clearly distinguish basic info from recent info',
        'cite_sources': '- Cite sources for recent information',
        'keep_structure': '- Keep the structure and style of your initial response',
        'prioritize_recent': '- If new info contradicts your knowledge, prioritize recent sources',
        'enriched_response': 'Enriched response:',
        'info_enriched': '💡 **Information enriched**: This response combines my basic knowledge with recent data found online.',
        'search_reason': '🔍 **Search reason**: {reason}',
        'default_search_reason': 'Potentially outdated information',
        'source_training': '🧠 **Source**: Response based on my training knowledge. No recent search was deemed necessary.',
        'online_processing_error': 'Error during online mode processing: {error}',
        'search_analysis_log': '🔍 Search analysis: {analysis}',
        'enriching_current_data': '🌐 Enriching with current data...',
        'no_search_necessary': '✅ No search necessary, response based on model knowledge',
        'error_online_mode': 'Error during online mode: {error}',
        'separator': '---'
    },
    'fr': {
        # Existing keys
        'analyze': 'Analysez',
        'content_of_file': "le contenu du fichier",
        'and_provide': "et fournissez une description de son objectif.",
        'content': "Contenu",
        'description': "Description",
        'template': "Je veux une réponse du genre: Le Fichier text.js a pour Objectif : .....",
        'project_structure': 'Structure du projet',
        'file': 'Fichier',
        'other_file': 'Autre fichier',
        'question': 'Question',
        'emoji': 'Ajoute quelques emojis pertinents quand c\'est nécessaire pour rendre la lecture agréable 😊📄✨',
        
        # New keys for local query mode
        'local_analysis_mode': '🔒 MODE ANALYSE LOCALE - Analysez UNIQUEMENT le contexte fourni ci-dessous.',
        'no_external_search': 'Ne faites PAS de recherche externe ou de référence à des informations non fournies.',
        'main_file': 'Fichier principal',
        'file_content': 'Contenu du fichier',
        'directory_context': 'Contexte du répertoire',
        'no_other_files': 'Aucun autre fichier dans le contexte.',
        'instructions': 'Instructions',
        'base_response_only': '- Basez votre réponse UNIQUEMENT sur le code/contenu fourni ci-dessus',
        'missing_info_clarify': '- Si l\'information n\'est pas dans le contexte fourni, dites-le clairement',
        'no_speculation': '- Ne spéculez pas sur des éléments non présents dans les fichiers',
        'focus_local_analysis': '- Concentrez-vous sur l\'analyse du code/contenu local',
        'error_local_analysis': 'Erreur lors de l\'analyse locale',
        'cached_result': 'Utilisation du résultat en cache',
        'analyzing': 'Analyse de',
        'with_context': 'avec contexte de',
        'files_in_directory': 'fichiers dans le répertoire',
        
        # Query analysis keys
        'analyze_query_prompt': 'Analysez cette question et déterminez si elle nécessite des informations récentes/actuelles que votre modèle pourrait ne pas avoir dans ses données d\'entraînement.',
        'query_label': 'Question',
        'json_response_format': 'Répondez au format JSON UNIQUEMENT',
        'needs_search_field': 'needs_search',
        'reason_field': 'reason',
        'search_keywords_field': 'search_keywords',
        'cutoff_relevance_field': 'estimated_cutoff_relevance',
        'short_explanation': 'explication courte',
        'keyword_or_null': 'ou null',
        'examples_need_search': 'Exemples de questions nécessitant une recherche',
        'current_prices_stocks': '- Prix actuels, cours de bourse récents',
        'recent_events_news': '- Événements récents, actualités',
        'new_software_versions': '- Nouvelles versions de logiciels/technologies',
        'recent_statistics_data': '- Statistiques récentes, données gouvernementales',
        'recent_people_companies': '- Informations sur des personnes/entreprises récentes',
        'examples_no_search': 'Exemples de questions NE nécessitant PAS de recherche',
        'general_concepts': '- Concepts généraux, théories établies',
        'programming_syntax': '- Programmation, syntaxe de langages',
        'history_facts': '- Histoire, faits historiques',
        'math_science': '- Mathématiques, sciences fondamentales',
        'analysis_error': 'Erreur d\'analyse',
        'query_analysis_error': 'Erreur lors de l\'analyse de la requête',
        'automatic_analysis_failed': 'Analyse automatique non concluante',
        'error_analysis_fallback': 'Erreur d\'analyse, recherche par sécurité',
        'analyzing_query': 'Analyse de la requête',
        'search_needed': 'Recherche nécessaire',
        'no_search_needed': 'Aucune recherche nécessaire',
        'json_parse_failed': 'Échec du parsing JSON',
        'fallback_analysis': 'Utilisation de l\'analyse de secours',

        # NEW KEYS FOR ONLINE MODE
        'online_mode_title': '🤖 Répondez à cette question en utilisant vos connaissances d\'entraînement.',
        'recent_info_mention': 'Si vous pensez que des informations plus récentes pourraient enrichir votre réponse, mentionnez-le à la fin.',
        'online_instructions_title': 'Instructions :',
        'give_best_answer': '- Donnez votre meilleure réponse basée sur vos connaissances',
        'be_precise_dates': '- Soyez précis sur les dates/versions que vous connaissez',
        'mention_recent_useful': '- Mentionnez si des infos plus récentes seraient utiles',
        'enrichment_title': '🔄 ENRICHISSEMENT DE RÉPONSE',
        'initial_response': 'Votre réponse initiale :',
        'new_info_found': 'Nouvelles informations trouvées :',
        'enrichment_instructions': 'Instructions :',
        'combine_intelligently': '- Combinez intelligemment votre réponse initiale avec les nouvelles infos',
        'update_obsolete': '- Mettez à jour les parties obsolètes si nécessaire',
        'distinguish_info': '- Distinguez clairement les infos de base des infos récentes',
        'cite_sources': '- Citez les sources pour les informations récentes',
        'keep_structure': '- Gardez la structure et le style de votre réponse initiale',
        'prioritize_recent': '- Si les nouvelles infos contredisent vos connaissances, privilégiez les sources récentes',
        'enriched_response': 'Réponse enrichie :',
        'info_enriched': '💡 **Informations enrichies** : Cette réponse combine mes connaissances de base avec des données récentes trouvées en ligne.',
        'search_reason': '🔍 **Raison de la recherche** : {reason}',
        'default_search_reason': 'Information potentiellement obsolète',
        'source_training': '🧠 **Source** : Réponse basée sur mes connaissances d\'entraînement. Aucune recherche récente n\'a été jugée nécessaire.',
        'online_processing_error': 'Erreur lors du traitement en mode online : {error}',
        'search_analysis_log': '🔍 Analyse de recherche : {analysis}',
        'enriching_current_data': '🌐 Enrichissement avec des données actuelles...',
        'no_search_necessary': '✅ Pas de recherche nécessaire, réponse basée sur les connaissances du modèle',
        'error_online_mode': 'Erreur lors du mode online : {error}',
        'separator': '---'
    },
    'es': {
        # Existing keys
        'analyze': 'Analiza',
        'content_of_file': "el contenido del archivo",
        'and_provide': "y proporciona una descripción de su propósito.",
        'content': "Contenido",
        'description': "Descripción",
        'template': "Quiero una respuesta como: El archivo text.js tiene como objetivo .....",
        'project_structure': 'Estructura del proyecto',
        'file': 'Archivo',
        'other_file': 'Otro archivo',
        'question': 'Pregunta',
        'emoji': 'Agrega algunos emojis relevantes cuando sea necesario para que sea agradable de leer 😊📄✨',
        
        # New keys for local query mode
        'local_analysis_mode': '🔒 MODO ANÁLISIS LOCAL - Analiza ÚNICAMENTE el contexto proporcionado a continuación.',
        'no_external_search': 'NO realices búsquedas externas o referencias a información no proporcionada.',
        'main_file': 'Archivo principal',
        'file_content': 'Contenido del archivo',
        'directory_context': 'Contexto del directorio',
        'no_other_files': 'Ningún otro archivo en el contexto.',
        'instructions': 'Instrucciones',
        'base_response_only': '- Basa tu respuesta ÚNICAMENTE en el código/contenido proporcionado arriba',
        'missing_info_clarify': '- Si la información no está en el contexto proporcionado, indícalo claramente',
        'no_speculation': '- No especules sobre elementos no presentes en los archivos',
        'focus_local_analysis': '- Concéntrate en analizar el código/contenido local',
        'error_local_analysis': 'Error durante el análisis local',
        'cached_result': 'Usando resultado en caché',
        'analyzing': 'Analizando',
        'with_context': 'con contexto de',
        'files_in_directory': 'archivos en el directorio',
        
        # Query analysis keys
        'analyze_query_prompt': 'Analiza esta pregunta y determina si requiere información reciente/actual que tu modelo podría no tener en sus datos de entrenamiento.',
        'query_label': 'Pregunta',
        'json_response_format': 'Responde en formato JSON ÚNICAMENTE',
        'needs_search_field': 'needs_search',
        'reason_field': 'reason',
        'search_keywords_field': 'search_keywords',
        'cutoff_relevance_field': 'estimated_cutoff_relevance',
        'short_explanation': 'explicación corta',
        'keyword_or_null': 'o null',
        'examples_need_search': 'Ejemplos de preguntas que requieren búsqueda',
        'current_prices_stocks': '- Precios actuales, precios de acciones recientes',
        'recent_events_news': '- Eventos recientes, noticias',
        'new_software_versions': '- Nuevas versiones de software/tecnologías',
        'recent_statistics_data': '- Estadísticas recientes, datos gubernamentales',
        'recent_people_companies': '- Información sobre personas/empresas recientes',
        'examples_no_search': 'Ejemplos de preguntas que NO requieren búsqueda',
        'general_concepts': '- Conceptos generales, teorías establecidas',
        'programming_syntax': '- Programación, sintaxis de lenguajes',
        'history_facts': '- Historia, hechos históricos',
        'math_science': '- Matemáticas, ciencias fundamentales',
        'analysis_error': 'Error de análisis',
        'query_analysis_error': 'Error durante el análisis de la consulta',
        'automatic_analysis_failed': 'Análisis automático no concluyente',
        'error_analysis_fallback': 'Error de análisis, búsqueda por seguridad',
        'analyzing_query': 'Analizando consulta',
        'search_needed': 'Búsqueda necesaria',
        'no_search_needed': 'No se necesita búsqueda',
        'json_parse_failed': 'Error al analizar respuesta JSON',
        'fallback_analysis': 'Usando análisis de respaldo',

        # NEW KEYS FOR ONLINE MODE
        'online_mode_title': '🤖 Responde esta pregunta usando tus conocimientos de entrenamiento.',
        'recent_info_mention': 'Si crees que información más reciente podría enriquecer tu respuesta, menciónalo al final.',
        'online_instructions_title': 'Instrucciones:',
        'give_best_answer': '- Da tu mejor respuesta basada en tus conocimientos',
        'be_precise_dates': '- Sé preciso sobre fechas/versiones que conoces',
        'mention_recent_useful': '- Menciona si información más reciente sería útil',
        'enrichment_title': '🔄 ENRIQUECIMIENTO DE RESPUESTA',
        'initial_response': 'Tu respuesta inicial:',
        'new_info_found': 'Nueva información encontrada:',
        'enrichment_instructions': 'Instrucciones:',
        'combine_intelligently': '- Combina inteligentemente tu respuesta inicial con la nueva info',
        'update_obsolete': '- Actualiza las partes obsoletas si es necesario',
        'distinguish_info': '- Distingue claramente la info básica de la info reciente',
        'cite_sources': '- Cita fuentes para la información reciente',
        'keep_structure': '- Mantén la estructura y estilo de tu respuesta inicial',
        'prioritize_recent': '- Si la nueva info contradice tus conocimientos, prioriza fuentes recientes',
        'enriched_response': 'Respuesta enriquecida:',
        'info_enriched': '💡 **Información enriquecida**: Esta respuesta combina mis conocimientos básicos con datos recientes encontrados en línea.',
        'search_reason': '🔍 **Razón de búsqueda**: {reason}',
        'default_search_reason': 'Información potencialmente obsoleta',
        'source_training': '🧠 **Fuente**: Respuesta basada en mis conocimientos de entrenamiento. No se consideró necesaria una búsqueda reciente.',
        'online_processing_error': 'Error durante el procesamiento en modo online: {error}',
        'search_analysis_log': '🔍 Análisis de búsqueda: {analysis}',
        'enriching_current_data': '🌐 Enriqueciendo con datos actuales...',
        'no_search_necessary': '✅ No es necesaria búsqueda, respuesta basada en conocimientos del modelo',
        'error_online_mode': 'Error durante modo online: {error}',
        'separator': '---'
    }
}

# Description template
description_template = "Je veux une reponse du genre: Le Fichier text.js a pour Objectif : ....."

# Utility functions
def extract_text_from_docx(file):
    try:
        doc = DocxDocument(BytesIO(file.read()))
        text = [para.text for para in doc.paragraphs if para.text.strip()]
        return '\n'.join(text)
    except Exception as e:
        return f"Error extracting text from .docx: {str(e)}"

def extract_text_from_pdf(file):
    try:
        pdf_reader = PyPDF2.PdfReader(BytesIO(file.read()))
        text = [page.extract_text() for page in pdf_reader.pages if page.extract_text()]
        return '\n'.join(text)
    except Exception as e:
        return f"Error extracting text from .pdf: {str(e)}"

def get_model_config(selected_model):
    """Get model configuration, fallback to default if not found"""
    return MODEL_CONFIG.get(selected_model, MODEL_CONFIG[DEFAULT_MODEL])

def call_openai_api(prompt, selected_model="gpt-3.5-turbo", max_retries=3, max_tokens_override=None):
    """
    Enhanced OpenAI API call supporting both Chat Completions and Responses API
    max_tokens_override: override la limite de tokens de la config du modèle
    """
    model_config = get_model_config(selected_model)
    model_id = model_config["model_id"]
    api_type = model_config.get("api_type", "chat")
    
    for attempt in range(max_retries):
        try:
            logger.info(f"[OpenAI] Using model: {model_id} with API: {api_type}")
            
            # GPT-5 variants use the new Responses API
            if api_type == "responses":
                request_params = {
                    "model": model_id,
                    "input": prompt
                }
                
                # Add reasoning parameters for GPT-5
                if "reasoning_effort" in model_config:
                    request_params["reasoning"] = {
                        "effort": model_config["reasoning_effort"]
                    }
                
                # Add verbosity parameters for GPT-5
                if "verbosity" in model_config:
                    request_params["text"] = {
                        "verbosity": model_config["verbosity"]
                    }
                
                logger.info(f"[OpenAI] GPT-5 request params: reasoning={model_config.get('reasoning_effort')}, verbosity={model_config.get('verbosity')}")
                response = openai_client.responses.create(**request_params)
                
                # Extract text from responses API - Updated extraction logic
                try:
                    # The actual content is in output array, look for message type with content
                    if hasattr(response, 'output') and response.output:
                        for item in response.output:
                            # Look for message type items
                            if hasattr(item, 'type') and item.type == 'message':
                                if hasattr(item, 'content') and item.content:
                                    for content_item in item.content:
                                        if hasattr(content_item, 'text') and content_item.text:
                                            logger.info(f"[OpenAI] Successfully extracted GPT-5 response")
                                            return content_item.text.strip()
                    
                    # Fallback extraction methods
                    if hasattr(response, 'text') and hasattr(response.text, 'content'):
                        return response.text.content.strip()
                    elif hasattr(response, 'content'):
                        return response.content.strip()
                    else:
                        # Final fallback: try to extract from string representation
                        response_str = str(response)
                        logger.warning(f"[OpenAI] Using fallback extraction for GPT-5 response")
                        
                        # Try to extract text from the string representation
                        import re
                        text_match = re.search(r"text='([^']*)'", response_str)
                        if text_match:
                            extracted_text = text_match.group(1)
                            # Decode escape sequences
                            extracted_text = extracted_text.replace('\\n', '\n').replace("\\'", "'")
                            return extracted_text.strip()
                        
                        return "Error: Could not extract response content from GPT-5"
                        
                except Exception as extraction_error:
                    logger.error(f"[OpenAI] Error extracting GPT-5 response: {extraction_error}")
                    return f"Error extracting response: {str(extraction_error)}"
            
            # Standard models use Chat Completions API
            else:
                # Utiliser max_tokens_override si fourni, sinon la config du modèle
                max_tokens = max_tokens_override if max_tokens_override is not None else model_config.get("max_tokens", 500)
                request_params = {
                    "model": model_id,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.5,
                    "max_tokens": max_tokens
                }
                
                response = openai_client.chat.completions.create(**request_params)
                return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.warning(f"[OpenAI] Attempt {attempt+1}/{max_retries} failed with {model_id}: {str(e)}")
            
            # Smart fallback strategy
            error_str = str(e).lower()
            if any(keyword in error_str for keyword in ["model", "not found", "unsupported", "invalid"]):
                # GPT-5 fallback chain
                if model_id == "gpt-5":
                    logger.info("[OpenAI] GPT-5 not available, falling back to GPT-5-mini")
                    model_id = "gpt-5-mini"
                    model_config = get_model_config("gpt-5-mini")
                    api_type = model_config.get("api_type", "responses")
                    continue
                elif model_id == "gpt-5-mini":
                    logger.info("[OpenAI] GPT-5-mini not available, falling back to GPT-5-nano")
                    model_id = "gpt-5-nano"
                    model_config = get_model_config("gpt-5-nano")
                    api_type = model_config.get("api_type", "responses")
                    continue
                elif model_id == "gpt-5-nano":
                    logger.info("[OpenAI] GPT-5-nano not available, falling back to GPT-4o")
                    model_id = "gpt-4o"
                    model_config = get_model_config("gpt-4o")
                    api_type = model_config.get("api_type", "chat")
                    continue
                elif model_id == "gpt-4o":
                    logger.info("[OpenAI] GPT-4o not available, falling back to GPT-3.5-turbo")
                    model_id = "gpt-3.5-turbo"
                    model_config = get_model_config("gpt-3.5-turbo")
                    api_type = model_config.get("api_type", "chat")
                    continue
            
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt
                logger.warning(f"[OpenAI] Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
                continue
            else:
                logger.error(f"[OpenAI] Max retries exceeded: {str(e)}")
                raise e
    
    raise RuntimeError("[OpenAI] Max retries exceeded")

def stream_response(prompt, selected_model="gpt-3.5-turbo"):
    """
    Génère une réponse en streaming pour n'importe quel modèle
    """
    model_config = get_model_config(selected_model)
    
    try:
        # Pour les modèles OpenAI avec support du streaming
        if selected_model.lower() in ["gpt-3.5-turbo", "gpt-4o", "openai"]:
            model_id = model_config["model_id"]
            
            stream = openai_client.chat.completions.create(
                model=model_id,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.5,
                max_tokens=model_config.get("max_tokens", 500),
                stream=True
            )
            
            for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield f"data: {json.dumps({'content': chunk.choices[0].delta.content})}\n\n"
            
            yield f"data: {json.dumps({'done': True})}\n\n"
            
        # Pour Mistral - pas de streaming natif, on simule
        elif selected_model.lower() == "mistral":
            try:
                # Appel normal à Mistral (sans streaming)
                response = call_mistral_api(prompt)
                
                # Simuler le streaming en envoyant par morceaux
                words = response.split(' ')
                for i in range(0, len(words), 3):  # Envoyer 3 mots à la fois
                    chunk = ' '.join(words[i:i+3])
                    if i + 3 < len(words):
                        chunk += ' '
                    yield f"data: {json.dumps({'content': chunk})}\n\n"
                    time.sleep(0.05)  # Petit délai pour simuler le streaming
                
                yield f"data: {json.dumps({'done': True})}\n\n"
                
            except Exception as mistral_error:
                # Si Mistral échoue, fallback vers GPT-3.5
                logger.warning(f"Mistral failed: {str(mistral_error)}, falling back to GPT-3.5")
                yield f"data: {json.dumps({'warning': 'Mistral indisponible, utilisation de GPT-3.5'})}\n\n"
                
                # Utiliser GPT-3.5 en fallback
                stream = openai_client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.5,
                    max_tokens=500,
                    stream=True
                )
                
                for chunk in stream:
                    if chunk.choices[0].delta.content:
                        yield f"data: {json.dumps({'content': chunk.choices[0].delta.content})}\n\n"
                
                yield f"data: {json.dumps({'done': True})}\n\n"
        
        # Pour Llama/Ollama - pas de streaming natif
        elif selected_model.lower() in ["llama3", "llama3.2"]:
            try:
                response = call_ollama_api(prompt, selected_model)
                
                # Simuler le streaming
                words = response.split(' ')
                for i in range(0, len(words), 3):
                    chunk = ' '.join(words[i:i+3])
                    if i + 3 < len(words):
                        chunk += ' '
                    yield f"data: {json.dumps({'content': chunk})}\n\n"
                    time.sleep(0.05)
                
                yield f"data: {json.dumps({'done': True})}\n\n"
                
            except Exception as ollama_error:
                logger.warning(f"Ollama failed: {str(ollama_error)}, falling back to GPT-3.5")
                yield f"data: {json.dumps({'warning': 'Ollama indisponible, utilisation de GPT-3.5'})}\n\n"
                
                # Fallback vers GPT-3.5
                stream = openai_client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.5,
                    max_tokens=500,
                    stream=True
                )
                
                for chunk in stream:
                    if chunk.choices[0].delta.content:
                        yield f"data: {json.dumps({'content': chunk.choices[0].delta.content})}\n\n"
                
                yield f"data: {json.dumps({'done': True})}\n\n"
        
        else:
            # Modèle inconnu, utiliser GPT-3.5 par défaut
            logger.warning(f"Unknown model {selected_model}, using GPT-3.5")
            yield f"data: {json.dumps({'warning': f'Modèle {selected_model} inconnu, utilisation de GPT-3.5'})}\n\n"
            
            stream = openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.5,
                max_tokens=500,
                stream=True
            )
            
            for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield f"data: {json.dumps({'content': chunk.choices[0].delta.content})}\n\n"
            
            yield f"data: {json.dumps({'done': True})}\n\n"
            
    except Exception as e:
        logger.error(f"Erreur streaming: {str(e)}")
        yield f"data: {json.dumps({'error': str(e)})}\n\n"

def call_mistral_api(prompt, max_retries=3):
    mistral_api_key = os.getenv("MISTRAL_API_KEY")
    if not mistral_api_key:
        raise ValueError("MISTRAL_API_KEY environment variable not set")

    url = "https://api.mistral.ai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {mistral_api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": MISTRAL_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 500,
        "temperature": 0.5
    }

    for attempt in range(max_retries):
        try:
            response = requests.post(url, headers=headers, json=payload)
            if response.status_code == 429:
                retry_after = int(response.headers.get("Retry-After", 1))
                logger.warning(f"[Mistral] Rate limited. Retrying in {retry_after} sec (attempt {attempt+1}/{max_retries})...")
                time.sleep(retry_after)
                continue

            response.raise_for_status()
            result = response.json()
            return result["choices"][0]["message"]["content"].strip()

        except requests.exceptions.HTTPError as e:
            if response.status_code == 429 and attempt < max_retries - 1:
                wait_time = 2 ** attempt
                logger.warning(f"[Mistral] 429 Too Many Requests. Retrying in {wait_time} sec (attempt {attempt+1}/{max_retries})...")
                time.sleep(wait_time)
                continue
            else:
                logger.error(f"[Mistral] HTTP Error: {e}")
                raise e

        except Exception as e:
            logger.error(f"[Mistral] Unexpected Error: {e}")
            raise e

    raise RuntimeError("[Mistral] Max retries exceeded")

def call_ollama_api(prompt, selected_model="llama3", max_retries=3):
    """Enhanced Ollama API call"""
    model_config = get_model_config(selected_model)
    model_id = model_config["model_id"]
    
    for attempt in range(max_retries):
        try:
            response = requests.post(OLLAMA_API_URL, json={
                "model": model_id,
                "prompt": prompt,
                "stream": False
            })
            response.raise_for_status()
            data = response.json()
            return data.get("response") or data.get("message", {}).get("content", "No response").strip()
            
        except Exception as e:
            logger.warning(f"[Ollama] Attempt {attempt+1}/{max_retries} failed: {str(e)}")
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt
                logger.warning(f"[Ollama] Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
                continue
            else:
                logger.error(f"[Ollama] Max retries exceeded: {str(e)}")
                raise e
    
    raise RuntimeError("[Ollama] Max retries exceeded")

async def analyze_file_content(file_content, file_name, is_binary=False, extension='', selected_model=DEFAULT_MODEL, language='en'):
    cache_key = f"desc_{file_name}_{selected_model}_{language}"
    cached = await cache.get(cache_key)
    if cached:
        return cached

    t = translations.get(language, translations['en'])

    prompt = (
        f"{t['analyze']} {t['content_of_file']} '{file_name}' {t['and_provide']}\n\n"
        f"{t['content']}:\n{file_content}\n\n"
        f"{t['description']}: {t['template']}"
    )

    try:
        # Enhanced model routing with GPT-5 variants
        if selected_model.lower() in ["gpt-3.5-turbo", "gpt-4o"]:
            description = call_openai_api(prompt, selected_model)
        elif selected_model.lower() in ["gpt-5", "gpt-5-mini", "gpt-5-nano"]:
            description = call_openai_api(prompt, selected_model)
        elif selected_model.lower() == "openai":
            # Legacy compatibility
            description = call_openai_api(prompt, "openai")
        elif selected_model.lower() == "mistral":
            description = call_mistral_api(prompt)
        elif selected_model.lower() in OLLAMA_MODELS or selected_model.lower() == "llama3":
            description = call_ollama_api(prompt, selected_model)
        else:
            logger.warning(f"Unknown model {selected_model}, falling back to default {DEFAULT_MODEL}")
            description = call_openai_api(prompt, DEFAULT_MODEL)
            
    except Exception as e:
        description = f"Error analyzing file: {str(e)}"

    await cache.set(cache_key, description, ttl=3600)
    return description

async def infer_corpus_actions(documents: List[Document], language: str = 'en') -> Dict[str, Any]:
    """
    Utilise un petit appel modèle pour deviner le type de corpus (CV, rapports annuels, etc.)
    et proposer des actions suggérées (boutons) adaptées.
    """
    try:
        # D'abord, détecter le type de document dominant dans le corpus
        document_types = {}
        for doc in documents[:20]:
            doc_type = await detect_document_type(doc.page_content[:2000], doc.metadata.get('fileName', ''))
            document_types[doc_type] = document_types.get(doc_type, 0) + 1
        
        # Trouver le type de document le plus fréquent
        dominant_type = max(document_types.items(), key=lambda x: x[1])[0] if document_types else 'document_generique'
        
        # Construire un résumé compact du corpus pour le prompt
        sample_texts = []
        for doc in documents[:20]:
            meta_name = doc.metadata.get('fileName') or doc.metadata.get('source') or 'document'
            snippet = doc.page_content[:800].replace('\n', ' ')
            sample_texts.append(f"- {meta_name}: {snippet}")
        corpus_preview = "\n".join(sample_texts)

        # Actions spécifiques selon le type de document
        specific_actions_prompts = {
            'contrat_location': """
Actions spécifiques pour un contrat de location (bail) :
1. "Vérifier les parties" - Identifie et liste toutes les parties (locataire, bailleur) avec leurs coordonnées complètes
2. "Vérifier les dates" - Extrait toutes les dates importantes : signature, début, fin, durée, préavis
3. "Vérifier les montants" - Liste tous les montants : loyer, caution, charges, indexation
4. "Analyser les clauses à risque" - Identifie les clauses potentiellement problématiques ou désavantageuses
5. "Vérifier les obligations" - Liste les obligations du locataire et du bailleur
6. "Vérifier le bien loué" - Détaille les caractéristiques du bien (adresse, superficie, type)
7. "Extraire données structurées" - Extrait toutes les données dans un format structuré JSON""",

            'contrat_travail': """
Actions spécifiques pour un contrat de travail :
1. "Vérifier les parties" - Identifie l'employeur et l'employé avec leurs coordonnées
2. "Vérifier les dates" - Extrait les dates : signature, début, période d'essai, fin
3. "Vérifier la rémunération" - Détaille le salaire, primes, avantages, révisions
4. "Vérifier les obligations" - Liste les obligations de l'employé et de l'employeur
5. "Analyser les clauses à risque" - Identifie les clauses restrictives ou problématiques
6. "Vérifier les conditions" - Détaille les conditions de travail, horaires, lieu
7. "Extraire données structurées" - Extrait toutes les données dans un format structuré JSON""",

            'contrat_vente': """
Actions spécifiques pour un contrat de vente :
1. "Vérifier les parties" - Identifie l'acheteur et le vendeur avec leurs coordonnées
2. "Vérifier les dates" - Extrait les dates : signature, livraison, paiement
3. "Vérifier les montants" - Détaille le prix, acompte, modalités de paiement
4. "Vérifier l'objet" - Décrit précisément l'objet de la vente
5. "Analyser les garanties" - Liste les garanties et conditions de garantie
6. "Vérifier les conditions" - Détaille les conditions de vente, délais, pénalités
7. "Extraire données structurées" - Extrait toutes les données dans un format structuré JSON""",

            'contrat_generique': """
Actions spécifiques pour un contrat :
1. "Vérifier les parties" - Identifie toutes les parties avec leurs coordonnées
2. "Vérifier les dates importantes" - Extrait toutes les dates clés du contrat
3. "Vérifier les montants" - Liste tous les montants et modalités financières
4. "Analyser les clauses à risque" - Identifie les clauses potentiellement problématiques
5. "Vérifier les obligations" - Liste les obligations de chaque partie
6. "Vérifier l'objet" - Décrit précisément l'objet du contrat
7. "Extraire données structurées" - Extrait toutes les données dans un format structuré JSON""",

            'testament': """
Actions spécifiques pour un testament :
1. "Vérifier le testateur" - Identifie le testateur et ses coordonnées
2. "Vérifier les bénéficiaires" - Liste tous les bénéficiaires et leurs parts
3. "Vérifier les dates" - Extrait les dates : rédaction, signature, modifications
4. "Vérifier les legs" - Détaille tous les legs et héritages
5. "Vérifier les conditions" - Liste les conditions et clauses particulières
6. "Vérifier l'exécuteur" - Identifie l'exécuteur testamentaire
7. "Extraire données structurées" - Extrait toutes les données dans un format structuré JSON""",

            'acte_notarie': """
Actions spécifiques pour un acte notarié :
1. "Vérifier les parties" - Identifie toutes les parties impliquées
2. "Vérifier les dates" - Extrait toutes les dates importantes
3. "Vérifier les montants" - Liste tous les montants et transactions
4. "Vérifier l'objet" - Décrit précisément l'objet de l'acte
5. "Vérifier le notaire" - Identifie le notaire et son étude
6. "Vérifier les conditions" - Détaille les conditions et clauses
7. "Extraire données structurées" - Extrait toutes les données dans un format structuré JSON""",

            'lettre': """
Actions spécifiques pour une lettre :
1. "Vérifier l'expéditeur" - Identifie l'expéditeur avec ses coordonnées
2. "Vérifier le destinataire" - Identifie le destinataire avec ses coordonnées
3. "Vérifier la date" - Extrait la date de la lettre
4. "Vérifier l'objet" - Décrit l'objet et le but de la lettre
5. "Vérifier infos clés" - Extrait les informations importantes (montants, références, engagements)
6. "Extraire données structurées" - Extrait toutes les données dans un format structuré JSON""",

            'document_financier': """
Actions spécifiques pour un document financier :
1. "Vérifier les parties" - Identifie les parties concernées (employeur, employé, institution)
2. "Vérifier la période" - Extrait la période couverte par le document
3. "Vérifier les montants" - Liste tous les montants (revenus, déductions, impôts, totaux)
4. "Vérifier déductions" - Détaille toutes les déductions (impôts, cotisations)
5. "Extraire données structurées" - Extrait toutes les données dans un format structuré JSON"""
        }

        base_prompt_fr = f"""
Tu reçois un aperçu de plusieurs documents importés par un utilisateur.
Le type de document dominant détecté est : {dominant_type}

{specific_actions_prompts.get(dominant_type, '')}

À partir de ces textes UNIQUEMENT, propose jusqu'à 7 actions suggérées au format JSON (elles seront affichées comme des boutons dans l'interface).
Les actions doivent être PRATIQUES et correspondre à ce que les utilisateurs vérifient habituellement pour ce type de document.

Retourne du JSON STRICT avec exactement cette forme :
{{
  "domain": "etiquette_courte_du_domaine",
  "suggested_actions": [
    {{
      "id": "identifiant_machine",
      "title": "Label court du bouton (max 25 caractères)",
      "description": "Une phrase expliquant ce que fait cette action pour l'utilisateur.",
      "sample_prompt": "Prompt complet en langage naturel que l'app pourra envoyer à l'assistant quand l'utilisateur clique sur ce bouton."
    }}
  ]
}}

IMPORTANT :
- Les titres doivent être courts et clairs (max 25 caractères)
- Les actions doivent être spécifiques au type de document détecté
- Priorise les actions que les utilisateurs vérifient habituellement (parties, dates, montants, clauses, obligations)
- Inclus toujours "Extraire données structurées" comme dernière action
"""

        base_prompt_en = f"""
You receive a small preview of many documents uploaded by a user.
The dominant document type detected is: {dominant_type}

Based ONLY on these texts, you must propose up to 7 suggested actions as JSON.
Each action will appear as a button in a UI.

Return STRICT valid JSON with this exact shape:
{{
  "domain": "short_domain_label",
  "suggested_actions": [
    {{
      "id": "machine_readable_id",
      "title": "Short button label (max 25 chars)",
      "description": "One sentence explaining what this action does for the user.",
      "sample_prompt": "A full natural language prompt the app can send to the assistant when the user clicks this action."
    }}
  ]
}}

IMPORTANT:
- Titles must be short and clear (max 25 characters)
- Actions must be specific to the detected document type
- Prioritize actions that users typically check (parties, dates, amounts, clauses, obligations)
- Always include "Extract structured data" as the last action
"""

        prompt = (base_prompt_fr if language == 'fr' else base_prompt_en) + "\n\nCORPUS PREVIEW:\n" + corpus_preview

        # Use Mistral instead of OpenAI for suggested actions generation
        raw_response = call_mistral_api(prompt)

        # Essayer d'extraire un JSON valide
        json_match = re.search(r'\{.*\}', raw_response, re.DOTALL)
        if json_match:
            actions = json.loads(json_match.group())
        else:
            actions = json.loads(raw_response)

        # Validation minimale
        if not isinstance(actions, dict) or "suggested_actions" not in actions:
            raise ValueError("Invalid actions format")

        return actions
    except Exception as e:
        logger.warning(f"⚠️  Unable to infer corpus actions: {e}")
        
        # Détecter le type de document pour le fallback
        try:
            # Utiliser le premier document pour détecter le type
            if documents:
                first_doc = documents[0]
                doc_type = await detect_document_type(
                    first_doc.page_content[:2000] if first_doc.page_content else '',
                    first_doc.metadata.get('fileName', '')
                )
            else:
                doc_type = 'document_generique'
        except:
            doc_type = 'document_generique'
        
        # Fallback avec actions spécifiques selon le type de document
        fallback_actions = {
            'contrat_location': [
                {"id": "verify_parties", "title": "Vérifier les parties", "description": "Identifie toutes les parties (locataire, bailleur) avec leurs coordonnées", "sample_prompt": "Identifie toutes les parties de ce contrat de location : le locataire et le bailleur. Liste leurs noms complets, adresses, téléphones et emails si disponibles."},
                {"id": "verify_dates", "title": "Vérifier les dates", "description": "Extrait toutes les dates importantes du contrat", "sample_prompt": "Extrais toutes les dates importantes de ce contrat de location : date de signature, date de début, date de fin, durée, préavis."},
                {"id": "verify_amounts", "title": "Vérifier les montants", "description": "Liste tous les montants : loyer, caution, charges", "sample_prompt": "Liste tous les montants mentionnés dans ce contrat de location : le loyer mensuel, la caution, les charges, et toute indexation prévue."},
                {"id": "analyze_risky_clauses", "title": "Analyser clauses à risque", "description": "Identifie les clauses potentiellement problématiques", "sample_prompt": "Analyse ce contrat de location et identifie les clauses potentiellement problématiques ou désavantageuses pour le locataire ou le bailleur."},
                {"id": "verify_obligations", "title": "Vérifier les obligations", "description": "Liste les obligations du locataire et du bailleur", "sample_prompt": "Liste toutes les obligations du locataire et du bailleur mentionnées dans ce contrat de location."},
                {"id": "extract_structured", "title": "Extraire données structurées", "description": "Extrait toutes les données dans un format structuré", "sample_prompt": "Extrait toutes les données structurées de ce contrat de location : parties, dates, montants, bien loué, clauses importantes."}
            ],
            'contrat_travail': [
                {"id": "verify_parties", "title": "Vérifier les parties", "description": "Identifie l'employeur et l'employé", "sample_prompt": "Identifie les parties de ce contrat de travail : l'employeur et l'employé. Liste leurs noms complets et coordonnées."},
                {"id": "verify_dates", "title": "Vérifier les dates", "description": "Extrait les dates importantes du contrat", "sample_prompt": "Extrais toutes les dates importantes de ce contrat de travail : date de signature, date de début, période d'essai, date de fin si applicable."},
                {"id": "verify_remuneration", "title": "Vérifier rémunération", "description": "Détaille le salaire, primes et avantages", "sample_prompt": "Détaille la rémunération dans ce contrat de travail : salaire de base, primes, avantages, révisions salariales prévues."},
                {"id": "verify_obligations", "title": "Vérifier les obligations", "description": "Liste les obligations de l'employé et de l'employeur", "sample_prompt": "Liste toutes les obligations de l'employé et de l'employeur mentionnées dans ce contrat de travail."},
                {"id": "analyze_risky_clauses", "title": "Analyser clauses à risque", "description": "Identifie les clauses restrictives ou problématiques", "sample_prompt": "Analyse ce contrat de travail et identifie les clauses potentiellement restrictives ou problématiques (clause de non-concurrence, clause d'exclusivité, etc.)."},
                {"id": "extract_structured", "title": "Extraire données structurées", "description": "Extrait toutes les données dans un format structuré", "sample_prompt": "Extrait toutes les données structurées de ce contrat de travail : parties, dates, rémunération, obligations, conditions de travail."}
            ],
            'contrat_vente': [
                {"id": "verify_parties", "title": "Vérifier les parties", "description": "Identifie l'acheteur et le vendeur", "sample_prompt": "Identifie les parties de ce contrat de vente : l'acheteur et le vendeur. Liste leurs noms complets et coordonnées."},
                {"id": "verify_dates", "title": "Vérifier les dates", "description": "Extrait les dates importantes", "sample_prompt": "Extrais toutes les dates importantes de ce contrat de vente : date de signature, date de livraison, dates de paiement."},
                {"id": "verify_amounts", "title": "Vérifier les montants", "description": "Détaille le prix et modalités de paiement", "sample_prompt": "Détaille tous les montants de ce contrat de vente : prix total, acompte, modalités de paiement, échéances."},
                {"id": "verify_object", "title": "Vérifier l'objet", "description": "Décrit précisément l'objet de la vente", "sample_prompt": "Décris précisément l'objet de cette vente : nature du bien, caractéristiques, quantité, état."},
                {"id": "verify_guarantees", "title": "Vérifier garanties", "description": "Liste les garanties et conditions", "sample_prompt": "Liste toutes les garanties mentionnées dans ce contrat de vente et leurs conditions."},
                {"id": "extract_structured", "title": "Extraire données structurées", "description": "Extrait toutes les données dans un format structuré", "sample_prompt": "Extrait toutes les données structurées de ce contrat de vente : parties, dates, montants, objet, garanties, conditions."}
            ],
            'contrat_generique': [
                {"id": "verify_parties", "title": "Vérifier les parties", "description": "Identifie toutes les parties", "sample_prompt": "Identifie toutes les parties de ce contrat avec leurs noms complets et coordonnées."},
                {"id": "verify_dates", "title": "Vérifier les dates", "description": "Extrait toutes les dates importantes", "sample_prompt": "Extrais toutes les dates importantes de ce contrat : signature, échéances, dates de paiement."},
                {"id": "verify_amounts", "title": "Vérifier les montants", "description": "Liste tous les montants et modalités", "sample_prompt": "Liste tous les montants mentionnés dans ce contrat et leurs modalités de paiement."},
                {"id": "verify_object", "title": "Vérifier l'objet", "description": "Décrit précisément l'objet du contrat", "sample_prompt": "Décris précisément l'objet de ce contrat en une phrase claire."},
                {"id": "analyze_risky_clauses", "title": "Analyser clauses à risque", "description": "Identifie les clauses problématiques", "sample_prompt": "Analyse ce contrat et identifie les clauses potentiellement problématiques ou désavantageuses."},
                {"id": "verify_obligations", "title": "Vérifier les obligations", "description": "Liste les obligations de chaque partie", "sample_prompt": "Liste toutes les obligations de chaque partie mentionnées dans ce contrat."},
                {"id": "extract_structured", "title": "Extraire données structurées", "description": "Extrait toutes les données dans un format structuré", "sample_prompt": "Extrait toutes les données structurées de ce contrat : parties, dates, montants, objet, obligations, clauses importantes."}
            ],
            'testament': [
                {"id": "verify_testator", "title": "Vérifier le testateur", "description": "Identifie le testateur", "sample_prompt": "Identifie le testateur de ce testament avec ses coordonnées complètes."},
                {"id": "verify_beneficiaries", "title": "Vérifier bénéficiaires", "description": "Liste tous les bénéficiaires et leurs parts", "sample_prompt": "Liste tous les bénéficiaires de ce testament et leurs parts respectives."},
                {"id": "verify_dates", "title": "Vérifier les dates", "description": "Extrait les dates importantes", "sample_prompt": "Extrais toutes les dates importantes de ce testament : date de rédaction, signature, modifications éventuelles."},
                {"id": "verify_legacies", "title": "Vérifier les legs", "description": "Détaille tous les legs et héritages", "sample_prompt": "Détaille tous les legs et héritages mentionnés dans ce testament."},
                {"id": "verify_executor", "title": "Vérifier l'exécuteur", "description": "Identifie l'exécuteur testamentaire", "sample_prompt": "Identifie l'exécuteur testamentaire mentionné dans ce testament."},
                {"id": "extract_structured", "title": "Extraire données structurées", "description": "Extrait toutes les données dans un format structuré", "sample_prompt": "Extrait toutes les données structurées de ce testament : testateur, bénéficiaires, legs, dates, exécuteur."}
            ],
            'acte_notarie': [
                {"id": "verify_parties", "title": "Vérifier les parties", "description": "Identifie toutes les parties", "sample_prompt": "Identifie toutes les parties impliquées dans cet acte notarié avec leurs coordonnées."},
                {"id": "verify_dates", "title": "Vérifier les dates", "description": "Extrait toutes les dates importantes", "sample_prompt": "Extrais toutes les dates importantes de cet acte notarié."},
                {"id": "verify_amounts", "title": "Vérifier les montants", "description": "Liste tous les montants et transactions", "sample_prompt": "Liste tous les montants et transactions mentionnés dans cet acte notarié."},
                {"id": "verify_object", "title": "Vérifier l'objet", "description": "Décrit précisément l'objet de l'acte", "sample_prompt": "Décris précisément l'objet de cet acte notarié."},
                {"id": "verify_notary", "title": "Vérifier le notaire", "description": "Identifie le notaire et son étude", "sample_prompt": "Identifie le notaire qui a rédigé cet acte et son étude notariale."},
                {"id": "extract_structured", "title": "Extraire données structurées", "description": "Extrait toutes les données dans un format structuré", "sample_prompt": "Extrait toutes les données structurées de cet acte notarié : parties, dates, montants, objet, notaire."}
            ],
            'lettre': [
                {"id": "verify_sender", "title": "Vérifier l'expéditeur", "description": "Identifie l'expéditeur de la lettre", "sample_prompt": "Identifie l'expéditeur de cette lettre : nom, fonction, organisation, coordonnées."},
                {"id": "verify_recipient", "title": "Vérifier le destinataire", "description": "Identifie le destinataire de la lettre", "sample_prompt": "Identifie le destinataire de cette lettre : nom, fonction, organisation, coordonnées."},
                {"id": "verify_date", "title": "Vérifier la date", "description": "Extrait la date de la lettre", "sample_prompt": "Extrais la date de cette lettre (date d'écriture, date d'envoi si mentionnée)."},
                {"id": "verify_object", "title": "Vérifier l'objet", "description": "Décrit l'objet et le but de la lettre", "sample_prompt": "Décris l'objet et le but principal de cette lettre en une phrase claire."},
                {"id": "verify_key_information", "title": "Vérifier infos clés", "description": "Extrait les informations importantes mentionnées", "sample_prompt": "Extrais toutes les informations importantes mentionnées dans cette lettre : montants, dates, références, engagements."},
                {"id": "extract_structured", "title": "Extraire données structurées", "description": "Extrait toutes les données dans un format structuré", "sample_prompt": "Extrait toutes les données structurées de cette lettre : expéditeur, destinataire, date, objet, informations clés."}
            ],
            'document_financier': [
                {"id": "verify_parties", "title": "Vérifier les parties", "description": "Identifie les parties concernées", "sample_prompt": "Identifie toutes les parties concernées par ce document financier : employeur, employé, institution, etc."},
                {"id": "verify_period", "title": "Vérifier la période", "description": "Extrait la période couverte", "sample_prompt": "Extrais la période couverte par ce document financier : dates de début et de fin."},
                {"id": "verify_amounts", "title": "Vérifier les montants", "description": "Liste tous les montants et totaux", "sample_prompt": "Liste tous les montants mentionnés dans ce document financier : revenus, déductions, impôts, totaux."},
                {"id": "verify_deductions", "title": "Vérifier déductions", "description": "Détaille toutes les déductions", "sample_prompt": "Détaille toutes les déductions mentionnées dans ce document financier : impôts, cotisations, autres déductions."},
                {"id": "extract_structured", "title": "Extraire données structurées", "description": "Extrait toutes les données dans un format structuré", "sample_prompt": "Extrait toutes les données structurées de ce document financier : parties, période, montants, déductions, totaux."}
            ]
        }
        
        # Utiliser les actions spécifiques si disponible, sinon actions génériques
        actions_list = fallback_actions.get(doc_type, [
            {"id": "summarize_all", "title": "Résumer documents", "description": "Génère un résumé global des documents", "sample_prompt": "Fournis un résumé clair et structuré de tous les documents uploadés, en mettant en évidence les thèmes principaux et les informations importantes. Adapte le résumé au type de document : pour un CV, concentre-toi sur l'expérience professionnelle, les compétences et les réalisations ; pour un document financier, mentionne les montants et chiffres pertinents ; pour un contrat, mentionne les parties et dates importantes. Ne mentionne PAS d'informations qui ne sont pas présentes dans les documents (par exemple, ne mentionne pas d'informations financières si le document est un CV)."},
            {"id": "extract_key_points", "title": "Extraire points clés", "description": "Liste les points clés et entités", "sample_prompt": "Extrais les points clés, décisions importantes et entités nommées (personnes, entreprises, lieux) de tous les documents uploadés et organise-les en puces."},
            {"id": "extract_structured", "title": "Extraire données structurées", "description": "Extrait toutes les données dans un format structuré", "sample_prompt": "Extrait toutes les données structurées de ce document : parties, dates, montants, informations clés."}
        ])
        
        return {
            "domain": doc_type,
            "suggested_actions": actions_list
        }

async def save_file_description(file_name, description):
    with open(DESCRIPTIONS_FILE, 'r') as f:
        descriptions = json.load(f)
    descriptions.append({"file_name": file_name, "description": description})
    with open(DESCRIPTIONS_FILE, 'w') as f:
        json.dump(descriptions, f, indent=4)

async def query_model(file_name, file_content, directory_content, repo_structure, user_query, is_binary=False, selected_model=DEFAULT_MODEL, language='en'):
    cache_key = f"query_{file_name}_{user_query}_{selected_model}_{language}"
    cached = await cache.get(cache_key)
    if cached:
        return cached

    # fallback to English if unknown language
    t = translations.get(language, translations['en'])

    # Construire le résumé des autres fichiers
    directory_content_summary = ' '.join(
        [f"{t['other_file']}: {doc['fileName']} : {doc['content']}" for doc in directory_content]
    )

    # Construire le prompt multilangue
    prompt = (
        f"{t['project_structure']}:\n{repo_structure}\n\n"
        f"{t['file']}: {file_name}\n\n"
        f"{t['content']}:\n{file_content}\n\n"
        f"{directory_content_summary}\n\n"
        f"{t['question']}: {user_query}\n\n"
        f"{t['emoji']}"
    )

    try:
        # Enhanced model routing with GPT-5 variants
        if selected_model.lower() in ["gpt-3.5-turbo", "gpt-4o"]:
            result = call_openai_api(prompt, selected_model)
        elif selected_model.lower() in ["gpt-5", "gpt-5-mini", "gpt-5-nano"]:
            result = call_openai_api(prompt, selected_model)
        elif selected_model.lower() == "openai":
            # Legacy compatibility
            result = call_openai_api(prompt, "openai")
        elif selected_model.lower() == "mistral":
            result = call_mistral_api(prompt)
        elif selected_model.lower() in OLLAMA_MODELS or selected_model.lower() == "llama3":
            result = call_ollama_api(prompt, selected_model)
        else:
            logger.warning(f"Unknown model {selected_model}, falling back to default {DEFAULT_MODEL}")
            result = call_openai_api(prompt, DEFAULT_MODEL)
            
    except Exception as e:
        result = f"Error querying model: {str(e)}"

    await cache.set(cache_key, result, ttl=3600)
    return result

# Validation de la configuration
try:
    FlaskConfig.validate_env_vars()
    logger.info("✅ Configuration validée")
except ValueError as e:
    logger.error(f"❌ Erreur de configuration: {e}")

# Initialisation de la base de données d'authentification
init_database()

# Enregistrement des routes d'authentification
register_auth_routes(app)

# New endpoint to get available models with detailed info
@app.route('/models', methods=['GET'])
def get_available_models():
    """
    Returns a list of available models with detailed configuration
    """
    models = []
    for model_id, config in MODEL_CONFIG.items():
        model_info = {
            "id": model_id,
            "name": config["name"],
            "provider": config["provider"],
            "description": config["description"],
            "cost_tier": config["cost_tier"],
            "max_tokens": config["max_tokens"],
            "is_default": model_id == DEFAULT_MODEL
        }
        models.append(model_info)
    
    return jsonify({
        "models": models,
        "default_model": DEFAULT_MODEL,
        "total_count": len(models)
    }), 200

@app.route('/models/<model_id>/test', methods=['POST'])
def test_model(model_id):
    """
    Test if a specific model is available and working
    """
    if model_id not in MODEL_CONFIG:
        return jsonify({"error": "Model not found"}), 404
    
    test_prompt = "Hello, please respond with 'Model is working correctly.'"
    
    try:
        if model_id in ["gpt-3.5-turbo", "gpt-4o", "gpt-5", "gpt-5-mini", "gpt-5-nano", "openai"]:
            response = call_openai_api(test_prompt, model_id)
        elif model_id == "mistral":
            response = call_mistral_api(test_prompt)
        elif model_id in OLLAMA_MODELS or model_id == "llama3":
            response = call_ollama_api(test_prompt, model_id)
        else:
            return jsonify({"error": "Model not supported"}), 400
            
        return jsonify({
            "model_id": model_id,
            "status": "available",
            "test_response": response,
            "config": MODEL_CONFIG[model_id]
        }), 200
        
    except Exception as e:
        logger.error(f"Model test failed for {model_id}: {str(e)}")
        return jsonify({
            "model_id": model_id,
            "status": "unavailable",
            "error": str(e),
            "config": MODEL_CONFIG[model_id]
        }), 503

# Enhanced Flask Routes
@app.route('/upload', methods=['POST'])
async def upload_files():
    if 'files' not in request.files:
        return jsonify({"error": "No files provided"}), 400

    files = request.files.getlist('files')
    selected_model = request.form.get('model', DEFAULT_MODEL)  # Use GPT-3.5-Turbo as default
    language = request.form.get('language', 'en')
    results, texts = [], []

    # Validate model
    if selected_model not in MODEL_CONFIG:
        logger.warning(f"Unknown model {selected_model}, using default {DEFAULT_MODEL}")
        selected_model = DEFAULT_MODEL

    for file in files:
        file_name = file.filename
        extension = file_name.rsplit('.', 1)[-1].lower() if '.' in file_name else ''
        is_binary = extension in ['docx', 'pdf']

        file_content = (extract_text_from_docx(file) if extension == 'docx' else
                        extract_text_from_pdf(file) if extension == 'pdf' else
                        file.read().decode('utf-8', errors='ignore'))

        description = await analyze_file_content(file_content, file_name, is_binary, extension, selected_model, language)
        await save_file_description(file_name, description)
        if not description.startswith("Error"):
            texts.append(description)
        results.append({
            "file_name": file_name, 
            "description": description,
            "model_used": selected_model
        })

    if texts:
        splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
        docs = [doc for text in texts for doc in splitter.create_documents([text])]
        global vector_store
        if vector_store is None:
            vector_store = FAISS.from_documents(docs, embeddings)
        else:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, vector_store.add_documents, docs)

    return jsonify({
        "message": "Files processed successfully", 
        "results": results,
        "model_used": selected_model,
        "model_config": MODEL_CONFIG.get(selected_model, {})
    }), 200

def perform_online_search(query: str, language: str = 'en') -> str:
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
            'no_cache': 'true'  # Force fresh results
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
    Le LLM évalue chaque document par rapport à la requête et les trie par pertinence.
    """
    try:
        if len(documents) <= 5:
            return documents  # Pas besoin de re-ranking pour peu de documents
        
        # Construire le prompt de re-ranking
        docs_summary = []
        for i, doc in enumerate(documents):
            file_name = doc.metadata.get("fileName") or doc.metadata.get("file_name") or f"document_{i}"
            content_snippet = doc.page_content[:500]  # Premier 500 chars pour le prompt
            docs_summary.append(f"[{i}] Fichier: {file_name}\nContenu: {content_snippet}...")
        
        rerank_prompt = f"""Tu dois classer ces documents par ordre de pertinence pour répondre à cette question: "{query}"

Documents à classer:
{chr(10).join(docs_summary)}

Retourne UNIQUEMENT une liste JSON des indices (nombres entre crochets) dans l'ordre de pertinence décroissante.
Format: [3, 1, 5, 2, 0, 4, ...]

Réponds UNIQUEMENT avec le JSON, sans explication."""
        
        # Appel au modèle pour re-ranking
        rerank_response = call_openai_api(rerank_prompt, model)
        
        # Extraire les indices du JSON
        import json
        json_match = re.search(r'\[.*?\]', rerank_response)
        if json_match:
            ranked_indices = json.loads(json_match.group())
            # Vérifier que tous les indices sont valides
            valid_indices = [idx for idx in ranked_indices if 0 <= idx < len(documents)]
            if len(valid_indices) == len(documents):
                reranked = [documents[idx] for idx in valid_indices]
                logger.info(f"✅ Re-ranking réussi: {len(reranked)} documents reclassés")
                return reranked
        
        # Fallback: retourner l'ordre original si le parsing échoue
        logger.warning("Re-ranking JSON invalide, utilisation de l'ordre original")
        return documents
        
    except Exception as e:
        logger.warning(f"Erreur lors du re-ranking: {str(e)}, utilisation de l'ordre original")
        return documents

def search_semantic_documents_sync(vector_store, user_query: str, session_id: str = 'default', conversation_history: Optional[List[Dict]] = None) -> List[Dict]:
    """
    Fonction helper synchrone pour rechercher des documents pertinents dans le vector store.
    Retourne une liste de dictionnaires avec 'fileName' et 'content'.
    AMÉLIORATION: Détecte les noms de personnes et filtre strictement par nom.
    Utilise l'historique de conversation pour détecter les pronoms (he, she, his, her).
    """
    try:
        # DÉTECTION DES NOMS DE PERSONNES dans la requête ET l'historique
        person_names = set()
        words = user_query.split()
        
        # Détecter les pronoms et chercher le nom dans l'historique
        query_lower = user_query.lower()
        has_pronoun = any(pronoun in query_lower for pronoun in ['he', 'she', 'his', 'her', 'him', 'they', 'their'])
        
        if has_pronoun and conversation_history:
            # Chercher le dernier nom mentionné dans l'historique
            for turn in reversed(conversation_history):
                content = (turn.get("content") or "").lower()
                # Chercher les noms dans l'historique
                for name in ['karim', 'dominique', 'essome', 'ngami']:
                    if name in content:
                        person_names.add(name)
                        logger.info(f"👤 Nom détecté depuis l'historique (pronoun détecté): {name}")
                        break
                if person_names:
                    break
        
        # Détecter les noms dans la requête actuelle
        for i, word in enumerate(words):
            clean_word = word.strip('.,!?;:()[]{}"\'').strip()
            # Détecter les noms propres (capitalisés) ou les mots après "his", "her", "their", etc.
            if clean_word and clean_word[0].isupper() and len(clean_word) > 2:
                person_names.add(clean_word.lower())
            # Détecter après des mots indicateurs
            if i > 0 and words[i-1].lower() in ['his', 'her', 'their', 'karim', 'dominique', 'about', 'for']:
                if len(clean_word) > 2:
                    person_names.add(clean_word.lower())
        
        # Ajouter aussi les noms communs dans les requêtes (karim, dominique, etc.)
        common_names = ['karim', 'dominique', 'essome', 'ngami']
        for name in common_names:
            if name in query_lower:
                person_names.add(name)
        
        logger.info(f"👤 Noms de personnes détectés (requête + historique): {person_names}")
        
        # Recherche sémantique
        # AMÉLIORATION: Recherche avec plus de résultats et recherche multiple pour meilleure précision
        # Recherche principale avec la requête complète
        search_results_with_scores = vector_store.similarity_search_with_score(user_query, k=50)
        
        # Recherche supplémentaire avec les mots-clés individuels pour capturer les noms de fonctions/méthodes
        query_words = [word.strip('.,!?;:()[]{}"\'').lower() for word in user_query.split() if len(word.strip('.,!?;:()[]{}"\'')) > 2]
        additional_results = []
        for word in query_words[:5]:  # Limiter à 5 mots pour éviter trop de résultats
            try:
                word_results = vector_store.similarity_search_with_score(word, k=10)
                additional_results.extend(word_results)
            except:
                pass
        
        # Combiner et dédupliquer les résultats
        all_search_results = {}
        for doc, score in search_results_with_scores:
            doc_id = id(doc)
            if doc_id not in all_search_results or score < all_search_results[doc_id][1]:
                all_search_results[doc_id] = (doc, score)
        
        for doc, score in additional_results:
            doc_id = id(doc)
            if doc_id not in all_search_results or score < all_search_results[doc_id][1]:
                all_search_results[doc_id] = (doc, score)
        
        search_results_with_scores = list(all_search_results.values())
        
        # Extraire les mots-clés (y compris noms propres courts)
        query_keywords = set()
        for word in user_query.split():
            clean_word = word.strip('.,!?;:()[]{}"\'').lower()
            if len(clean_word) > 2:
                query_keywords.add(clean_word)
        
        logger.info(f"🔑 Mots-clés extraits: {query_keywords}")
        
        # Recherche par nom de fichier - Essayer de récupérer tous les documents
        filename_matches = []
        try:
            # Méthode 1: Recherche avec une requête très large pour récupérer beaucoup de documents
            all_docs_from_store = vector_store.similarity_search("document file content", k=1000)
            
            # Méthode 2: Si on peut accéder au docstore directement, l'utiliser
            if hasattr(vector_store, 'docstore') and hasattr(vector_store.docstore, '_dict'):
                all_docs_dict = vector_store.docstore._dict
                logger.info(f"📦 Accès direct au docstore: {len(all_docs_dict)} documents disponibles")
                # Convertir les valeurs du dict en documents
                all_docs_from_store = list(all_docs_dict.values()) if all_docs_dict else all_docs_from_store
            
            logger.info(f"🔍 Recherche dans {len(all_docs_from_store)} documents pour correspondance de nom")
            
            for doc in all_docs_from_store:
                file_name_from_meta = (doc.metadata.get("fileName") or doc.metadata.get("file_name") or "").lower()
                for keyword in query_keywords:
                    if keyword in file_name_from_meta:
                        filename_matches.append(doc)
                        logger.info(f"📁 Fichier trouvé par nom: {doc.metadata.get('fileName', 'N/A')} (mot-clé: '{keyword}')")
                        break
        except Exception as e:
            logger.warning(f"Erreur lors de la récupération de tous les documents: {str(e)}")
        
        logger.info(f"📂 {len(filename_matches)} fichiers trouvés par correspondance de nom")
        
        # AMÉLIORATION: Recherche explicite par nom de fonction/méthode dans le contenu
        function_name_matches = []
        # Extraire les noms potentiels de fonctions/méthodes de la requête (mots avec underscore ou camelCase)
        potential_function_names = []
        query_words_for_func = user_query.split()
        for word in query_words_for_func:
            clean_word = word.strip('.,!?;:()[]{}"\'').strip()
            # Détecter les noms de fonctions (avec underscore ou camelCase)
            if '_' in clean_word or (clean_word and clean_word[0].islower() and any(c.isupper() for c in clean_word[1:])):
                potential_function_names.append(clean_word.lower())
                potential_function_names.append(clean_word)  # Garder aussi la version originale
        
        # Rechercher explicitement ces noms dans le contenu
        if potential_function_names:
            try:
                all_docs_for_function_search = vector_store.similarity_search("function method def class", k=500)
                for doc in all_docs_for_function_search:
                    content_lower = doc.page_content.lower()
                    for func_name in potential_function_names:
                        if func_name.lower() in content_lower:
                            function_name_matches.append(doc)
                            logger.info(f"🔧 Fonction/méthode trouvée par nom: '{func_name}' dans {doc.metadata.get('fileName', 'N/A')}")
                            break
            except Exception as e:
                logger.warning(f"Erreur lors de la recherche par nom de fonction: {str(e)}")
        
        logger.info(f"🔧 {len(function_name_matches)} documents trouvés par correspondance de nom de fonction/méthode")
        
        # Combiner les résultats avec priorité aux correspondances exactes
        all_candidate_docs = {}
        # Priorité 1: Correspondances de noms de fonctions (score très élevé)
        for doc in function_name_matches:
            all_candidate_docs[id(doc)] = (doc, 0.95)  # Score très élevé pour correspondances exactes
        
        # Priorité 2: Correspondances de noms de fichiers (score élevé)
        for doc in filename_matches:
            doc_id = id(doc)
            if doc_id not in all_candidate_docs:
                all_candidate_docs[doc_id] = (doc, 0.85)
        
        # Priorité 3: Résultats de recherche sémantique (score normalisé)
        for doc, score in search_results_with_scores:
            doc_id = id(doc)
            # Si déjà présent avec un meilleur score, garder le meilleur
            if doc_id not in all_candidate_docs:
                all_candidate_docs[doc_id] = (doc, 1 - score)
            elif all_candidate_docs[doc_id][1] < (1 - score):
                # Si le nouveau score est meilleur, le remplacer
                all_candidate_docs[doc_id] = (doc, 1 - score)
        
        # FILTRAGE STRICT PAR NOM DE PERSONNE (CRITIQUE)
        # Si un nom de personne est détecté, ne garder QUE les fichiers correspondant à ce nom
        query_words = [w.strip('.,!?;:()[]{}"\'').lower() for w in user_query.split() if len(w.strip('.,!?;:()[]{}"\'')) > 2]
        filename_match_ids = {id(doc) for doc in filename_matches}
        filtered_docs = []
        
        # Liste des noms de personnes connus pour exclusion
        known_person_names = {
            'karim': ['dominique', 'essome'],
            'dominique': ['karim', 'ngami'],
            'essome': ['karim', 'ngami'],
            'ngami': ['dominique', 'essome']
        }
        
        # Déterminer les noms à exclure
        names_to_exclude = set()
        for detected_name in person_names:
            if detected_name in known_person_names:
                names_to_exclude.update(known_person_names[detected_name])
        
        logger.info(f"🚫 Noms à exclure (autres personnes): {names_to_exclude}")
        
        for doc, similarity_score in all_candidate_docs.values():
            doc_id = id(doc)
            file_name_lower = (doc.metadata.get("fileName") or doc.metadata.get("file_name") or "").lower()
            doc_content_lower = doc.page_content[:500].lower()  # Vérifier aussi dans le contenu
            
            # EXCLUSION STRICTE: Si un nom de personne est détecté, exclure les fichiers d'autres personnes
            should_exclude = False
            if person_names:
                # RÈGLE 1: Exclure TOUJOURS les fichiers contenant un nom à exclure (même avec score élevé)
                for exclude_name in names_to_exclude:
                    if exclude_name in file_name_lower:
                        should_exclude = True
                        logger.info(f"❌ Fichier EXCLU (nom de fichier contient '{exclude_name}'): {doc.metadata.get('fileName', 'N/A')}")
                        break
                    # Vérifier aussi dans le contenu (premiers 200 caractères pour être plus strict)
                    if exclude_name in doc_content_lower[:200]:
                        should_exclude = True
                        logger.info(f"❌ Fichier EXCLU (contenu contient '{exclude_name}'): {doc.metadata.get('fileName', 'N/A')}")
                        break
                
                # RÈGLE 2: Si un nom de personne est détecté, ne garder QUE les fichiers qui contiennent ce nom
                if not should_exclude:
                    file_contains_person_name = any(name in file_name_lower for name in person_names)
                    # Vérifier aussi dans le contenu si pas dans le nom
                    if not file_contains_person_name:
                        file_contains_person_name = any(name in doc_content_lower[:300] for name in person_names)
                    
                    if not file_contains_person_name:
                        # Si aucun nom de personne n'est dans le fichier, EXCLURE TOUJOURS (même avec score élevé)
                        should_exclude = True
                        logger.info(f"⚠️ Fichier EXCLU (ne contient AUCUN nom de la personne recherchée): {doc.metadata.get('fileName', 'N/A')}")
            
            if should_exclude:
                continue  # Exclure ce document
            
            filename_keyword_matches = sum(1 for word in query_words if word in file_name_lower)
            
            # Score élevé pour les fichiers trouvés par nom de personne
            if doc_id in filename_match_ids:
                # Bonus supplémentaire si le fichier contient le nom de la personne détectée
                person_name_bonus = 0.0
                if person_names:
                    for name in person_names:
                        if name in file_name_lower:
                            person_name_bonus = 0.15
                            break
                filtered_docs.append((doc, 0.9 + person_name_bonus))
                logger.info(f"✅ Fichier inclus (correspond au nom): {doc.metadata.get('fileName', 'N/A')}")
            elif similarity_score >= 0.45 or filename_keyword_matches >= 1:
                filtered_docs.append((doc, similarity_score))
        
        filtered_docs.sort(key=lambda x: x[1], reverse=True)
        # AMÉLIORATION: Augmenter le nombre de documents récupérés pour améliorer la précision
        # Si un nom de personne est détecté, limiter aux top 20 fichiers les plus pertinents
        # Sinon, prendre jusqu'à 30 documents pour avoir plus de contexte
        max_docs = 20 if person_names else 30
        top_docs = [doc for doc, score in filtered_docs[:max_docs]]
        
        logger.info(f"📊 {len(top_docs)} documents finaux sélectionnés après filtrage strict par nom")
        
        # Construire la liste de résultats avec amélioration du contenu
        seen_docs = set()
        results = []
        for doc in top_docs:
            file_name_from_meta = doc.metadata.get("fileName") or doc.metadata.get("file_name") or "document_vectorstore"
            content_preview = doc.page_content[:100]
            doc_key = f"{file_name_from_meta}:{content_preview}"
            
            if doc_key not in seen_docs:
                seen_docs.add(doc_key)
                # AMÉLIORATION: Augmenter la taille du contenu et chercher le contexte autour des mots-clés
                content = doc.page_content
                query_lower = user_query.lower()
                query_words = [w.strip('.,!?;:()[]{}"\'').lower() for w in user_query.split() if len(w.strip('.,!?;:()[]{}"\'')) > 2]
                
                # Si on trouve un mot-clé dans le contenu, essayer d'inclure plus de contexte autour
                content_lower = content.lower()
                for word in query_words:
                    if word in content_lower:
                        # Trouver la position du mot et inclure plus de contexte
                        idx = content_lower.find(word)
                        if idx > 0:
                            # Inclure 500 caractères avant et après pour capturer toute la fonction
                            start = max(0, idx - 500)
                            end = min(len(content), idx + len(word) + 500)
                            # Si le contenu extrait est plus pertinent, l'utiliser
                            if end - start > len(content[:3000]):
                                content = content[start:end]
                                break
                
                results.append({
                    "fileName": file_name_from_meta,
                    "content": content[:3000]  # Augmenté de 2500 à 3000 pour plus de contexte
                })
        
        logger.info(f"📚 {len(results)} documents uniques récupérés pour la requête")
        return results
        
    except Exception as e:
        logger.error(f"Erreur lors de la recherche sémantique synchrone: {str(e)}")
        return []

async def detect_missing_information(response: str, user_query: str, language: str = 'en') -> bool:
    """
    Détecte si la réponse du modèle indique que l'information n'est pas disponible dans les documents
    ou si une recherche en ligne serait utile pour obtenir des informations en temps réel.
    Retourne True si l'information semble absente ou si une recherche en ligne serait bénéfique.
    """
    response_lower = response.lower()
    query_lower = user_query.lower()
    
    # Phrases indicatrices que l'information n'est pas disponible
    missing_indicators = [
        "n'apparaît pas",
        "n'est pas disponible",
        "n'est pas présent",
        "n'est pas trouvé",
        "n'est pas mentionné",
        "n'est pas indiqué",
        "n'est pas fourni",
        "n'est pas dans",
        "ne figure pas",
        "ne contient pas",
        "aucune information",
        "pas d'information",
        "information absente",
        "information non disponible",
        "je ne trouve pas",
        "je n'ai pas trouvé",
        "impossible de trouver",
        "ne peut pas être trouvé",
        "does not appear",
        "is not available",
        "is not present",
        "is not found",
        "is not mentioned",
        "is not indicated",
        "is not provided",
        "is not in",
        "no information",
        "information not available",
        "i cannot find",
        "i did not find",
        "unable to find",
        "cannot be found"
    ]
    
    # Indicateurs que des informations plus récentes seraient utiles
    needs_recent_info_indicators = [
        "informations plus récentes",
        "information plus récente",
        "données plus récentes",
        "vérifier les changements",
        "confirmer que",
        "pourrait être utile",
        "serait utile",
        "pourrait nécessiter",
        "nécessiterait",
        "more recent information",
        "recent information",
        "more recent data",
        "check for changes",
        "confirm that",
        "might be useful",
        "would be useful",
        "might require",
        "would require",
        "should verify",
        "devrait vérifier",
        "il est important de vérifier",
        "it is important to check"
    ]
    
    # Mots-clés dans la requête qui indiquent un besoin d'informations en temps réel
    real_time_query_keywords = [
        "heure actuelle",
        "heure maintenant",
        "quelle heure",
        "what time",
        "current time",
        "time now",
        "prix actuel",
        "prix maintenant",
        "current price",
        "price now",
        "taux actuel",
        "current rate",
        "taux de change",
        "exchange rate",
        "cours actuel",
        "current rate",
        "événements récents",
        "recent events",
        "nouvelles récentes",
        "recent news",
        "maintenant",
        "now",
        "actuel",
        "current",
        "aujourd'hui",
        "today",
        "en ce moment",
        "right now",
        "à l'instant",
        "at the moment"
    ]
    
    # Vérifier si la réponse contient des indicateurs d'absence
    has_missing_indicator = any(indicator in response_lower for indicator in missing_indicators)
    
    # Vérifier si la réponse suggère qu'une information plus récente serait utile
    needs_recent_info = any(indicator in response_lower for indicator in needs_recent_info_indicators)
    
    # Vérifier si la requête demande des informations en temps réel
    needs_realtime_info = any(keyword in query_lower for keyword in real_time_query_keywords)
    
    # Vérifier aussi la longueur de la réponse - si elle est très courte, c'est probablement qu'il n'y a pas d'info
    is_very_short = len(response.strip()) < 100
    
    # Vérifier si la réponse contient des phrases comme "d'après les documents" ou "dans les documents fournis"
    # Si oui, c'est probablement qu'il n'y a pas d'info ailleurs
    mentions_documents_only = any(phrase in response_lower for phrase in [
        "dans les documents fournis",
        "dans les documents",
        "dans le document",
        "d'après les documents",
        "selon les documents",
        "in the provided documents",
        "in the documents",
        "in the document",
        "according to the documents"
    ])
    
    # Déclencher une recherche en ligne si :
    # 1. La réponse indique que l'info est absente
    # 2. La réponse suggère qu'une info plus récente serait utile
    # 3. La requête demande des informations en temps réel
    # 4. La réponse est très courte ET mentionne seulement les documents
    should_search_online = (
        has_missing_indicator or 
        needs_recent_info or 
        needs_realtime_info or 
        (is_very_short and mentions_documents_only)
    )
    
    if should_search_online:
        reason = []
        if has_missing_indicator:
            reason.append("information absente")
        if needs_recent_info:
            reason.append("besoin d'informations récentes")
        if needs_realtime_info:
            reason.append("demande d'informations en temps réel")
        logger.info(f"🔍 Recherche en ligne déclenchée: {', '.join(reason)}")
    
    return should_search_online

async def query_model_local_mode(file_name: str, file_content: str, directory_content: List[Dict], 
                                repo_structure: str, user_query: str, is_binary: bool = False, 
                                selected_model: str = DEFAULT_MODEL, language: str = 'en',
                                conversation_history: Optional[List[Dict]] = None,
                                enable_auto_online_search: bool = True) -> str:
    """
    Mode LOCAL: analyse STRICTEMENT les documents fournis (fichier principal + contexte).
    On réduit et structure le contexte pour améliorer la précision et limiter les hallucinations.
    IMPORTANT: pas de cache sur ce mode, pour toujours prendre en compte le contexte le plus récent
    (nouveaux fichiers indexés, corrections, etc.).
    """
    t = translations.get(language, translations['en'])

    # Amélioration: Organiser le contexte par pertinence et préserver les informations clés
    max_chunk_len = 2000  # Augmenté encore plus pour préserver le maximum de contexte
    contextual_docs: List[str] = []
    
    # Grouper les documents par fichier source pour éviter la duplication et préserver le contexte complet
    docs_by_file = {}
    for doc in directory_content or []:
        file_label = doc.get('fileName') or doc.get('file_name') or "document_contextuel"
        raw_content = doc.get('content', '') or ''
        
        if file_label not in docs_by_file:
            docs_by_file[file_label] = []
        docs_by_file[file_label].append(raw_content)
    
    # Construire un résumé structuré par fichier (les premiers sont les plus pertinents)
    # IMPORTANT: Préserver le maximum de contenu pour capturer les informations comme les adresses
    for idx, (file_label, contents) in enumerate(docs_by_file.items(), 1):
        # Combiner les chunks du même fichier avec un séparateur clair
        combined_content = "\n---\n".join(contents)
        
        # Pour les fichiers pertinents (top 5), préserver encore plus de contenu
        extended_max_len = max_chunk_len * 1.5 if idx <= 5 else max_chunk_len
        
        # Tronquer intelligemment en préservant le début et la fin
        if len(combined_content) > extended_max_len:
            # Garder le début (souvent le plus important) et un peu de la fin
            # Augmenter la partie finale pour capturer les informations en fin de document
            content = combined_content[:int(extended_max_len - 300)] + "\n[... section tronquée ...]\n" + combined_content[-300:]
        else:
            content = combined_content
        
        # Marquer les documents les plus pertinents (premiers dans la liste)
        relevance_marker = "⭐" if idx <= 3 else "🔍" if idx <= 8 else ""
        contextual_docs.append(f"{relevance_marker} [{idx}] {file_label}:\n{content}")

    directory_content_summary = "\n\n" + "="*80 + "\n\n".join(contextual_docs) + "\n\n" + "="*80 if contextual_docs else t.get(
        'no_other_files', "Aucun autre fichier dans le contexte."
    )
    
    # Ajouter un header explicatif si on a du contexte
    if contextual_docs:
        directory_content_summary = (
            f"⚠️ ATTENTION: {len(docs_by_file)} fichiers ont été récupérés par recherche sémantique "
            f"car ils sont potentiellement pertinents pour ta question.\n"
            f"Les documents sont classés par pertinence:\n"
            f"  ⭐ = Très pertinent (priorité haute)\n"
            f"  🔍 = Pertinent (priorité moyenne)\n"
            f"  [numéro] = Autre document à analyser\n\n"
            f"TU DOIS ANALYSER TOUS CES FICHIERS, même si l'information semble absente du document principal.\n\n"
            f"{directory_content_summary}"
        )

    # On tronque aussi légèrement le contenu du fichier principal si nécessaire
    main_max_len = 4000
    trimmed_main_content = file_content[:main_max_len] + ("..." if len(file_content) > main_max_len else "")

    # Construire un résumé compact de l'historique de conversation (si fourni)
    history_section = ""
    if conversation_history:
      history_lines: List[str] = []
      for turn in conversation_history[-10:]:
          role = turn.get("role", "user")
          content = (turn.get("content") or "")[:600]
          prefix = "Utilisateur" if role == "user" else "Assistant"
          history_lines.append(f"{prefix}: {content}")
      if history_lines:
          history_section = "=== HISTORIQUE DE LA CONVERSATION ===\n" + "\n".join(history_lines) + "\n\n"

    # Détection des noms de personnes dans la requête pour instructions strictes
    person_names_in_query = set()
    words = user_query.split()
    for i, word in enumerate(words):
        clean_word = word.strip('.,!?;:()[]{}"\'').strip()
        if clean_word and clean_word[0].isupper() and len(clean_word) > 2:
            person_names_in_query.add(clean_word.lower())
        if i > 0 and words[i-1].lower() in ['his', 'her', 'their', 'karim', 'dominique', 'about', 'for']:
            if len(clean_word) > 2:
                person_names_in_query.add(clean_word.lower())
    
    query_lower = user_query.lower()
    common_names = ['karim', 'dominique', 'essome', 'ngami']
    for name in common_names:
        if name in query_lower:
            person_names_in_query.add(name)
    
    # Instructions strictes si un nom de personne est détecté
    person_filter_instructions = ""
    if person_names_in_query:
        person_names_str = ", ".join([name.capitalize() for name in person_names_in_query])
        person_filter_instructions = (
            f"\n🚨 INSTRUCTION CRITIQUE - FILTRAGE PAR NOM DE PERSONNE:\n"
            f"La question concerne {person_names_str}. TU DOIS UNIQUEMENT utiliser les documents qui contiennent "
            f"le(s) nom(s) '{person_names_str}' dans leur nom de fichier OU dans leur contenu.\n"
            f"❌ EXCLUSION STRICTE: N'utilise JAMAIS les documents d'autres personnes (comme Dominique si on demande Karim, "
            f"ou Karim si on demande Dominique).\n"
            f"✅ PRIORITÉ: Les fichiers dont le nom contient '{person_names_str}' sont les SEULS documents pertinents.\n"
            f"⚠️ Si un document ne contient pas le nom '{person_names_str}', IGNORE-LE COMPLÈTEMENT, même s'il semble "
            f"sémantiquement similaire à la question.\n\n"
        )
    
    # Prompt structuré et très explicite avec instructions améliorées pour la recherche sémantique
    # IMPORTANT: Le modèle doit analyser TOUS les documents, pas seulement le fichier sélectionné
    num_other_docs = len(contextual_docs) if contextual_docs else 0
    total_docs_note = f"\n⚠️ ATTENTION: Tu as accès à {num_other_docs} autres documents en plus du document principal. " \
                      f"L'information demandée peut être dans N'IMPORTE LEQUEL de ces documents. " \
                      f"ANALYSE TOUS LES DOCUMENTS avant de conclure qu'une information est absente.\n\n" if num_other_docs > 0 else ""

    prompt = (
        f"{t['local_analysis_mode']}\n"
        f"{t['no_external_search']}\n\n"
        f"{history_section}"
        f"{total_docs_note}"
        f"{person_filter_instructions}"
        f"=== CONTEXTE DU PROJET ===\n"
        f"{t['project_structure']}:\n{repo_structure}\n\n"
        f"=== DOCUMENT PRINCIPAL (FICHIER SÉLECTIONNÉ) ===\n"
        f"{t['main_file']}: {file_name}\n"
        f"⚠️ NOTE: Ce fichier est celui actuellement sélectionné, mais l'information peut être dans d'autres fichiers.\n"
        f"{t['file_content']}:\n{trimmed_main_content}\n\n"
        f"=== AUTRES DOCUMENTS DU DOSSIER (RÉCUPÉRÉS PAR RECHERCHE SÉMANTIQUE) ===\n"
        f"⚠️ IMPORTANT: Ces documents ont été récupérés car ils sont potentiellement pertinents pour ta question. "
        f"ANALYSE-TOUS MÉTICULEUSEMENT, même si l'information semble absente du document principal.\n"
        f"{directory_content_summary}\n\n"
        f"=== QUESTION À TRAITER ===\n"
        f"{t['question']}: {user_query}\n\n"
        f"{t['instructions']}:\n"
        f"{t['base_response_only']}\n"
        f"🔍 PROCÉDURE DE RECHERCHE OBLIGATOIRE:\n"
    )
    
    # Construire la première étape de la procédure (éviter les backslashes dans f-string)
    if person_names_in_query:
        step1_text = "Si la question concerne une personne spécifique, vérifie d'abord que le document principal contient le nom de cette personne. Sinon, cherche dans les autres documents."
    else:
        step1_text = f"Commence par analyser le document principal ({file_name})."
    
    prompt += (
        f"1. {step1_text}\n"
        f"2. Si l'information n'est pas trouvée, PARCOURS SYSTÉMATIQUEMENT TOUS les autres documents listés ci-dessus.\n"
        f"3. Les documents marqués ⭐ sont les plus pertinents selon la recherche sémantique - commence par ceux-là.\n"
        f"4. Ne conclus JAMAIS qu'une information est absente avant d'avoir analysé TOUS les documents fournis.\n"
        f"5. Si tu trouves l'information dans un autre document, cite explicitement le nom du fichier source.\n"
        f"6. Si l'information est dans plusieurs documents, mentionne tous les fichiers concernés.\n\n"
        f"- Les documents sont classés par pertinence sémantique: les premiers sont les plus liés à ta question.\n"
        f"- Mais même les documents moins pertinents peuvent contenir l'information recherchée - ne les ignore pas.\n"
        f"{t['missing_info_clarify']}\n"
        f"{t['no_speculation']}\n"
        f"{t['focus_local_analysis']}\n"
        f"- Tu peux faire des calculs (totaux, moyennes, salaire mensuel/annuel, etc.) "
        f"à partir des montants et périodes présents dans les documents, mais explique "
        f"clairement ton raisonnement et les formules utilisées.\n"
        f"- Si une information n'est pas directement présente mais peut être déduite "
        f"par un calcul simple à partir des données (par exemple, convertir un salaire "
        f"par paie en salaire mensuel), effectue le calcul et montre les étapes.\n"
        f"- Si une information ne peut ni être lue ni déduite des textes ci-dessus APRÈS AVOIR ANALYSÉ TOUS LES DOCUMENTS, "
        f"répond explicitement qu'elle n'apparaît pas dans les documents fournis.\n\n"
        f"{t['emoji']}"
    )

    try:
        result = await execute_model_query(prompt, selected_model)
        
        # Détection automatique si l'information n'est pas disponible et recherche en ligne si activée
        if enable_auto_online_search:
            missing_info = await detect_missing_information(result, user_query, language)
            
            if missing_info:
                logger.info("🔍 Information absente détectée dans les documents. Recherche en ligne automatique...")
                t = translations.get(language, translations['en'])
                
                try:
                    # Effectuer une recherche en ligne
                    search_query = user_query
                    search_results = perform_online_search(search_query, language)
                    
                    if search_results and search_results != "Aucun résultat trouvé." and search_results != "Clé API manquante":
                        # Fusionner les résultats locaux avec les résultats en ligne
                        enrichment_prompt = (
                            f"{t.get('enrichment_title', '🌐 Enrichissement avec recherche en ligne')}\n\n"
                            f"**Réponse initiale basée sur les documents locaux:**\n{result}\n\n"
                            f"**Résultats de recherche en ligne:**\n{search_results}\n\n"
                            f"{t.get('enrichment_instructions', 'Instructions:')}\n"
                            f"- Combine intelligemment les informations des documents locaux avec les données trouvées en ligne.\n"
                            f"- Si l'information n'est pas dans les documents locaux mais est trouvée en ligne, utilise les données en ligne.\n"
                            f"- Distingue clairement les sources: indique ce qui vient des documents locaux vs. ce qui vient de la recherche en ligne.\n"
                            f"- Cite les sources en ligne si disponibles.\n"
                            f"- Garde la structure et le format de la réponse initiale si possible.\n"
                            f"- Priorise les informations récentes trouvées en ligne pour les données qui peuvent être obsolètes.\n\n"
                            f"**Réponse enrichie:**"
                        )
                        
                        enriched_result = await execute_model_query(enrichment_prompt, selected_model)
                        
                        # Ajouter une note indiquant que la recherche en ligne a été utilisée
                        result = (
                            f"{enriched_result}\n\n"
                            f"---\n"
                            f"💡 **Note**: Cette réponse combine les informations des documents locaux avec des données trouvées en ligne, "
                            f"car certaines informations n'étaient pas disponibles dans les documents fournis.\n"
                        )
                        
                        logger.info("✅ Réponse enrichie avec des données en ligne")
                    else:
                        logger.info("⚠️ Aucun résultat trouvé en ligne ou clé API manquante")
                        # Garder la réponse originale si la recherche en ligne n'a rien donné
                except Exception as search_error:
                    logger.warning(f"⚠️ Erreur lors de la recherche en ligne automatique: {str(search_error)}")
                    # En cas d'erreur, garder la réponse originale
                    pass
    except Exception as e:
        result = f"Erreur lors de l'analyse locale: {str(e)}"

    return result

async def execute_model_query(prompt: str, selected_model: str) -> str:
    """
    Exécute la requête sur le modèle sélectionné
    """
    try:
        if selected_model.lower() in ["gpt-3.5-turbo", "gpt-4o"]:
            result = call_openai_api(prompt, selected_model)
        elif selected_model.lower() in ["gpt-5", "gpt-5-mini", "gpt-5-nano"]:
            result = call_openai_api(prompt, selected_model)
        elif selected_model.lower() == "openai":
            result = call_openai_api(prompt, "openai")
        elif selected_model.lower() == "mistral":
            result = call_mistral_api(prompt)
        elif selected_model.lower() in OLLAMA_MODELS or selected_model.lower() == "llama3":
            result = call_ollama_api(prompt, selected_model)
        else:
            logger.warning(f"Modèle inconnu {selected_model}, utilisation du modèle par défaut {DEFAULT_MODEL}")
            result = call_openai_api(prompt, DEFAULT_MODEL)
        
        return result
    except Exception as e:
        raise e

async def detect_document_type(file_content: str, file_name: str) -> str:
    """
    Détecte le type de document (contrat, testament, acte notarié, lettre, etc.)
    """
    content_lower = file_content[:3000].lower()  # Augmenter la fenêtre d'analyse
    file_name_lower = file_name.lower()
    
    # Détection des lettres (doit être fait en premier pour éviter les faux positifs)
    letter_keywords = ['lettre', 'letter', 'correspondance', 'correspondence', 'courrier', 'mail']
    letter_context = ['soutien', 'support', 'recommandation', 'recommendation', 'demande', 'request', 
                     'attestation', 'certificate', 'certificat', 'justificatif', 'justification']
    
    if any(word in file_name_lower for word in letter_keywords) or \
       (any(word in content_lower[:500] for word in letter_keywords) and 
        any(word in content_lower for word in letter_context)):
        return 'lettre'
    
    # Détection des documents financiers/fiscaux
    financial_keywords = ['t4', 't-4', 'relevé', 'statement', 'payroll', 'paie', 'salaire', 'salary', 
                          'revenu', 'income', 'impôt', 'tax', 'déduction', 'deduction']
    if any(word in file_name_lower for word in financial_keywords) or \
       any(word in content_lower[:500] for word in financial_keywords):
        return 'document_financier'
    
    # Détection des contrats (doit être fait après les lettres)
    if any(word in content_lower or word in file_name_lower for word in ['contrat', 'contract', 'agreement']):
        if any(word in content_lower for word in ['location', 'rental', 'bail', 'loyer']):
            return 'contrat_location'
        elif any(word in content_lower for word in ['travail', 'employment', 'employé', 'employee']):
            return 'contrat_travail'
        elif any(word in content_lower for word in ['vente', 'sale', 'achat', 'purchase']):
            return 'contrat_vente'
        else:
            return 'contrat_generique'
    
    # Détection des testaments
    elif any(word in content_lower or word in file_name_lower for word in ['testament', 'will']):
        return 'testament'
    
    # Détection des actes notariés (doit être plus strict pour éviter les faux positifs)
    notary_keywords = ['acte notarié', 'notarial act', 'acte authentique', 'authentic act']
    notary_context = ['notaire', 'notary', 'étude notariale', 'notary office', 'minute', 
                     'authentification', 'authentification', 'signature authentique']
    
    # Un acte notarié doit contenir à la fois des mots-clés d'acte ET de notaire
    has_acte = any(word in content_lower or word in file_name_lower for word in ['acte', 'deed'])
    has_notary = any(word in content_lower for word in notary_context) or \
                 any(phrase in content_lower for phrase in notary_keywords)
    
    if has_acte and has_notary:
        return 'acte_notarie'
    elif any(word in content_lower or word in file_name_lower for word in ['bail', 'lease']):
        return 'bail'
    else:
        return 'document_generique'

async def extract_structured_data(file_content: str, file_name: str, document_type: str, 
                                  selected_model: str = DEFAULT_MODEL, language: str = 'fr') -> Dict[str, Any]:
    """
    Extrait les données structurées d'un document selon son type
    Retourne un dictionnaire JSON structuré
    """
    # Prompts spécialisés par type de document
    prompts = {
        'contrat_location': """Tu dois extraire toutes les informations structurées de ce contrat de location.
Retourne UNIQUEMENT un JSON valide avec cette structure exacte:
{
  "type_document": "Contrat de location",
  "parties": [
    {
      "nom": "nom complet",
      "role": "LOCATAIRE ou BAILLEUR",
      "adresse": "adresse complète",
      "telephone": "numéro si disponible",
      "email": "email si disponible"
    }
  ],
  "dates_importantes": [
    {
      "type": "Date de signature",
      "valeur": "date au format JJ/MM/AAAA"
    },
    {
      "type": "Date de début",
      "valeur": "date"
    },
    {
      "type": "Date de fin",
      "valeur": "date si disponible"
    },
    {
      "type": "Durée",
      "valeur": "durée (ex: 3 ans)"
    }
  ],
  "montants": [
    {
      "type": "Loyer mensuel",
      "valeur": nombre,
      "devise": "EUR"
    },
    {
      "type": "Caution",
      "valeur": nombre,
      "devise": "EUR"
    },
    {
      "type": "Charges",
      "valeur": nombre si disponible,
      "devise": "EUR"
    }
  ],
  "bien_loue": {
    "adresse": "adresse complète du bien",
    "superficie": "superficie si disponible",
    "type": "appartement, maison, etc."
  },
  "clauses_cles": [
    "liste des clauses importantes (renouvellement, indexation, etc.)"
  ],
  "conditions": [
    "conditions particulières mentionnées"
  ]
}
Extrait TOUTES les informations disponibles. Si une information n'est pas présente, utilise null ou omets le champ.""",

        'contrat_travail': """Tu dois extraire toutes les informations structurées de ce contrat de travail.
Retourne UNIQUEMENT un JSON valide avec cette structure exacte:
{
  "type_document": "Contrat de travail",
  "employeur": {
    "nom": "nom de l'entreprise",
    "adresse": "adresse complète",
    "siret": "SIRET si disponible"
  },
  "employe": {
    "nom": "nom complet",
    "adresse": "adresse complète",
    "poste": "intitulé du poste",
    "fonctions": "description des fonctions"
  },
  "dates_importantes": [
    {
      "type": "Date de signature",
      "valeur": "date"
    },
    {
      "type": "Date d'embauche",
      "valeur": "date"
    },
    {
      "type": "Période d'essai",
      "valeur": "durée"
    }
  ],
  "remuneration": {
    "salaire_brut_mensuel": nombre,
    "salaire_net_mensuel": nombre si disponible,
    "devise": "EUR",
    "avantages": ["liste des avantages"]
  },
  "duree": {
    "type": "CDI, CDD, etc.",
    "duree": "durée si CDD"
  },
  "clauses_cles": [
    "clause de non-concurrence si présente",
    "clause de confidentialité si présente",
    "autres clauses importantes"
  ]
}""",

        'testament': """Tu dois extraire toutes les informations structurées de ce testament.
Retourne UNIQUEMENT un JSON valide avec cette structure exacte:
{
  "type_document": "Testament",
  "testateur": {
    "nom": "nom complet",
    "adresse": "adresse complète",
    "date_naissance": "date si disponible"
  },
  "beneficiaires": [
    {
      "nom": "nom complet",
      "relation": "relation avec le testateur",
      "legs": "description du legs",
      "conditions": "conditions éventuelles"
    }
  ],
  "executeur_testamentaire": {
    "nom": "nom si mentionné",
    "fonctions": "fonctions"
  },
  "biens_legues": [
    {
      "description": "description du bien",
      "beneficiaire": "nom du bénéficiaire",
      "valeur_estimee": "valeur si mentionnée"
    }
  ],
  "dates_importantes": [
    {
      "type": "Date de rédaction",
      "valeur": "date"
    },
    {
      "type": "Date de signature",
      "valeur": "date"
    }
  ],
  "conditions_particulieres": [
    "conditions ou clauses particulières"
  ]
}""",

        'contrat_generique': """Tu dois extraire toutes les informations structurées de ce contrat.
Retourne UNIQUEMENT un JSON valide avec cette structure exacte:
{
  "type_document": "Contrat",
  "parties": [
    {
      "nom": "nom complet",
      "role": "rôle dans le contrat",
      "adresse": "adresse si disponible"
    }
  ],
  "objet": "objet du contrat en une phrase",
  "dates_importantes": [
    {
      "type": "type de date (signature, échéance, etc.)",
      "valeur": "date"
    }
  ],
  "montants": [
    {
      "type": "type de montant",
      "valeur": nombre,
      "devise": "EUR"
    }
  ],
  "clauses_cles": [
    "liste des clauses importantes"
  ],
  "obligations": [
    "obligations de chaque partie"
  ],
  "conditions": [
    "conditions particulières"
  ]
}""",

        'document_generique': """Tu dois extraire les informations structurées de ce document.
Retourne UNIQUEMENT un JSON valide avec cette structure:
{
  "type_document": "Type de document détecté",
  "parties_mentionnees": [
    {
      "nom": "nom",
      "role": "rôle si identifiable"
    }
  ],
  "dates_importantes": [
    {
      "type": "type de date",
      "valeur": "date"
    }
  ],
  "montants": [
    {
      "type": "type de montant",
      "valeur": nombre,
      "devise": "EUR"
    }
  ],
  "informations_cles": [
    "points clés du document"
  ]
}"""
    }
    
    # Sélectionner le prompt approprié
    prompt_template = prompts.get(document_type, prompts['document_generique'])
    
    # Construire le prompt final
    extraction_prompt = f"""{prompt_template}

DOCUMENT À ANALYSER:
Nom du fichier: {file_name}

Contenu:
{file_content[:8000]}

IMPORTANT: 
- Retourne UNIQUEMENT le JSON, sans texte avant ou après
- Le JSON DOIT être complet et valide (toutes les accolades et crochets doivent être fermés)
- Utilise des valeurs null pour les champs manquants
- Sois précis et exhaustif
- Extrais TOUTES les informations disponibles dans le document
- Assure-toi que le JSON est bien formé et complet avant de répondre"""
    
    try:
        # Appeler le modèle pour l'extraction avec une limite de tokens plus élevée (2000 tokens pour les JSON structurés)
        # On utilise directement call_openai_api avec max_tokens_override
        raw_response = call_openai_api(extraction_prompt, selected_model, max_retries=3, max_tokens_override=2000)
        
        # Nettoyer la réponse : enlever les markdown code blocks si présents
        cleaned_response = raw_response.strip()
        if cleaned_response.startswith('```json'):
            cleaned_response = cleaned_response[7:]  # Enlever ```json
        if cleaned_response.startswith('```'):
            cleaned_response = cleaned_response[3:]  # Enlever ```
        if cleaned_response.endswith('```'):
            cleaned_response = cleaned_response[:-3]  # Enlever ``` à la fin
        cleaned_response = cleaned_response.strip()
        
        # Fonction pour réparer un JSON incomplet
        def repair_json(json_str: str) -> str:
            """Tente de réparer un JSON incomplet en fermant les structures ouvertes et les chaînes"""
            json_str = json_str.strip()
            if not json_str.startswith('{'):
                return json_str
            
            result = json_str
            
            # Réparer les chaînes tronquées (ex: "devise": "E -> "devise": "EUR")
            # Chercher les guillemets non fermés à la fin
            # On cherche le dernier guillemet ouvrant qui n'est pas suivi d'un guillemet fermant avant la fin
            # Pattern: trouver "..." qui n'est pas fermé
            # On va simplement fermer les chaînes ouvertes à la fin
            lines = result.split('\n')
            if lines:
                last_line = lines[-1].strip()
                # Si la dernière ligne se termine par un guillemet ouvrant ou une chaîne incomplète
                if last_line.count('"') % 2 != 0:  # Nombre impair de guillemets = chaîne non fermée
                    # Trouver le dernier guillemet ouvrant
                    last_quote_pos = last_line.rfind('"')
                    if last_quote_pos >= 0:
                        # Vérifier s'il y a un guillemet fermant après
                        after_quote = last_line[last_quote_pos + 1:]
                        if '"' not in after_quote:
                            # La chaîne est tronquée, on la ferme avec une valeur par défaut ou null
                            # On va plutôt essayer de compléter intelligemment
                            # Pour l'instant, on ferme simplement la chaîne
                            if last_line.endswith('"'):
                                # Déjà un guillemet, on ajoute juste la fermeture
                                pass
                            else:
                                # Tronqué au milieu, on ferme avec null
                                # Trouver où commence la valeur
                                if ':' in last_line:
                                    key_part = last_line[:last_line.rfind(':') + 1]
                                    # Remplacer la valeur tronquée par null
                                    lines[-1] = key_part + ' null'
                                else:
                                    # Juste fermer la chaîne
                                    lines[-1] = last_line + '"'
                        result = '\n'.join(lines)
            
            # Compter les accolades et crochets ouverts
            open_braces = result.count('{')
            close_braces = result.count('}')
            open_brackets = result.count('[')
            close_brackets = result.count(']')
            
            # Fermer les structures ouvertes
            if open_braces > close_braces:
                # Fermer les objets
                for _ in range(open_braces - close_braces):
                    # Trouver la dernière virgule ou le dernier caractère et fermer
                    if result.rstrip().endswith(','):
                        result = result.rstrip()[:-1]  # Enlever la virgule
                    # Nettoyer les virgules avant de fermer
                    result = re.sub(r',(\s*)$', r'\1', result)
                    result += '\n}'
            
            if open_brackets > close_brackets:
                # Fermer les tableaux
                for _ in range(open_brackets - close_brackets):
                    if result.rstrip().endswith(','):
                        result = result.rstrip()[:-1]  # Enlever la virgule
                    # Nettoyer les virgules avant de fermer
                    result = re.sub(r',(\s*)$', r'\1', result)
                    result += '\n]'
            
            # Nettoyer les virgules finales avant les fermetures
            result = re.sub(r',(\s*[}\]])', r'\1', result)
            
            # Nettoyer les chaînes mal fermées restantes
            # Si on a encore des problèmes, on remplace les valeurs tronquées par null
            # Chercher les patterns comme "key": "incomplete_string (sans guillemet fermant)
            result = re.sub(r':\s*"([^"]*?)(?<!")\s*$', r': null', result, flags=re.MULTILINE)
            # Aussi pour les dernières lignes qui se terminent par une chaîne incomplète
            lines = result.split('\n')
            if lines:
                last_line = lines[-1].strip()
                # Si la ligne se termine par un guillemet ouvrant sans fermeture
                if last_line.count('"') % 2 != 0 and ':' in last_line:
                    # Extraire la clé et remplacer la valeur par null
                    key_match = re.search(r'(\s*"[^"]+"\s*):\s*"[^"]*$', last_line)
                    if key_match:
                        lines[-1] = key_match.group(1) + ': null'
                    result = '\n'.join(lines)
            
            return result
        
        # Extraire le JSON de la réponse
        json_match = re.search(r'\{.*', cleaned_response, re.DOTALL)
        if json_match:
            json_str = json_match.group()
            
            # Essayer de parser directement
            try:
                structured_data = json.loads(json_str)
            except json.JSONDecodeError:
                # Essayer de réparer le JSON
                logger.warning("⚠️ JSON incomplet détecté, tentative de réparation...")
                repaired_json = repair_json(json_str)
                try:
                    structured_data = json.loads(repaired_json)
                    logger.info("✅ JSON réparé avec succès")
                except json.JSONDecodeError as repair_error:
                    logger.error(f"❌ Impossible de réparer le JSON: {str(repair_error)}")
                    # Essayer d'extraire au moins les parties valides
                    try:
                        # Extraire juste le début du JSON jusqu'à la première erreur
                        # Trouver la position de l'erreur
                        error_pos = int(str(repair_error).split('char ')[1].split(')')[0]) if 'char' in str(repair_error) else len(json_str)
                        partial_json = json_str[:error_pos]
                        # Fermer proprement
                        partial_json = repair_json(partial_json)
                        structured_data = json.loads(partial_json)
                        logger.warning("⚠️ JSON partiel extrait (certaines données peuvent être manquantes)")
                    except:
                        raise repair_error
        else:
            # Essayer de parser directement
            structured_data = json.loads(cleaned_response)
        
        # Ajouter des métadonnées
        structured_data['metadata'] = {
            'file_name': file_name,
            'document_type': document_type,
            'extraction_date': datetime.utcnow().isoformat()
        }
        
        logger.info(f"✅ Extraction structurée réussie pour {file_name} (type: {document_type})")
        return structured_data
        
    except json.JSONDecodeError as e:
        logger.error(f"❌ Erreur de parsing JSON lors de l'extraction: {str(e)}")
        logger.error(f"Réponse brute (premiers 2000 caractères): {raw_response[:2000]}")
        logger.error(f"Longueur totale de la réponse: {len(raw_response)} caractères")
        # Retourner une structure minimale avec l'erreur
        return {
            "error": "Erreur lors de l'extraction des données structurées - JSON invalide ou incomplet",
            "error_details": str(e),
            "raw_response_preview": raw_response[:2000],
            "response_length": len(raw_response),
            "metadata": {
                "file_name": file_name,
                "document_type": document_type
            }
        }
    except Exception as e:
        logger.error(f"❌ Erreur lors de l'extraction structurée: {str(e)}")
        return {
            "error": f"Erreur lors de l'extraction: {str(e)}",
            "metadata": {
                "file_name": file_name,
                "document_type": document_type
            }
        }
    
async def analyze_query_need_for_search(user_query: str, selected_model: str, language: str = 'en') -> Dict:
    """
    Analyse si la query nécessite des informations actuelles
    Amélioré pour détecter les questions nécessitant des informations en temps réel
    """
    t = translations.get(language, translations['en'])
    
    # Détection rapide basée sur des mots-clés pour les questions en temps réel
    query_lower = user_query.lower()
    realtime_keywords = [
        "heure actuelle", "heure maintenant", "quelle heure", "what time", "current time", "time now",
        "prix actuel", "prix maintenant", "current price", "price now",
        "taux actuel", "current rate", "taux de change", "exchange rate",
        "cours actuel", "current rate",
        "maintenant", "now", "actuel", "current", "aujourd'hui", "today",
        "en ce moment", "right now", "à l'instant", "at the moment",
        "météo", "weather", "température", "temperature",
        "actualité", "news", "événements récents", "recent events"
    ]
    
    # Si la question contient des mots-clés de temps réel, déclencher directement la recherche
    needs_realtime = any(keyword in query_lower for keyword in realtime_keywords)
    
    if needs_realtime:
        logger.info(f"🔍 Question en temps réel détectée: {user_query[:50]}...")
        return {
            "needs_search": True,
            "reason": "Question nécessitant des informations en temps réel",
            "search_keywords": [user_query],
            "estimated_cutoff_relevance": "high"
        }
    
    needs_search_field = t['needs_search_field']
    reason_field = t['reason_field']
    search_keywords_field = t['search_keywords_field']
    cutoff_relevance_field = t['cutoff_relevance_field']
    
    analysis_prompt = (
        f"{t['analyze_query_prompt']}\n\n"
        f"{t['query_label']}: {user_query}\n\n"
        f"{t['json_response_format']}:\n"
        f"{{\n"
        f'  "{needs_search_field}": true/false,\n'
        f'  "{reason_field}": "{t["short_explanation"]}",\n'
        f'  "{search_keywords_field}": ["mot-clé1", "mot-clé2"] {t["keyword_or_null"]},\n'
        f'  "{cutoff_relevance_field}": "high/medium/low"\n'
        f"}}\n\n"
        f"{t['examples_need_search']}:\n"
        f"{t['current_prices_stocks']}\n"
        f"{t['recent_events_news']}\n"
        f"{t['new_software_versions']}\n"
        f"{t['recent_statistics_data']}\n"
        f"{t['recent_people_companies']}\n"
        f"- Questions sur l'heure actuelle dans un pays ou une ville\n"
        f"- Questions sur les prix actuels, taux de change, cours boursiers\n"
        f"- Questions sur la météo actuelle\n"
        f"- Questions sur les événements récents ou l'actualité\n\n"
        f"{t['examples_no_search']}:\n"
        f"{t['general_concepts']}\n"
        f"{t['programming_syntax']}\n"
        f"{t['history_facts']}\n"
        f"{t['math_science']}"
    )
    
    try:
        analysis_result = await execute_model_query(analysis_prompt, selected_model)
        # Nettoyer la réponse pour extraire le JSON
        json_match = re.search(r'\{.*\}', analysis_result, re.DOTALL)
        if json_match:
            analysis_data = json.loads(json_match.group())
            return analysis_data
        else:
            # Fallback si le JSON n'est pas parsable
            return {
                "needs_search": True,
                "reason": "Analyse automatique non concluante",
                "search_keywords": [user_query],
                "estimated_cutoff_relevance": "medium"
            }
    except Exception as e:
        logger.warning(f"Erreur lors de l'analyse de la query: {str(e)}")
        return {
            "needs_search": True,
            "reason": "Erreur d'analyse, recherche par sécurité",
            "search_keywords": [user_query],
            "estimated_cutoff_relevance": "medium"
        }
    
async def query_model_online_mode(user_query: str, selected_model: str = DEFAULT_MODEL, 
                                 language: str = 'en', enable_auto_online_search: bool = True) -> str:
    """
    Mode ONLINE: Réponse du modèle enrichie avec des données actuelles si nécessaire (comme SearchGPT)
    Avec recherche automatique si l'information n'est pas trouvée dans les connaissances du modèle
    """
    cache_key = f"online_query_{user_query}_{selected_model}_{language}"
    cached = await cache.get(cache_key)
    if cached:
        return cached

    t = translations.get(language, translations['en'])

    # ÉTAPE 1: Réponse initiale du modèle avec ses connaissances
    initial_prompt = (
        f"{t['online_mode_title']}\n"
        f"{t['recent_info_mention']}\n\n"
        f"{t['question']}: {user_query}\n\n"
        f"{t['online_instructions_title']}\n"
        f"{t['give_best_answer']}\n"
        f"{t['be_precise_dates']}\n"
        f"{t['mention_recent_useful']}\n\n"
        f"{t['emoji']}"
    )

    try:
        # Réponse initiale du modèle
        initial_response = await execute_model_query(initial_prompt, selected_model)
        
        # ÉTAPE 2: Analyse automatique du besoin de recherche
        search_analysis = await analyze_query_need_for_search(user_query, selected_model, language)
        
        logger.info(f"🔍 Analyse de recherche: {search_analysis}")
        
        # ÉTAPE 3: Recherche et enrichissement si nécessaire
        should_search = search_analysis.get("needs_search", False)
        
        # NOUVEAU: Vérifier aussi si la réponse indique que l'information n'est pas disponible
        if enable_auto_online_search and not should_search:
            missing_info = await detect_missing_information(initial_response, user_query, language)
            if missing_info:
                logger.info("🔍 Information absente détectée dans les connaissances du modèle. Recherche en ligne automatique...")
                should_search = True
        
        if should_search:
            logger.info("🌐 Enrichissement avec des données actuelles...")
            
            # Utiliser les mots-clés optimisés ou la query originale
            search_keywords = search_analysis.get("search_keywords", [user_query])
            search_query = " ".join(search_keywords) if isinstance(search_keywords, list) else user_query
            
            # Recherche en ligne
            try:
                search_results = perform_online_search(search_query, language)
                
                if search_results and search_results != "Aucun résultat trouvé." and search_results != "Clé API manquante":
                    # ÉTAPE 4: Fusion intelligente des informations avec formatage amélioré
                    enrichment_prompt = (
                        f"{t['enrichment_title']}\n\n"
                        f"{t['initial_response']}\n{initial_response}\n\n"
                        f"{t['new_info_found']}\n{search_results}\n\n"
                        f"{t['enrichment_instructions']}\n"
                        f"{t['combine_intelligently']}\n"
                        f"{t['update_obsolete']}\n"
                        f"{t['distinguish_info']}\n"
                        f"{t['cite_sources']}\n"
                        f"{t['keep_structure']}\n"
                        f"{t['prioritize_recent']}\n\n"
                        f"**FORMATAGE SPÉCIAL POUR CERTAINES RÉPONSES:**\n"
                        f"- Pour les questions sur l'heure: Réponds directement avec l'heure actuelle au format 'Il est XXhXX à [lieu]' ou 'It is XX:XX in [place]'\n"
                        f"- Pour les prix (cryptomonnaies, actions, devises): Formate comme une carte avec le prix en gras, le changement en pourcentage, et une description claire\n"
                        f"- Pour les taux de change: Affiche le taux actuel de manière claire et structurée\n"
                        f"- Pour la météo: Formate avec température, conditions, et lieu\n"
                        f"- Utilise des emojis appropriés (🕐 pour l'heure, 💰 pour les prix, 🌤️ pour la météo, etc.)\n"
                        f"- Sois concis et précis, va droit au but\n"
                        f"- Si les données de recherche sont claires, utilise-les directement sans trop d'explications\n\n"
                        f"{t['enriched_response']}"
                    )
                    
                    enriched_response = await execute_model_query(enrichment_prompt, selected_model)
                    
                    # Ajout des métadonnées de recherche
                    final_response = (
                        f"{enriched_response}\n\n"
                        f"---\n"
                        f"💡 **Informations enrichies**: Cette réponse combine mes connaissances de base "
                        f"avec des données récentes trouvées en ligne.\n \n"
                        f"🔍 **Model**: {selected_model}"
                    )
                else:
                    # Pas de résultats en ligne, garder la réponse initiale
                    logger.info("⚠️ Aucun résultat trouvé en ligne ou clé API manquante")
                    final_response = (
                        f"{initial_response}\n\n"
                        f"{t['separator']}\n"
                        f"{t['source_training']}"
                    )
            except Exception as search_error:
                logger.warning(f"⚠️ Erreur lors de la recherche en ligne: {str(search_error)}")
                # En cas d'erreur, garder la réponse initiale
                final_response = (
                    f"{initial_response}\n\n"
                    f"{t['separator']}\n"
                    f"{t['source_training']}"
                )
            
        else:
            logger.info("✅ Pas de recherche nécessaire, réponse basée sur les connaissances du modèle")
            final_response = (
                f"{initial_response}\n\n"
                f"{t['separator']}\n"
                f"{t['source_training']}"
            )

    except Exception as e:
        logger.error(f"Erreur lors du mode online: {str(e)}")
        final_response = f"Erreur lors du traitement en mode online: {str(e)}"

    await cache.set(cache_key, final_response, ttl=1800)
    return final_response

@app.route('/index-directory', methods=['POST'])
async def index_directory():
    """
    Indexe les fichiers d'un repertoire avec OpenAI embeddings
    """
    try:
        data = request.get_json()
        files = data.get('files', [])
        session_id = request.headers.get('Session-ID', 'default')
        language = data.get('language', 'en')

        if not files:
            return jsonify({
                "error": "Aucun fichier fourni pour l'indexation",
                'files_received': len(files)
            }), 400
        
        logger.info(f"📂 Indexation de {len(files)} fichiers pour la session {session_id}")
        documents = []
        for file_data in files:
            if not file_data.get('content') or not file_data.get('fileName'):
                logger.warning(f"Fichier ignoré (contenu ou nom manquant): {file_data.get('fileName', 'inconnu')}")
                continue

            documents.append(Document(
                page_content=file_data['content'],
                metadata={
                    'fileName': file_data['fileName'],
                    'file_size': len(file_data['content']),
                    'indexed_at': datetime.utcnow().isoformat()
                }
            ))
        if not documents:
            return jsonify({
                "error": "Aucun fichier valide à indexer",
                'files_processed':0
            }), 400
        
        logger.info(f"🗂️ {len(documents)} documents prêts pour l'indexation")

        # Diviser les documents en chunks avec stratégie améliorée pour préserver le contexte
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=2000,  # Augmenté pour préserver plus de contexte
            chunk_overlap=300,  # Plus de chevauchement pour préserver les phrases complètes
            length_function=len,
            separators=["\n\n\n", "\n\n", "\n", ". ", " ", ""]  # Meilleure préservation des paragraphes
        )
        split_docs = text_splitter.split_documents(documents)
        logger.info(f"✂️ Documents divisés en {len(split_docs)} chunks (chunk_size=2000, overlap=300)")
        
        # Vérifier la clé OpenAI
        openai_api_key = os.getenv('OPENAI_API_KEY')
        if not openai_api_key:
            return jsonify({
                'error': 'Clé API OpenAI non configurée sur le serveur',
                'suggestion': 'Contactez l\'administrateur pour configurer OPENAI_API_KEY'
            }), 500
        
        # Créer les embeddings avec un modèle plus récent et performant
        logger.info("🧠 Création des embeddings avec OpenAI...")
        # Utiliser text-embedding-3-small ou text-embedding-ada-002 selon disponibilité
        try:
            # Essayer d'abord le modèle plus récent (meilleure qualité sémantique)
            embeddings = OpenAIEmbeddings(
                api_key=openai_api_key,
                model="text-embedding-3-small"  # Plus performant que ada-002
            )
            logger.info("✅ Utilisation de text-embedding-3-small pour meilleure qualité sémantique")
        except Exception as e:
            logger.warning(f"text-embedding-3-small non disponible, fallback vers ada-002: {str(e)}")
        embeddings = OpenAIEmbeddings(
            api_key=openai_api_key,
            model="text-embedding-ada-002"
        )
        
        # Test rapide de l'API
        try:
            test_embedding = await embeddings.aembed_query("test")
            logger.info(f"✅ API OpenAI fonctionnelle, dimension: {len(test_embedding)}")
        except Exception as e:
            logger.error(f"❌ Erreur de test API OpenAI: {str(e)}")
            return jsonify({
                'error': f'Erreur API OpenAI: {str(e)}',
                'suggestion': 'Vérifiez votre clé API et votre quota'
            }), 500
        
        # Inférer des actions suggérées pour ce corpus
        logger.info("🧠 Inférence des actions suggérées pour le corpus...")
        language = data.get('language', 'en')
        inferred_actions = await infer_corpus_actions(split_docs, language=language)
        
        # Créer le vector store
        logger.info("🗃️ Création du vector store...")
        vector_store = await FAISS.afrom_documents(split_docs, embeddings)
        
        # Stocker le vector store et les actions pour cette session
        vector_stores[session_id] = {
            'store': vector_store,
            'created_at': datetime.utcnow().isoformat(),
            'files_count': len(files),
            'chunks_count': len(split_docs),
            'files_indexed': [f['fileName'] for f in files],
            'auto_actions': inferred_actions
        }
        
        logger.info(f"✅ Indexation terminée pour la session {session_id}")
        
        return jsonify({
            'success': True,
            'session_id': session_id,
            'indexed_files_count': len(files),
            'chunks_count': len(split_docs),
            'files_indexed': [f['fileName'] for f in files],
            'vector_store_ready': True,
            'suggested_actions': inferred_actions.get('suggested_actions', []),
            'corpus_domain': inferred_actions.get('domain', 'unknown')
        }), 200
        
    except Exception as e:
        logger.error(f"❌ Erreur lors de l'indexation: {str(e)}")
        return jsonify({
            'error': f'Erreur lors de l\'indexation: {str(e)}',
            'success': False
        }), 500


@app.route('/query', methods=['POST'])
async def handle_query():
    """
    Route de requête améliorée avec support des modes local et online
    """
    data = request.get_json()
    
    # Extraction des paramètres
    user_query = data.get('user_query')
    research_mode = data.get('research_mode', 'local')
    selected_model = data.get('selected_model', DEFAULT_MODEL)
    language = data.get('language', 'en')
    session_id = request.headers.get('Session-ID', 'default')  # NOUVEAU: récupérer session ID
    conversation_history = data.get('conversation_history', [])
    
    # Paramètres de contrôle des modes
    disable_online_search = data.get('disable_online_search', False)
    enable_online_search = data.get('enable_online_search', False)
    use_backend_vectorstore = data.get('use_backend_vectorstore', False)  # NOUVEAU
    
    # Validation des paramètres essentiels
    if not user_query:
        return jsonify({"error": "user_query est requis"}), 400
    
    # Validation et nettoyage du modèle
    if selected_model not in MODEL_CONFIG:
        logger.warning(f"Modèle inconnu {selected_model}, utilisation du modèle par défaut {DEFAULT_MODEL}")
        selected_model = DEFAULT_MODEL
    
    try:
        # Détermination du mode effectif
        effective_mode = research_mode
        
        # MODE LOCAL
        if effective_mode == 'local' or disable_online_search:
            logger.info(f"🔒 Mode LOCAL activé pour la requête: {user_query[:50]}...")
            
            # Validation des paramètres pour le mode local
            file_name = data.get('file_name')
            file_content = data.get('file_content', '')
            directory_content = data.get('directory_content', [])
            repo_structure = data.get('repo_structure', '')
            is_binary = data.get('is_binary', False)
            
            if not file_name:
                return jsonify({
                    "error": "Mode local nécessite un file_name",
                    "mode": "local",
                    "suggestion": "Sélectionnez un fichier ou utilisez le mode online"
                }), 400
            
            # NOUVELLE LOGIQUE: Recherche sémantique améliorée avec recherche hybride (sémantique + mots-clés)
            relevant_docs = []
            if use_backend_vectorstore and session_id in vector_stores:
                try:
                    session_store = vector_stores[session_id]
                    session_vector_store = session_store['store']
                    
                    logger.info(f"🔍 Recherche sémantique améliorée dans le vector store de la session {session_id}")
                    
                    # RECHERCHE 1: Sémantique pure (similarité vectorielle)
                    search_results_with_scores = session_vector_store.similarity_search_with_score(
                        user_query, 
                        k=20  # Récupère 20 candidats pour avoir plus de contexte
                    )
                    
                    # RECHERCHE 2: Recherche par mots-clés ET par nom de fichier (CRITIQUE pour capturer les noms propres)
                    # Extraire les mots-clés importants de la requête (y compris les noms propres courts)
                    query_keywords = set()
                    query_lower = user_query.lower()
                    # Ajouter tous les mots significatifs (plus de 2 caractères pour capturer "karim", "live", etc.)
                    for word in user_query.split():
                        clean_word = word.strip('.,!?;:()[]{}"\'').lower()
                        if len(clean_word) > 2:  # Réduit à 2 pour capturer "karim", "live", etc.
                            query_keywords.add(clean_word)
                    
                    logger.info(f"🔑 Mots-clés extraits de la requête: {query_keywords}")
                    
                    # RECHERCHE 3: Recherche explicite par nom de fichier (TRÈS IMPORTANT)
                    # Si la requête contient un nom (comme "karim"), forcer la récupération de tous les fichiers contenant ce nom
                    filename_matches = []
                    try:
                        # Méthode 1: Recherche avec une requête très large pour récupérer beaucoup de documents
                        all_docs_from_store = session_vector_store.similarity_search("document file content", k=1000)
                        
                        # Méthode 2: Si on peut accéder au docstore directement, l'utiliser (plus fiable)
                        if hasattr(session_vector_store, 'docstore') and hasattr(session_vector_store.docstore, '_dict'):
                            all_docs_dict = session_vector_store.docstore._dict
                            logger.info(f"📦 Accès direct au docstore: {len(all_docs_dict)} documents disponibles")
                            # Convertir les valeurs du dict en documents
                            all_docs_from_store = list(all_docs_dict.values()) if all_docs_dict else all_docs_from_store
                        
                        logger.info(f"🔍 Recherche dans {len(all_docs_from_store)} documents pour correspondance de nom")
                        
                        # Filtrer par nom de fichier si la requête contient des mots-clés
                        for doc in all_docs_from_store:
                            file_name_from_meta = (doc.metadata.get("fileName") or doc.metadata.get("file_name") or "").lower()
                            # Si le nom du fichier contient un mot-clé de la requête, l'inclure FORCÉMENT
                            for keyword in query_keywords:
                                if keyword in file_name_from_meta:
                                    filename_matches.append(doc)
                                    logger.info(f"📁 Fichier correspondant trouvé par nom: {doc.metadata.get('fileName', 'N/A')} (mot-clé: '{keyword}')")
                                    break  # Ne pas ajouter plusieurs fois le même document
                        
                        logger.info(f"📂 {len(filename_matches)} fichiers trouvés par correspondance de nom de fichier")
                    except Exception as e:
                        logger.warning(f"Erreur lors de la recherche par nom de fichier: {str(e)}")
                    
                    # Recherche par mots-clés dans le contenu
                    keyword_matches = []
                    all_docs_in_store = session_vector_store.docstore._dict if hasattr(session_vector_store, 'docstore') else {}
                    
                    # Si on peut accéder aux documents, chercher par mots-clés dans le contenu
                    try:
                        # Utiliser similarity_search avec la requête originale pour récupérer plus de variété
                        keyword_results = session_vector_store.similarity_search(
                            user_query,
                            k=15
                        )
                        # Combiner avec les résultats sémantiques
                        all_candidate_docs = {}
                        for doc, score in search_results_with_scores:
                            doc_id = id(doc)  # Utiliser l'ID du document comme clé
                            if doc_id not in all_candidate_docs:
                                all_candidate_docs[doc_id] = (doc, 1 - score)  # Score de similarité
                        
                        for doc in keyword_results:
                            doc_id = id(doc)
                            if doc_id not in all_candidate_docs:
                                all_candidate_docs[doc_id] = (doc, 0.5)  # Score moyen pour résultats mots-clés
                            else:
                                # Augmenter le score si trouvé par les deux méthodes
                                doc_obj, current_score = all_candidate_docs[doc_id]
                                all_candidate_docs[doc_id] = (doc_obj, min(current_score + 0.2, 1.0))
                        
                        # AJOUT CRITIQUE: Forcer l'inclusion des fichiers trouvés par nom (score élevé)
                        for doc in filename_matches:
                            doc_id = id(doc)
                            if doc_id not in all_candidate_docs:
                                # Score très élevé pour les fichiers trouvés par nom (priorité maximale)
                                all_candidate_docs[doc_id] = (doc, 0.95)
                                logger.info(f"⭐ Fichier ajouté avec priorité haute: {doc.metadata.get('fileName', 'N/A')}")
                            else:
                                # Augmenter encore plus le score si déjà présent
                                doc_obj, current_score = all_candidate_docs[doc_id]
                                all_candidate_docs[doc_id] = (doc_obj, min(current_score + 0.3, 1.0))
                                logger.info(f"⬆️ Score augmenté pour fichier par nom: {doc.metadata.get('fileName', 'N/A')}")
                        
                        combined_docs = list(all_candidate_docs.values())
                    except Exception as e:
                        logger.warning(f"Recherche hybride partielle: {str(e)}")
                        combined_docs = [(doc, 1 - distance) for doc, distance in search_results_with_scores]
                        # Ajouter quand même les fichiers trouvés par nom
                        for doc in filename_matches:
                            combined_docs.append((doc, 0.95))
                    
                    # DÉTECTION DES NOMS DE PERSONNES dans la requête ET l'historique (pour les pronoms)
                    person_names = set()
                    words = user_query.split()
                    
                    # Détecter les pronoms et chercher le nom dans l'historique
                    query_lower = user_query.lower()
                    has_pronoun = any(pronoun in query_lower for pronoun in ['he', 'she', 'his', 'her', 'him', 'they', 'their'])
                    
                    if has_pronoun and conversation_history:
                        # Chercher le dernier nom mentionné dans l'historique
                        for turn in reversed(conversation_history):
                            content = (turn.get("content") or "").lower()
                            # Chercher les noms dans l'historique
                            for name in ['karim', 'dominique', 'essome', 'ngami']:
                                if name in content:
                                    person_names.add(name)
                                    logger.info(f"👤 Nom détecté depuis l'historique (pronoun détecté): {name}")
                                    break
                            if person_names:
                                break
                    
                    # Détecter les noms dans la requête actuelle
                    for i, word in enumerate(words):
                        clean_word = word.strip('.,!?;:()[]{}"\'').strip()
                        if clean_word and clean_word[0].isupper() and len(clean_word) > 2:
                            person_names.add(clean_word.lower())
                        if i > 0 and words[i-1].lower() in ['his', 'her', 'their', 'karim', 'dominique', 'about', 'for']:
                            if len(clean_word) > 2:
                                person_names.add(clean_word.lower())
                    
                    common_names = ['karim', 'dominique', 'essome', 'ngami']
                    for name in common_names:
                        if name in query_lower:
                            person_names.add(name)
                    
                    logger.info(f"👤 Noms de personnes détectés (requête + historique): {person_names}")
                    
                    # Filtrer par score de similarité (seuil très réduit pour récupérer le maximum de documents)
                    # ET rechercher par mots-clés pour capturer les documents contenant les termes de la requête
                    filtered_docs = []
                    query_words = [w.strip('.,!?;:()[]{}"\'').lower() for w in user_query.split() if len(w.strip('.,!?;:()[]{}"\'')) > 2]
                    
                    # Liste des noms de personnes connus pour exclusion
                    known_person_names = {
                        'karim': ['dominique', 'essome'],
                        'dominique': ['karim', 'ngami'],
                        'essome': ['karim', 'ngami'],
                        'ngami': ['dominique', 'essome']
                    }
                    
                    # Déterminer les noms à exclure
                    names_to_exclude = set()
                    for detected_name in person_names:
                        if detected_name in known_person_names:
                            names_to_exclude.update(known_person_names[detected_name])
                    
                    logger.info(f"🚫 Noms à exclure (autres personnes): {names_to_exclude}")
                    
                    # Créer un set des IDs des fichiers trouvés par nom pour vérification rapide
                    filename_match_ids = {id(doc) for doc in filename_matches}
                    
                    for doc, similarity_score in combined_docs:
                        doc_id = id(doc)
                        doc_content_lower = doc.page_content[:500].lower()  # Vérifier dans le début du contenu
                        file_name_lower = (doc.metadata.get("fileName") or doc.metadata.get("file_name") or "").lower()
                        
                        # EXCLUSION STRICTE: Si un nom de personne est détecté, exclure les fichiers d'autres personnes
                        should_exclude = False
                        if person_names:
                            # RÈGLE 1: Exclure TOUJOURS les fichiers contenant un nom à exclure (même avec score élevé)
                            for exclude_name in names_to_exclude:
                                if exclude_name in file_name_lower:
                                    should_exclude = True
                                    logger.info(f"❌ Fichier EXCLU (nom de fichier contient '{exclude_name}'): {doc.metadata.get('fileName', 'N/A')}")
                                    break
                                # Vérifier aussi dans le contenu (premiers 200 caractères pour être plus strict)
                                if exclude_name in doc_content_lower[:200]:
                                    should_exclude = True
                                    logger.info(f"❌ Fichier EXCLU (contenu contient '{exclude_name}'): {doc.metadata.get('fileName', 'N/A')}")
                                    break
                            
                            # RÈGLE 2: Si un nom de personne est détecté, ne garder QUE les fichiers qui contiennent ce nom
                            if not should_exclude:
                                file_contains_person_name = any(name in file_name_lower for name in person_names)
                                # Vérifier aussi dans le contenu si pas dans le nom
                                if not file_contains_person_name:
                                    file_contains_person_name = any(name in doc_content_lower[:300] for name in person_names)
                                
                                if not file_contains_person_name:
                                    # Si aucun nom de personne n'est dans le fichier, EXCLURE TOUJOURS (même avec score élevé)
                                    should_exclude = True
                                    logger.info(f"⚠️ Fichier EXCLU (ne contient AUCUN nom de la personne recherchée): {doc.metadata.get('fileName', 'N/A')}")
                        
                        if should_exclude:
                            continue  # Exclure ce document
                        
                        # Vérifier si le document contient des mots-clés de la requête dans le contenu
                        keyword_matches = sum(1 for word in query_words if word in doc_content_lower)
                        # Vérifier aussi dans le nom de fichier
                        filename_keyword_matches = sum(1 for word in query_words if word in file_name_lower)
                        
                        keyword_bonus = min(keyword_matches * 0.15, 0.4)  # Bonus jusqu'à 0.4 pour correspondances de mots-clés
                        filename_bonus = min(filename_keyword_matches * 0.25, 0.5)  # Bonus encore plus élevé pour correspondance dans le nom
                        adjusted_score = similarity_score + keyword_bonus + filename_bonus
                        
                        # CRITIQUE: Toujours inclure les fichiers trouvés par nom, même avec score bas
                        # OU si score ajusté >= 0.45 OU si contient au moins 2 mots-clés
                        if doc_id in filename_match_ids:
                            # Bonus supplémentaire si le fichier contient le nom de la personne détectée
                            person_name_bonus = 0.0
                            if person_names:
                                for name in person_names:
                                    if name in file_name_lower:
                                        person_name_bonus = 0.15
                                        break
                            filtered_docs.append((doc, max(adjusted_score, 0.9) + person_name_bonus))
                            logger.info(f"✅ Fichier inclus (correspond au nom): {doc.metadata.get('fileName', 'N/A')}")
                        elif adjusted_score >= 0.45 or keyword_matches >= 2 or filename_keyword_matches >= 1:
                            filtered_docs.append((doc, adjusted_score))
                    
                    # Trier par score décroissant
                    filtered_docs.sort(key=lambda x: x[1], reverse=True)
                    
                    # AMÉLIORATION: Augmenter le nombre de documents récupérés pour améliorer la précision
                    # Si un nom de personne est détecté, limiter aux top 20 fichiers les plus pertinents
                    # Sinon, prendre jusqu'à 30 documents pour avoir plus de contexte
                    max_docs = 20 if person_names else 30
                    top_docs = [doc for doc, score in filtered_docs[:max_docs]]
                    
                    logger.info(f"📊 {len(top_docs)} documents finaux sélectionnés après filtrage strict par nom")
                    
                    logger.info(f"📊 Recherche hybride: {len(search_results_with_scores)} sémantiques + {len(keyword_results) if 'keyword_results' in locals() else 0} mots-clés → {len(filtered_docs)} pertinents (score≥0.55) → {len(top_docs)} sélectionnés")
                    
                    # Re-ranking avec le LLM pour affiner la pertinence
                    if len(top_docs) > 5:
                        try:
                            reranked_docs = await rerank_documents_with_llm(
                                user_query, 
                                top_docs, 
                                selected_model
                            )
                            relevant_docs = reranked_docs[:12]  # Top 12 après re-ranking (augmenté)
                            logger.info(f"🎯 Re-ranking LLM: {len(relevant_docs)} documents finaux sélectionnés")
                        except Exception as rerank_error:
                            logger.warning(f"Re-ranking échoué, utilisation des résultats initiaux: {str(rerank_error)}")
                            relevant_docs = top_docs[:12]
                    else:
                        relevant_docs = top_docs
                    
                    # Ajout des documents pertinents au contexte avec métadonnées enrichies
                    # Éviter les doublons en utilisant un set de file_name + début du contenu
                    seen_docs = set()
                    for doc in relevant_docs:
                        file_name_from_meta = doc.metadata.get("fileName") or doc.metadata.get("file_name") or "document_vectorstore"
                        content_preview = doc.page_content[:100]  # Premier 100 chars pour détecter les doublons
                        doc_key = f"{file_name_from_meta}:{content_preview}"
                        
                        if doc_key not in seen_docs:
                            seen_docs.add(doc_key)
                        directory_content.append({ 
                                "fileName": file_name_from_meta, 
                                "content": doc.page_content[:2500]  # Augmenté à 2500 chars par chunk
                        })
                    
                    logger.info(f"📚 {len(seen_docs)} documents uniques ajoutés depuis le vector store de session")
                    
                except Exception as e:
                    logger.warning(f"Erreur lors de la récupération depuis le vector store: {str(e)}")
            
            elif use_backend_vectorstore:
                logger.warning(f"Vector store demandé mais non trouvé pour la session {session_id}")
            
            # ANCIENNE LOGIQUE: Utiliser le vector store global (fallback)
            elif vector_store and user_query:
                try:
                    logger.info(f"🔍 Recherche sémantique améliorée dans le vector store global")
                    search_results_with_scores = vector_store.similarity_search_with_score(
                        user_query, 
                        k=15
                    )
                    
                    filtered_docs = []
                    for doc, distance in search_results_with_scores:
                        similarity_score = 1 - distance
                        if similarity_score >= 0.65:
                            filtered_docs.append((doc, similarity_score))
                    
                    filtered_docs.sort(key=lambda x: x[1], reverse=True)
                    top_docs = [doc for doc, score in filtered_docs[:10]]
                    
                    if len(top_docs) > 5:
                        try:
                            reranked_docs = await rerank_documents_with_llm(
                                user_query, 
                                top_docs, 
                                selected_model
                            )
                            relevant_docs = reranked_docs[:8]
                        except Exception as rerank_error:
                            logger.warning(f"Re-ranking échoué: {str(rerank_error)}")
                            relevant_docs = top_docs[:8]
                    else:
                        relevant_docs = top_docs
                    
                    for doc in relevant_docs:
                        directory_content.append({ 
                            "fileName": doc.metadata.get("file_name", "document_vectorstore"), 
                            "content": doc.page_content[:2000]
                        })
                    logger.info(f"📚 {len(relevant_docs)} documents ajoutés depuis le vector store global")
                except Exception as e:
                    logger.warning(f"Erreur lors de la récupération depuis le vector store global: {str(e)}")
            
            # Exécution de la requête en mode local - recherche en ligne DÉSACTIVÉE par défaut
            enable_auto_search = data.get('enable_auto_online_search', False)  # Désactivé par défaut en mode local
            response = await query_model_local_mode(
                file_name=file_name,
                file_content=file_content,
                directory_content=directory_content,
                repo_structure=repo_structure,
                user_query=user_query,
                is_binary=is_binary,
                selected_model=selected_model,
                language=language,
                conversation_history=conversation_history,
                enable_auto_online_search=enable_auto_search
            )
            
            return jsonify({
                "response": response,
                "mode": "local",
                "model_used": selected_model,
                "model_config": MODEL_CONFIG.get(selected_model, {}),
                "context_info": {
                    "file_name": file_name,
                    "directory_files_count": len(directory_content),
                    "vector_store_docs": len(relevant_docs),
                    "is_binary": is_binary,
                    "session_id": session_id,
                    "used_backend_vectorstore": use_backend_vectorstore
                }
            }), 200
        
        # MODE ONLINE avec recherche automatique si l'info n'est pas trouvée
        elif effective_mode == 'online' or enable_online_search:
            logger.info(f"🌐 Mode ONLINE activé pour la requête: {user_query[:50]}...")
            
            enable_auto_search = data.get('enable_auto_online_search', True)  # Activé par défaut
            response = await query_model_online_mode(
                user_query=user_query,
                selected_model=selected_model,
                language=language,
                enable_auto_online_search=enable_auto_search
            )
            
            return jsonify({
                "response": response,
                "mode": "online",
                "model_used": selected_model,
                "model_config": MODEL_CONFIG.get(selected_model, {}),
                "search_info": {
                    "query": user_query,
                    "language": language,
                    "search_performed": "intelligent_enrichment",
                    "approach": "searchgpt_style"
                }
            }), 200
        
        else:
            return jsonify({
                "error": f"Mode de recherche non supporté: {effective_mode}",
                "supported_modes": ["local", "online"]
            }), 400
            
    except Exception as e:
        logger.error(f"Erreur lors du traitement de la requête: {str(e)}")
        return jsonify({
            "error": f"Erreur lors du traitement: {str(e)}",
            "mode": effective_mode,
            "model_used": selected_model
        }), 500

@app.route('/query-stream', methods=['POST'])
def handle_query_stream():
    """
    Version streaming de la route query pour réponses en temps réel
    """
    data = request.get_json()
    
    # Récupérer les paramètres
    user_query = data.get('user_query')
    research_mode = data.get('research_mode', 'local')
    selected_model = data.get('selected_model', DEFAULT_MODEL)
    language = data.get('language', 'en')
    session_id = request.headers.get('Session-ID', 'default')
    
    if not user_query:
        return jsonify({"error": "user_query est requis"}), 400
    
    # Validation du modèle
    if selected_model not in MODEL_CONFIG:
        logger.warning(f"Unknown model {selected_model}, using default {DEFAULT_MODEL}")
        selected_model = DEFAULT_MODEL
    
    logger.info(f"🚀 Streaming request - Model: {selected_model}, Mode: {research_mode}")
    
    try:
        # MODE ONLINE
        if research_mode == 'online' or data.get('enable_online_search'):
            t = translations.get(language, translations['en'])
            
            prompt = (
                f"{t['online_mode_title']}\n"
                f"{t['recent_info_mention']}\n\n"
                f"{t['question']}: {user_query}\n\n"
                f"{t['online_instructions_title']}\n"
                f"{t['give_best_answer']}\n"
                f"{t['be_precise_dates']}\n"
                f"{t['mention_recent_useful']}\n\n"
                f"{t['emoji']}"
            )
            
            return Response(
                stream_with_context(stream_response(prompt, selected_model)),
                mimetype='text/event-stream',
                headers={
                    'Cache-Control': 'no-cache',
                    'Connection': 'keep-alive',
                    'X-Accel-Buffering': 'no'
                }
            )
        
        # MODE LOCAL
        elif research_mode == 'local':
            file_name = data.get('file_name')
            file_content = data.get('file_content', '')
            directory_content = data.get('directory_content', [])
            repo_structure = data.get('repo_structure', '')
            use_backend_vectorstore = data.get('use_backend_vectorstore', False)
            conversation_history = data.get('conversation_history', [])
            
            if not file_name:
                return jsonify({"error": "Mode local nécessite un file_name"}), 400
            
            # Si le vector store backend est disponible, utiliser la recherche sémantique améliorée
            if use_backend_vectorstore and session_id in vector_stores:
                try:
                    session_store = vector_stores[session_id]
                    session_vector_store = session_store['store']
                    
                    # Utiliser la fonction helper synchrone pour la recherche sémantique (avec historique pour détecter les pronoms)
                    directory_content = search_semantic_documents_sync(session_vector_store, user_query, session_id, conversation_history)
                    logger.info(f"✅ {len(directory_content)} documents récupérés par recherche sémantique pour le streaming")
                except Exception as e:
                    logger.warning(f"Erreur lors de la recherche sémantique en streaming: {str(e)}")
            
            t = translations.get(language, translations['en'])
            
            # Construire le prompt local avec query_model_local_mode pour avoir le même prompt amélioré
            import asyncio
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                enable_auto_search = data.get('enable_auto_online_search', False)  # Désactivé par défaut en mode local
                prompt = loop.run_until_complete(
                    query_model_local_mode(
                        file_name, file_content, directory_content, repo_structure,
                        user_query, False, selected_model, language, conversation_history,
                        enable_auto_online_search=enable_auto_search
                    )
                )
                loop.close()
            except Exception as e:
                logger.warning(f"Erreur lors de la construction du prompt amélioré: {str(e)}")
                # Fallback vers l'ancien prompt
            directory_content_summary = ' '.join(
                [f"{t['other_file']}: {doc['fileName']} : {doc['content']}" 
                 for doc in directory_content]
            ) if directory_content else t['no_other_files']
            
            prompt = (
                f"{t['local_analysis_mode']}\n"
                f"{t['no_external_search']}\n\n"
                f"{t['project_structure']}:\n{repo_structure}\n\n"
                f"{t['main_file']}: {file_name}\n\n"
                f"{t['file_content']}:\n{file_content}\n\n"
                f"{t['directory_context']}:\n{directory_content_summary}\n\n"
                f"{t['question']}: {user_query}\n\n"
                f"{t['instructions']}:\n"
                f"{t['base_response_only']}\n"
                f"{t['missing_info_clarify']}\n"
                f"{t['no_speculation']}\n"
                f"{t['focus_local_analysis']}\n\n"
                f"{t['emoji']}"
            )
            
            return Response(
                stream_with_context(stream_response(prompt, selected_model)),
                mimetype='text/event-stream',
                headers={
                    'Cache-Control': 'no-cache',
                    'Connection': 'keep-alive',
                    'X-Accel-Buffering': 'no'
                }
            )
        
        else:
            return jsonify({"error": f"Mode non supporté: {research_mode}"}), 400
            
    except Exception as e:
        logger.error(f"Erreur dans handle_query_stream: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route('/vector-store-status', methods=['GET'])
async def get_vector_store_status():
    """
    Endpoint pour vérifier le statut des vector stores
    """
    session_id = request.headers.get('Session-ID', 'default')
    
    return jsonify({
        'session_id': session_id,
        'session_has_vectorstore': session_id in vector_stores,
        'global_vectorstore_exists': vector_store is not None,
        'total_sessions': len(vector_stores),
        'session_info': vector_stores.get(session_id, {}).get('files_indexed', []) if session_id in vector_stores else None
    }), 200

@app.route('/extract-structured', methods=['POST'])
async def extract_structured():
    """
    Endpoint pour extraire les données structurées d'un document
    Utilisé pour les avocats/notaires pour extraire automatiquement les informations importantes
    """
    try:
        data = request.get_json()
        
        # Validation des paramètres
        file_name = data.get('file_name')
        file_content = data.get('file_content', '')
        selected_model = data.get('selected_model', DEFAULT_MODEL)
        language = data.get('language', 'fr')
        
        if not file_name:
            return jsonify({
                "error": "file_name est requis",
                "success": False
            }), 400
        
        if not file_content:
            return jsonify({
                "error": "file_content est requis",
                "success": False
            }), 400
        
        # Validation du modèle
        if selected_model not in MODEL_CONFIG:
            logger.warning(f"Modèle inconnu {selected_model}, utilisation du modèle par défaut {DEFAULT_MODEL}")
            selected_model = DEFAULT_MODEL
        
        logger.info(f"📋 Extraction structurée demandée pour: {file_name}")
        
        # Détecter le type de document
        document_type = await detect_document_type(file_content, file_name)
        logger.info(f"🔍 Type de document détecté: {document_type}")
        
        # Extraire les données structurées
        structured_data = await extract_structured_data(
            file_content, 
            file_name, 
            document_type, 
            selected_model, 
            language
        )
        
        if "error" in structured_data:
            return jsonify({
                "success": False,
                "error": structured_data.get("error"),
                "data": structured_data
            }), 500
        
        return jsonify({
            "success": True,
            "data": structured_data,
            "document_type": document_type,
            "file_name": file_name
        }), 200
        
    except Exception as e:
        logger.error(f"❌ Erreur lors de l'extraction structurée: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"Erreur lors de l'extraction: {str(e)}"
        }), 500

@app.route('/summarize_file_stream', methods=['POST'])
def summarize_file_stream():
    """Génère un résumé d'un fichier avec streaming (4 lignes max)"""
    try:
        data = request.get_json()
        file_name = data.get('file_name', '')
        file_content = data.get('file_content', '')
        language = data.get('language', 'fr')
        
        if not file_content:
            return jsonify({"error": "Aucun contenu fourni"}), 400
        
        # Utiliser Mistral pour générer le résumé
        client = OpenAI(base_url="https://api.mistral.ai/v1", api_key=os.getenv("MISTRAL_API_KEY"))
        
        prompt = f"""Génère un résumé concis du document suivant en exactement 4 lignes maximum. 
Le résumé doit être en {language} et mettre en évidence les informations clés.

Document: {file_name}
Contenu:
{file_content[:2000]}

Résumé (4 lignes max):"""
        
        def generate():
            try:
                stream = client.chat.completions.create(
                    model="mistral-small",
                    messages=[
                        {"role": "system", "content": f"Tu es un assistant expert en analyse de documents. Génère des résumés clairs et concis en exactement 4 lignes maximum en {language}."},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=200,
                    temperature=0.3,
                    stream=True
                )
                
                accumulated_text = ""
                line_count = 0
                
                for chunk in stream:
                    if chunk.choices[0].delta.content:
                        content = chunk.choices[0].delta.content
                        accumulated_text += content
                        
                        # Compter les lignes
                        current_lines = accumulated_text.split('\n')
                        if len(current_lines) > 4:
                            # Limiter à 4 lignes
                            accumulated_text = '\n'.join(current_lines[:4])
                            yield f"data: {json.dumps({'content': content, 'done': False})}\n\n"
                            yield f"data: {json.dumps({'done': True})}\n\n"
                            return
                        
                        yield f"data: {json.dumps({'content': content, 'done': False})}\n\n"
                
                # Limiter à 4 lignes à la fin
                final_lines = accumulated_text.split('\n')
                if len(final_lines) > 4:
                    accumulated_text = '\n'.join(final_lines[:4])
                
                yield f"data: {json.dumps({'done': True})}\n\n"
                
            except Exception as e:
                logger.error(f"❌ Erreur lors du streaming du résumé: {str(e)}")
                yield f"data: {json.dumps({'error': str(e), 'done': True})}\n\n"
        
        return Response(generate(), mimetype='text/event-stream')
        
    except Exception as e:
        logger.error(f"❌ Erreur lors de la génération du résumé: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/summarize_repository_stream', methods=['POST'])
def summarize_repository_stream():
    """Génère un résumé d'un répertoire avec streaming"""
    try:
        data = request.get_json()
        files_info = data.get('files', [])
        language = data.get('language', 'fr')
        
        if not files_info or len(files_info) == 0:
            return jsonify({"error": "Aucun fichier fourni"}), 400
        
        # Compter les sous-répertoires et fichiers
        file_count = len(files_info)
        subdirectories = set()
        for file_info in files_info:
            name = file_info.get('name', '')
            if '/' in name:
                parts = name.split('/')
                if len(parts) > 1:
                    subdirectories.add(parts[0])
        
        subdirectory_count = len(subdirectories)
        
        def generate():
            try:
                # Utiliser Mistral pour générer le résumé
                client = OpenAI(base_url="https://api.mistral.ai/v1", api_key=os.getenv("MISTRAL_API_KEY"))
                
                # Construire le prompt avec les informations du répertoire
                file_names_text = '\n'.join([f"- {f.get('display_name', f.get('name', ''))}" for f in files_info[:10]])
                
                prompt = f"""Génère un résumé concis d'un répertoire contenant {file_count} fichier{'s' if file_count > 1 else ''} et {subdirectory_count} sous-répertoire{'s' if subdirectory_count > 1 else ''}.

Fichiers dans le répertoire:
{file_names_text}

Génère un résumé en {language} qui inclut:
1. Le nombre total de fichiers et sous-répertoires
2. Pour chacun des 3 premiers fichiers listés, génère un résumé de 2 lignes maximum avec le format: **[nom_fichier]**: [résumé 2 lignes]

Format attendu:
📁 Répertoire: {file_count} fichier{'s' if file_count > 1 else ''}, {subdirectory_count} sous-répertoire{'s' if subdirectory_count > 1 else ''}

**[nom_fichier_1]**: [résumé 2 lignes]
**[nom_fichier_2]**: [résumé 2 lignes]
**[nom_fichier_3]**: [résumé 2 lignes]

Résumé:"""
                
                stream = client.chat.completions.create(
                    model="mistral-small",
                    messages=[
                        {"role": "system", "content": f"Tu es un assistant expert en analyse de répertoires. Génère des résumés clairs et structurés en {language}. Pour chaque fichier, génère un résumé basé sur son nom et son extension."},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=400,
                    temperature=0.3,
                    stream=True
                )
                
                for chunk in stream:
                    if chunk.choices[0].delta.content:
                        content = chunk.choices[0].delta.content
                        yield f"data: {json.dumps({'content': content, 'done': False})}\n\n"
                
                yield f"data: {json.dumps({'done': True})}\n\n"
                
            except Exception as e:
                logger.error(f"❌ Erreur lors du streaming du résumé de répertoire: {str(e)}")
                yield f"data: {json.dumps({'error': str(e), 'done': True})}\n\n"
        
        return Response(generate(), mimetype='text/event-stream')
        
    except Exception as e:
        logger.error(f"❌ Erreur lors de la génération du résumé de répertoire: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/health', methods=['GET'])
def health_check():
    """Endpoint de santé pour vérifier que l'API fonctionne"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0",
        "services": {
            "openai": bool(os.getenv("OPENAI_API_KEY")),
            "mistral": bool(os.getenv("MISTRAL_API_KEY")),
            "google_oauth": AuthConfig.is_google_configured(),
            "database": os.path.exists(AuthConfig.DATABASE_PATH)
        },
        "endpoints": {
            "extract_structured": "/extract-structured",
            "summarize_file_stream": "/summarize_file_stream",
            "summarize_repository_stream": "/summarize_repository_stream"
        }
    }), 200

@app.route('/test-endpoints', methods=['GET'])
def test_endpoints():
    """Endpoint pour tester la disponibilité des endpoints"""
    endpoints_status = {}
    
    # Liste des endpoints à tester
    endpoints_to_test = [
        '/extract-structured',
        '/summarize_file_stream',
        '/summarize_repository_stream',
        '/query',
        '/upload'
    ]
    
    # Vérifier si les routes existent dans l'application Flask
    for endpoint in endpoints_to_test:
        rule = None
        for rule in app.url_map.iter_rules():
            if rule.rule == endpoint:
                endpoints_status[endpoint] = {
                    "exists": True,
                    "methods": list(rule.methods - {'HEAD', 'OPTIONS'}),
                    "rule": rule.rule
                }
                break
        else:
            endpoints_status[endpoint] = {
                "exists": False,
                "error": "Route not found"
            }
    
    return jsonify({
        "status": "ok",
        "endpoints": endpoints_status,
        "total_routes": len(list(app.url_map.iter_rules()))
    }), 200

@app.route('/users/me', methods=['GET'])
def get_current_user():
    """Récupère les informations de l'utilisateur connecté"""
    from auth import verify_jwt_token
    
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return jsonify({'error': 'Token manquant'}), 401
    
    token = auth_header.replace('Bearer ', '')
    payload = verify_jwt_token(token)
    
    if not payload:
        return jsonify({'error': 'Token invalide'}), 401
    
    return jsonify({
        'user': {
            'id': payload['user_id'],
            'email': payload['email'],
            'name': payload['name']
        }
    }), 200

# Route pour tester la configuration Google (DEBUG)
@app.route('/debug/google-config', methods=['GET'])
def debug_google_config():
    google_client_id = os.getenv('GOOGLE_CLIENT_ID')
    return jsonify({
        'google_client_id_set': bool(google_client_id),
        'google_client_secret_set': bool(os.getenv('GOOGLE_CLIENT_SECRET')),
        'client_id_preview': google_client_id[:20] + '...' if google_client_id else 'Missing',
        'full_client_id': google_client_id  # Temporaire pour debug
    })

def main():
    print("🚀 Starting Enhanced AI backend on http://0.0.0.0:5000")
    print(f"📋 Available models: {', '.join(MODEL_CONFIG.keys())}")
    print(f"🎯 Default model: {DEFAULT_MODEL} (Mistral)")
    print("📡 Endpoints:")
    print("   GET  /models - List all available models")
    print("   POST /models/<model_id>/test - Test specific model")
    print("   POST /upload - Upload files for analysis")
    print("   POST /query - Query with selected model")
    print("   POST /index-directory - Index directory files")
    print("🔐 Authentication endpoints:")
    print("   POST /auth/login - Email/password login")
    print("   POST /auth/register - User registration")
    print("   GET  /auth/google - Google OAuth")
    print("   GET  /auth/verify - Verify JWT token")
    print("   POST /marketing/subscribe - Save marketing emails")
    print("   GET  /health - Health check")
    print("   GET  /users/me - Current user info")
    print("✨ New features:")
    print("   • Complete authentication system")
    print("   • Google OAuth integration")
    print("   • Marketing email capture")
    print("   • JWT-based sessions")
    print("   • SQLite database")
    if AuthConfig.is_google_configured():
        print("   • ✅ Google OAuth configured")
    else:
        print("   • ⚠️  Google OAuth NOT configured")
    app.run(debug=False, host='0.0.0.0', port=5000)

if __name__ == "__main__":
    main()