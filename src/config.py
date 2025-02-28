"""
Configuration settings for the Jobs Applier AI Agent.
"""
from pathlib import Path

# LLM Configuration
LLM_MODEL_TYPE = "ollama"  # Using Ollama as the default LLM provider
LLM_MODEL = "phi3:latest"  # Using deepseek as the default model
LLM_API_URL = ""  # Use default Ollama API URL (localhost:11434)

# Application paths
BASE_DIR = Path(__file__).resolve().parent.parent
LOG_DIR = BASE_DIR / "logs"
OUTPUT_DIR = BASE_DIR / "output"
DATA_DIR = BASE_DIR / "data"

# Feature flags
USE_LOCAL_MODELS_ONLY = True  # Only use local models, no API calls
DEBUG_MODE = True

# Job processing settings
MAX_JOBS_TO_PROCESS = 10
JOB_SUITABILITY_SCORE = 6  # Minimum score (out of 10) for job to be considered suitable

# API retry settings
MAX_RETRIES = 3
RETRY_DELAY = 5

# Create directories if they don't exist
for directory in [LOG_DIR, OUTPUT_DIR, DATA_DIR]:
    directory.mkdir(exist_ok=True)
