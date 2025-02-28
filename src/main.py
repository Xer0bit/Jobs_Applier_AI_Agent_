"""
Main entry point for the Jobs Applier AI Agent.
"""
import os
import sys
from pathlib import Path
from loguru import logger
from dotenv import load_dotenv

# Add project root to path
project_root = Path(__file__).resolve().parent.parent
if project_root not in sys.path:
    sys.path.append(str(project_root))

# Local imports
from src.utils.ollama_utils import initialize_ollama_environment
import src.config as config

# Configure logging
log_path = config.LOG_DIR / "app.log"
logger.add(log_path, rotation="10 MB", retention="7 days")

def main():
    """
    Main function that serves as the entry point for the application.
    """
    logger.info("Starting Jobs Applier AI Agent")
    
    # Initialize the Ollama environment
    initialize_ollama_environment()
    
    # Your main application code would go here
    logger.info("AI Hawk agent is ready!")
    
    # Example placeholder for future functionality
    logger.info("Running with configuration:")
    logger.info(f"- LLM Model: {config.LLM_MODEL}")
    logger.info(f"- Debug Mode: {config.DEBUG_MODE}")
    logger.info(f"- Using Local Models Only: {config.USE_LOCAL_MODELS_ONLY}")
    
    logger.info("Jobs Applier AI Agent finished")

if __name__ == "__main__":
    main()
