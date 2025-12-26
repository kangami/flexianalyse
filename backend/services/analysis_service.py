"""
Services d'analyse de fichiers et de documents
"""
import os
import json
import logging
import asyncio
from typing import Dict, List, Any
from langchain.schema import Document
import aiocache
from config.models import DEFAULT_MODEL, OLLAMA_MODELS
from services.api_clients import call_openai_api, call_mistral_api, call_ollama_api, call_gemini_api
from utils.translations import translations

logger = logging.getLogger(__name__)

# Cache setup
cache = aiocache.SimpleMemoryCache()

# Description file path
DESCRIPTIONS_FILE = os.path.join(os.path.dirname(__file__), "..", "file_descriptions.json")
if not os.path.exists(DESCRIPTIONS_FILE):
    with open(DESCRIPTIONS_FILE, 'w') as f:
        json.dump([], f)


async def analyze_file_content(file_content, file_name, is_binary=False, extension='', selected_model=DEFAULT_MODEL, language='en'):
    """Analyse le contenu d'un fichier et génère une description"""
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
        if selected_model.lower() in ["gpt-3.5-turbo", "gpt-4o"]:
            description = call_openai_api(prompt, selected_model)
        elif selected_model.lower() in ["gpt-5", "gpt-5-mini", "gpt-5-nano"]:
            description = call_openai_api(prompt, selected_model)
        elif selected_model.lower() == "openai":
            description = call_openai_api(prompt, "openai")
        elif selected_model.lower() == "mistral":
            description = call_mistral_api(prompt)
        elif selected_model.lower().startswith("gemini") or selected_model.lower() in ["gemini-3-flash", "gemini-pro"]:
            description = call_gemini_api(prompt, selected_model)
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
    """Sauvegarde la description d'un fichier"""
    with open(DESCRIPTIONS_FILE, 'r') as f:
        descriptions = json.load(f)
    descriptions.append({"file_name": file_name, "description": description})
    with open(DESCRIPTIONS_FILE, 'w') as f:
        json.dump(descriptions, f, indent=4)


