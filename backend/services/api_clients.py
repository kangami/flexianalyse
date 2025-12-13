"""
Clients API pour les différents fournisseurs de modèles AI
"""
import os
import json
import requests
import time
import re
import logging
from openai import OpenAI
from config.models import (
    MODEL_CONFIG, DEFAULT_MODEL, MISTRAL_MODEL, 
    OLLAMA_API_URL, OLLAMA_MODELS, OPENAI_API_KEY, MISTRAL_API_KEY
)

logger = logging.getLogger(__name__)

# Initialize OpenAI client
openai_client = OpenAI(api_key=OPENAI_API_KEY)


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
                
                # Extract text from responses API
                try:
                    if hasattr(response, 'output') and response.output:
                        for item in response.output:
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
                        response_str = str(response)
                        logger.warning(f"[OpenAI] Using fallback extraction for GPT-5 response")
                        text_match = re.search(r"text='([^']*)'", response_str)
                        if text_match:
                            extracted_text = text_match.group(1)
                            extracted_text = extracted_text.replace('\\n', '\n').replace("\\'", "'")
                            return extracted_text.strip()
                        return "Error: Could not extract response content from GPT-5"
                except Exception as extraction_error:
                    logger.error(f"[OpenAI] Error extracting GPT-5 response: {extraction_error}")
                    return f"Error extracting response: {str(extraction_error)}"
            
            # Standard models use Chat Completions API
            else:
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
        elif selected_model.lower() == "mistral":
            try:
                response = call_mistral_api(prompt)
                words = response.split(' ')
                for i in range(0, len(words), 3):
                    chunk = ' '.join(words[i:i+3])
                    if i + 3 < len(words):
                        chunk += ' '
                    yield f"data: {json.dumps({'content': chunk})}\n\n"
                    time.sleep(0.05)
                yield f"data: {json.dumps({'done': True})}\n\n"
            except Exception as mistral_error:
                logger.warning(f"Mistral failed: {str(mistral_error)}, falling back to GPT-3.5")
                yield f"data: {json.dumps({'warning': 'Mistral indisponible, utilisation de GPT-3.5'})}\n\n"
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
        elif selected_model.lower() in ["llama3", "llama3.2"]:
            try:
                response = call_ollama_api(prompt, selected_model)
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


