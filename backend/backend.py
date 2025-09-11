import os
import json
import requests
from flask import Flask, request, jsonify
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
from typing import Dict, List, Optional
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
        "model_id": "mistral-medium-2505",
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
DEFAULT_MODEL = "gpt-3.5-turbo"  # Set GPT-3.5-Turbo as default
MISTRAL_MODEL = "mistral-medium-2505"
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")

if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY environment variable not set")

# Flask setup
app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": ["http://flexianalyse.com", "http://localhost:5173", "https://flexianalyse.com"]}})

# Initialize clients and components
openai_client = OpenAI(api_key=OPENAI_API_KEY)
embeddings = OpenAIEmbeddings(api_key=OPENAI_API_KEY)
vector_store = None

# Cache setup
cache = aiocache.SimpleMemoryCache()

# Logger setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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

def call_openai_api(prompt, selected_model="gpt-3.5-turbo", max_retries=3):
    """
    Enhanced OpenAI API call supporting both Chat Completions and Responses API
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
                request_params = {
                    "model": model_id,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.5,
                    "max_tokens": model_config.get("max_tokens", 500)
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

async def query_model_local_mode(file_name: str, file_content: str, directory_content: List[Dict], 
                                repo_structure: str, user_query: str, is_binary: bool = False, 
                                selected_model: str = DEFAULT_MODEL, language: str = 'en') -> str:
    """
    Mode LOCAL: Analyse uniquement le contexte local fourni
    """
    cache_key = f"local_query_{file_name}_{user_query}_{selected_model}_{language}"
    cached = await cache.get(cache_key)
    if cached:
        return cached

    t = translations.get(language, translations['en'])

    # Construction du prompt UNIQUEMENT avec le contexte local
    directory_content_summary = ' '.join(
        [f"{t['other_file']}: {doc['fileName']} : {doc['content']}" for doc in directory_content]
    ) if directory_content else "Aucun autre fichier dans le contexte."

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

    try:
        result = await execute_model_query(prompt, selected_model)
    except Exception as e:
        result = f"Erreur lors de l'analyse locale: {str(e)}"

    await cache.set(cache_key, result, ttl=3600)
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
    
async def analyze_query_need_for_search(user_query: str, selected_model: str, language: str = 'en') -> Dict:
    """
    Analyse si la query nécessite des informations actuelles
    """
    t = translations.get(language, translations['en'])
    
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
        f"{t['recent_people_companies']}\n\n"
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
                                 language: str = 'en') -> str:
    """
    Mode ONLINE: Réponse du modèle enrichie avec des données actuelles si nécessaire (comme SearchGPT)
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
        if search_analysis.get("needs_search", False):
            logger.info("🌐 Enrichissement avec des données actuelles...")
            
            # Utiliser les mots-clés optimisés ou la query originale
            search_keywords = search_analysis.get("search_keywords", [user_query])
            search_query = " ".join(search_keywords) if isinstance(search_keywords, list) else user_query
            
            # Recherche en ligne
            search_results = perform_online_search(search_query, language)
            
            # ÉTAPE 4: Fusion intelligente des informations
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
                f"{t['enriched_response']}"
            )
            
            enriched_response = await execute_model_query(enrichment_prompt, selected_model)
            
            # Ajout des métadonnées de recherche
            final_response = (
                f"{enriched_response}\n\n"
                f"---\n"
                f"💡 **Informations enrichies**: Cette réponse combine mes connaissances de base "
                f"avec des données récentes trouvées en ligne.\n \n"
                f"🔍 **Model **: {selected_model}"
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

        # Diviser les documents en chunks
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1500,
            chunk_overlap=200,
            length_function=len,
            separators=["\n\n", "\n", " ", ""]
        )
        split_docs = text_splitter.split_documents(documents)
        logger.info(f"✂️ Documents divisés en {len(split_docs)} chunks")
        
        # Vérifier la clé OpenAI
        openai_api_key = os.getenv('OPENAI_API_KEY')
        if not openai_api_key:
            return jsonify({
                'error': 'Clé API OpenAI non configurée sur le serveur',
                'suggestion': 'Contactez l\'administrateur pour configurer OPENAI_API_KEY'
            }), 500
        
        # Créer les embeddings
        logger.info("🧠 Création des embeddings avec OpenAI...")
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
        
        # Créer le vector store
        logger.info("🗃️ Création du vector store...")
        vector_store = await FAISS.afrom_documents(split_docs, embeddings)
        
        # Stocker le vector store pour cette session
        vector_stores[session_id] = {
            'store': vector_store,
            'created_at': datetime.utcnow().isoformat(),
            'files_count': len(files),
            'chunks_count': len(split_docs),
            'files_indexed': [f['fileName'] for f in files]
        }
        
        logger.info(f"✅ Indexation terminée pour la session {session_id}")
        
        return jsonify({
            'success': True,
            'session_id': session_id,
            'indexed_files_count': len(files),
            'chunks_count': len(split_docs),
            'files_indexed': [f['fileName'] for f in files],
            'vector_store_ready': True
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
            
            # NOUVELLE LOGIQUE: Utiliser le vector store de la session
            relevant_docs = []
            if use_backend_vectorstore and session_id in vector_stores:
                try:
                    session_store = vector_stores[session_id]
                    vector_store = session_store['store']
                    
                    logger.info(f"🔍 Recherche dans le vector store de la session {session_id}")
                    retriever = vector_store.as_retriever(k=5)
                    
                    # Recherche synchrone (ajuster selon votre version de LangChain)
                    relevant_docs = retriever.invoke(user_query)
                    
                    # Ajout des documents pertinents au contexte
                    for doc in relevant_docs:
                        directory_content.append({ 
                            "fileName": doc.metadata.get("fileName", "document_vectorstore"), 
                            "content": doc.page_content 
                        })
                    
                    logger.info(f"📚 {len(relevant_docs)} documents ajoutés depuis le vector store de session")
                    
                except Exception as e:
                    logger.warning(f"Erreur lors de la récupération depuis le vector store: {str(e)}")
            
            elif use_backend_vectorstore:
                logger.warning(f"Vector store demandé mais non trouvé pour la session {session_id}")
            
            # ANCIENNE LOGIQUE: Utiliser le vector store global (fallback)
            elif vector_store and user_query:
                try:
                    retriever = vector_store.as_retriever(k=5)
                    relevant_docs = retriever.invoke(user_query)
                    
                    # Ajout des documents pertinents au contexte
                    for doc in relevant_docs:
                        directory_content.append({ 
                            "fileName": doc.metadata.get("file_name", "document_vectorstore"), 
                            "content": doc.page_content 
                        })
                    logger.info(f"📚 {len(relevant_docs)} documents ajoutés depuis le vector store global")
                except Exception as e:
                    logger.warning(f"Erreur lors de la récupération depuis le vector store global: {str(e)}")
            
            # Exécution de la requête en mode local
            response = await query_model_local_mode(
                file_name=file_name,
                file_content=file_content,
                directory_content=directory_content,
                repo_structure=repo_structure,
                user_query=user_query,
                is_binary=is_binary,
                selected_model=selected_model,
                language=language
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
        
        # MODE ONLINE (reste identique)
        elif effective_mode == 'online' or enable_online_search:
            logger.info(f"🌐 Mode ONLINE activé pour la requête: {user_query[:50]}...")
            
            response = await query_model_online_mode(
                user_query=user_query,
                selected_model=selected_model,
                language=language
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
        }
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
    print(f"🎯 Default model: {DEFAULT_MODEL} (GPT-3.5-Turbo)")
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