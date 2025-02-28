import requests
from src import config
import logging

logger = logging.getLogger(__name__)

def call_ollama_api(prompt: str):
    """
    Calls the Ollama API to generate text based on the given prompt.
    Handles potential errors and retries.
    """
    url = config.LLM_API_URL or "http://localhost:11434/api/generate"
    headers = {"Content-Type": "application/json"}
    data = {
        "prompt": prompt,
        "model": config.LLM_MODEL,
        "stream": False  # Adjust as needed
    }

    for attempt in range(config.MAX_RETRIES):
        try:
            response = requests.post(url, headers=headers, json=data)
            response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
            return response.json()['response']
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed (attempt {attempt + 1}/{config.MAX_RETRIES}): {e}")
            if attempt < config.MAX_RETRIES - 1:
                logger.info(f"Retrying in {config.RETRY_DELAY} seconds...")
                time.sleep(config.RETRY_DELAY)
            else:
                logger.error("Max retries reached. API call failed.")
                raise  # Re-raise the exception if all retries failed
