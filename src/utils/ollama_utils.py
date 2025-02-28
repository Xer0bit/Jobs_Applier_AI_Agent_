"""
Utility functions for working with Ollama models.
"""
import subprocess
import requests
import time
import platform
import os
from pathlib import Path
from loguru import logger

def check_ollama_running():
    """Check if Ollama server is running."""
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        return response.status_code == 200
    except requests.RequestException:
        return False

def start_ollama_server():
    """Start the Ollama server if it's not already running."""
    if check_ollama_running():
        logger.info("Ollama server is already running.")
        return True
    
    try:
        # Determine the platform
        system = platform.system().lower()
        
        if system == "windows":
            # On Windows, start Ollama using subprocess
            logger.info("Starting Ollama server on Windows...")
            # Assuming Ollama is in the PATH or specify the full path
            subprocess.Popen(["ollama", "serve"], 
                            creationflags=subprocess.CREATE_NO_WINDOW,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE)
        elif system == "darwin" or system == "linux":
            # On macOS or Linux
            logger.info(f"Starting Ollama server on {system}...")
            subprocess.Popen(["ollama", "serve"],
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE)
        else:
            logger.error(f"Unsupported operating system: {system}")
            return False
        
        # Wait for the server to start
        max_retries = 30
        retry_delay = 1
        for _ in range(max_retries):
            time.sleep(retry_delay)
            if check_ollama_running():
                logger.info("Ollama server started successfully.")
                return True
            
        logger.error("Failed to start Ollama server.")
        return False
        
    except Exception as e:
        logger.error(f"Error starting Ollama server: {str(e)}")
        return False

def ensure_model_is_available(model_name="llama3.3"):
    """
    Ensure the specified model is available in Ollama.
    Returns True if model is ready to use, False otherwise.
    """
    if not check_ollama_running():
        if not start_ollama_server():
            logger.error("Could not start Ollama server")
            return False
    
    try:
        # Check if model exists
        response = requests.get("http://localhost:11434/api/tags", timeout=10)
        models = response.json()
        
        model_exists = any(model["name"] == model_name for model in models.get("models", []))
        
        if not model_exists:
            logger.info(f"Model {model_name} not found. Attempting to pull it...")
            
            # Pull the model
            pull_process = subprocess.Popen(
                ["ollama", "pull", model_name],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )
            
            # Monitor the process
            for line in pull_process.stdout:
                if "pulling" in line.lower() or "downloading" in line.lower():
                    logger.info(line.strip())
            
            return_code = pull_process.wait()
            
            if return_code != 0:
                stderr = pull_process.stderr.read()
                logger.error(f"Failed to pull model: {stderr}")
                return False
                
            logger.info(f"Model {model_name} successfully pulled.")
        else:
            logger.info(f"Model {model_name} is already available.")
            
        return True
        
    except Exception as e:
        logger.error(f"Error ensuring model availability: {str(e)}")
        return False

def initialize_ollama_environment():
    """
    Initialize the Ollama environment: start server and ensure model is available.
    """
    logger.info("Initializing Ollama environment...")
    
    # Start the server
    if not start_ollama_server():
        logger.warning("Ollama server could not be started. Some features may not work correctly.")
    
    # Ensure model is available
    model_name = "llama3.3"  # The model we're using
    if not ensure_model_is_available(model_name):
        logger.warning(f"Could not ensure model {model_name} is available. Some features may not work correctly.")
        
    logger.info("Ollama environment initialization completed.")
