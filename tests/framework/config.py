"""
Configuración compartida para todos los benchmarks.
"""

import os

# ── API Configuration ────────────────────────────────────────────────────────

API_URL = "https://ai-api.berguecio.cl/v1"

def load_api_key() -> str:
    """Carga la API key desde variable de entorno o archivo .env"""
    # 1. Variable de entorno
    if os.environ.get("LITELLM_MASTER_KEY"):
        return os.environ["LITELLM_MASTER_KEY"]

    # 2. Archivo .env en el directorio raíz del proyecto
    env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env")
    if os.path.exists(env_path):
        for line in open(env_path):
            line = line.strip()
            if line.startswith("LITELLM_MASTER_KEY="):
                return line.split("=", 1)[1]


# ── Models Configuration ─────────────────────────────────────────────────────

# Modelos en orden: más grande primero
# Formato: (nombre_litellm, nombre_ollama)
MODELS = [
    ("gemma4:31b", "gemma4:31b-it-q4_K_M"),
    ("gemma4:31b-thinking", "gemma4:31b-it-q4_K_M"),
    ("qwen3.5:35b", "qwen3.5:35b-a3b"),
    ("qwen3.5:35b-thinking", "qwen3.5:35b-a3b"),
    ("glm-4.7-flash", "glm-4.7-flash:q4_K_M"),
    ("glm-4.7-flash:thinking", "glm-4.7-flash:q4_K_M"),
    ("ministral-3:14b", "ministral-3:14b"),
    ("gemma4:26b", "gemma4:26b"),
    ("gemma4:26b-thinking", "gemma4:26b"),
    ("gemma4:e4b", "gemma4:e4b"),
    ("gemma4:e2b", "gemma4:e2b"),
]

# ── Docker Configuration ─────────────────────────────────────────────────────

OLLAMA_CONTAINER = "ollama-prod"

# ── Test Configuration ───────────────────────────────────────────────────────

# Parámetros comunes para llamadas a la API
DEFAULT_TEMPERATURE = 0.1
DEFAULT_MAX_TOKENS = 3000
DEFAULT_TIMEOUT = 600

# Timeout para ejecución de scripts generados
EXECUTION_TIMEOUT = 60

# Tiempo de espera entre modelos (para evitar sobrecargar el servidor)
INTER_MODEL_DELAY = 5