"""
Services d'analyse de fichiers et de documents
"""
import os
import json
import logging
import asyncio
import time
from typing import Dict, List, Any
from langchain_core.documents import Document
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
    """Sauvegarde la description d'un fichier avec gestion robuste des erreurs JSON"""
    descriptions = []
    
    # Lire le fichier avec gestion d'erreurs pour fichiers corrompus
    if os.path.exists(DESCRIPTIONS_FILE):
        try:
            with open(DESCRIPTIONS_FILE, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                
                # Si le fichier est vide, créer une liste vide
                if not content:
                    descriptions = []
                else:
                    # Essayer de parser comme JSON normal
                    try:
                        descriptions = json.loads(content)
                    except json.JSONDecodeError as e:
                        # Si échec, essayer de réparer le fichier
                        logger.warning(f"Fichier JSON corrompu détecté (erreur: {e}), tentative de réparation...")
                        
                        # Créer une sauvegarde d'abord
                        backup_file = DESCRIPTIONS_FILE + '.backup'
                        try:
                            with open(backup_file, 'w', encoding='utf-8') as backup:
                                backup.write(content)
                            logger.info(f"Sauvegarde créée: {backup_file}")
                        except Exception as backup_error:
                            logger.error(f"Impossible de créer une sauvegarde: {backup_error}")
                        
                        # Méthode de réparation: extraire les objets JSON valides
                        import re
                        descriptions = []
                        
                        # Chercher tous les objets JSON avec file_name
                        pattern = r'\{\s*"file_name"\s*:\s*"[^"]*"\s*,\s*"description"\s*:\s*"[^"]*"\s*\}'
                        matches = re.finditer(pattern, content, re.DOTALL)
                        for match in matches:
                            try:
                                # Étendre la recherche pour capturer des descriptions multi-lignes
                                start = match.start()
                                # Chercher l'objet complet en comptant les accolades
                                brace_count = 0
                                in_string = False
                                escape = False
                                end = start
                                
                                for i, char in enumerate(content[start:], start):
                                    if escape:
                                        escape = False
                                        continue
                                    if char == '\\':
                                        escape = True
                                        continue
                                    if char == '"' and not escape:
                                        in_string = not in_string
                                        continue
                                    if not in_string:
                                        if char == '{':
                                            brace_count += 1
                                        elif char == '}':
                                            brace_count -= 1
                                            if brace_count == 0:
                                                end = i + 1
                                                break
                                
                                obj_str = content[start:end]
                                parsed = json.loads(obj_str)
                                if isinstance(parsed, dict) and 'file_name' in parsed:
                                    descriptions.append(parsed)
                            except (json.JSONDecodeError, ValueError) as parse_error:
                                logger.debug(f"Impossible de parser un objet: {parse_error}")
                                continue
                        
                        # Dédupliquer par file_name
                        seen = set()
                        unique_descriptions = []
                        for desc in descriptions:
                            if isinstance(desc, dict) and 'file_name' in desc:
                                file_name_key = desc['file_name']
                                if file_name_key not in seen:
                                    seen.add(file_name_key)
                                    unique_descriptions.append(desc)
                        
                        descriptions = unique_descriptions
                        
                        if descriptions:
                            logger.info(f"Fichier JSON réparé, {len(descriptions)} entrées récupérées")
                            # Sauvegarder immédiatement le fichier réparé
                            try:
                                temp_file = DESCRIPTIONS_FILE + '.tmp'
                                with open(temp_file, 'w', encoding='utf-8') as f:
                                    json.dump(descriptions, f, indent=4, ensure_ascii=False)
                                os.replace(temp_file, DESCRIPTIONS_FILE)
                            except Exception as save_error:
                                logger.warning(f"Impossible de sauvegarder le fichier réparé: {save_error}")
                        else:
                            descriptions = []
                            logger.warning("Aucune entrée valide trouvée, création d'un nouveau fichier")
                    
                    # S'assurer que descriptions est une liste
                    if not isinstance(descriptions, list):
                        logger.warning("Le fichier JSON ne contient pas une liste, conversion en liste...")
                        descriptions = [descriptions] if descriptions else []
        
        except Exception as e:
            logger.error(f"Erreur lors de la lecture du fichier de descriptions: {e}")
            descriptions = []
            # Créer une sauvegarde si possible
            try:
                backup_file = DESCRIPTIONS_FILE + '.backup.' + str(int(time.time()))
                if os.path.exists(DESCRIPTIONS_FILE):
                    import shutil
                    shutil.copy2(DESCRIPTIONS_FILE, backup_file)
                    logger.warning(f"Fichier sauvegardé dans {backup_file}")
            except Exception:
                pass
    
    # Ajouter la nouvelle description
    # Vérifier si le fichier existe déjà pour éviter les doublons
    existing_index = None
    for idx, desc in enumerate(descriptions):
        if isinstance(desc, dict) and desc.get('file_name') == file_name:
            existing_index = idx
            break
    
    new_entry = {"file_name": file_name, "description": description}
    
    if existing_index is not None:
        # Mettre à jour l'entrée existante
        descriptions[existing_index] = new_entry
        logger.info(f"Description mise à jour pour {file_name}")
    else:
        # Ajouter une nouvelle entrée
        descriptions.append(new_entry)
        logger.info(f"Nouvelle description ajoutée pour {file_name}")
    
    # Écrire le fichier avec gestion d'erreurs
    try:
        # Écrire dans un fichier temporaire d'abord, puis renommer (atomique)
        temp_file = DESCRIPTIONS_FILE + '.tmp'
        with open(temp_file, 'w', encoding='utf-8') as f:
            json.dump(descriptions, f, indent=4, ensure_ascii=False)
        
        # Renommer atomiquement (fonctionne sur la plupart des systèmes)
        if os.path.exists(DESCRIPTIONS_FILE):
            os.replace(temp_file, DESCRIPTIONS_FILE)
        else:
            os.rename(temp_file, DESCRIPTIONS_FILE)
            
        logger.info(f"Fichier de descriptions sauvegardé avec succès ({len(descriptions)} entrées)")
    except Exception as e:
        logger.error(f"Erreur lors de l'écriture du fichier de descriptions: {e}")
        # Essayer d'écrire directement si le renommage échoue
        try:
            with open(DESCRIPTIONS_FILE, 'w', encoding='utf-8') as f:
                json.dump(descriptions, f, indent=4, ensure_ascii=False)
        except Exception as e2:
            logger.error(f"Échec de l'écriture directe: {e2}")
            raise


