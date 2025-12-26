"""
Configuration des modèles AI disponibles
"""
import os
from dotenv import load_dotenv

# Load environment variables early
load_dotenv()

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
        "reasoning_effort": "medium",
        "verbosity": "medium"
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
    "gemini-3-flash": {
        "name": "Gemini 3 Flash",
        "provider": "Google",
        "model_id": "gemini-3-flash-preview",
        "max_tokens": 8192,
        "description": "Fast and efficient Gemini 3 Flash model",
        "cost_tier": "low",
        "api_type": "gemini"
    }
}

# Config constants
OLLAMA_API_URL = "http://localhost:11434/api/generate"
OLLAMA_MODELS = ["llama3.2", "llama3"]
DEFAULT_MODEL = "mistral"
MISTRAL_MODEL = "mistral-medium-latest"
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")
# Support both GOOGLE_API_KEY and GEMINI_API_KEY for compatibility
GEMINI_API_KEY = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")

# Note: La validation de OPENAI_API_KEY se fait dans FlaskConfig.validate_env_vars()
# pour ne pas bloquer l'import du module

