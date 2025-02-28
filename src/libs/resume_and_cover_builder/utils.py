"""
This module contains utility functions for the Resume and Cover Letter Builder service.
"""

# app/libs/resume_and_cover_builder/utils.py
import json
import openai
import time
import re
from datetime import datetime
from typing import Dict, List
from langchain_core.messages.ai import AIMessage
from langchain_core.prompt_values import StringPromptValue
from langchain_openai import ChatOpenAI
from .config import global_config
from loguru import logger
from requests.exceptions import HTTPError as HTTPStatusError


class LLMLogger:

    def __init__(self, llm: ChatOpenAI):
        self.llm = llm

    @staticmethod
    def log_request(prompts, parsed_reply: Dict[str, Dict]):
        calls_log = global_config.LOG_OUTPUT_FILE_PATH / "open_ai_calls.json"
        if isinstance(prompts, StringPromptValue):
            prompts = prompts.text
        elif isinstance(prompts, Dict):
            # Convert prompts to a dictionary if they are not in the expected format
            prompts = {
                f"prompt_{i+1}": prompt.content
                for i, prompt in enumerate(prompts.messages)
            }
        else:
            prompts = {
                f"prompt_{i+1}": prompt.content
                for i, prompt in enumerate(prompts.messages)
            }

        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Extract token usage details from the response
        token_usage = parsed_reply["usage_metadata"]
        output_tokens = token_usage["output_tokens"]
        input_tokens = token_usage["input_tokens"]
        total_tokens = token_usage["total_tokens"]

        # Extract model details from the response
        model_name = parsed_reply["response_metadata"]["model_name"]
        prompt_price_per_token = 0.00000015
        completion_price_per_token = 0.0000006

        # Calculate the total cost of the API call
        total_cost = (input_tokens * prompt_price_per_token) + (
            output_tokens * completion_price_per_token
        )

        # Create a log entry with all relevant information
        log_entry = {
            "model": model_name,
            "time": current_time,
            "prompts": prompts,
            "replies": parsed_reply["content"],  # Response content
            "total_tokens": total_tokens,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_cost": total_cost,
        }

        # Write the log entry to the log file in JSON format
        with open(calls_log, "a", encoding="utf-8") as f:
            json_string = json.dumps(log_entry, ensure_ascii=False, indent=4)
            f.write(json_string + "\n")


class LoggerChatModel:

    def __init__(self, llm: ChatOpenAI):
        self.llm = llm
        self.fallback_llm = None
        self.is_using_fallback = False

    def _initialize_fallback(self):
        """Initialize a fallback model using Ollama."""
        try:
            from langchain_community.llms import Ollama
            logger.info("Initializing fallback model (deepseek-r1:32b)")
            self.fallback_llm = Ollama(model="deepseek-r1:32b")
            logger.info("Fallback model initialized successfully")
            self.is_using_fallback = True
        except Exception as e:
            logger.error(f"Failed to initialize fallback model: {str(e)}")
            return False
        return True

    def __call__(self, messages: List[Dict[str, str]]) -> str:
        max_retries = 15
        retry_delay = 10
        auth_error_encountered = False

        for attempt in range(max_retries):
            try:
                # Use fallback model if authentication error was encountered previously
                if auth_error_encountered and self.fallback_llm:
                    logger.info("Using fallback model due to previous authentication error")
                    
                    # For Ollama models, we need to convert the messages format
                    if isinstance(messages, list):
                        # Extract content from each message to create a single prompt
                        text_prompt = "\n\n".join([m.get("content", "") for m in messages])
                    else:
                        text_prompt = str(messages)
                    
                    fallback_response = self.fallback_llm(text_prompt)
                    
                    # Create a compatible response structure
                    ai_message = AIMessage(content=fallback_response)
                    ai_message.response_metadata = {"model_name": "deepseek-r1", "finish_reason": "stop"}
                    ai_message.id = "fallback_response"
                    ai_message.usage_metadata = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}
                    
                    return ai_message
                
                reply = self.llm.invoke(messages)
                parsed_reply = self.parse_llmresult(reply)
                LLMLogger.log_request(prompts=messages, parsed_reply=parsed_reply)
                return reply
                
            except (openai.RateLimitError, HTTPStatusError) as err:
                if isinstance(err, HTTPStatusError):
                    if err.response.status_code == 401:
                        logger.warning("Authentication error (401 Unauthorized): Attempting to use fallback model")
                        auth_error_encountered = True
                        
                        if not self.fallback_llm and not self._initialize_fallback():
                            logger.error("Authentication error and fallback initialization failed.")
                            raise ValueError("Invalid API key and fallback model initialization failed.")
                        
                        # Continue to retry with the fallback model
                        continue
                        
                    elif err.response.status_code == 429:
                        logger.warning(f"HTTP 429 Too Many Requests: Waiting for {retry_delay} seconds before retrying (Attempt {attempt + 1}/{max_retries})...")
                        time.sleep(retry_delay)
                        retry_delay *= 2
                    else:
                        logger.warning(f"HTTP error {err.response.status_code}: Waiting for {retry_delay} seconds before retrying (Attempt {attempt + 1}/{max_retries})...")
                        time.sleep(retry_delay)
                        retry_delay *= 2
                else:
                    wait_time = self.parse_wait_time_from_error_message(str(err))
                    logger.warning(f"Rate limit exceeded or API error. Waiting for {wait_time} seconds before retrying (Attempt {attempt + 1}/{max_retries})...")
                    time.sleep(wait_time)
            except ValueError as e:
                if "API key" in str(e) or "authentication" in str(e).lower():
                    logger.warning(f"API authentication error: {str(e)}")
                    auth_error_encountered = True
                    
                    if not self.fallback_llm and not self._initialize_fallback():
                        logger.error("Authentication error and fallback initialization failed.")
                        raise ValueError("Invalid API key and fallback model initialization failed.")
                    
                    # Continue to retry with the fallback model
                    continue
                else:
                    logger.error(f"ValueError: {str(e)}, retrying in {retry_delay} seconds... (Attempt {attempt + 1}/{max_retries})")
                    time.sleep(retry_delay)
                    retry_delay *= 2
            except Exception as e:
                logger.error(f"Unexpected error occurred: {str(e)}, retrying in {retry_delay} seconds... (Attempt {attempt + 1}/{max_retries})")
                time.sleep(retry_delay)
                retry_delay *= 2

        logger.critical("Failed to get a response from the model after multiple attempts.")
        raise Exception("Failed to get a response from the model after multiple attempts.")

    def parse_wait_time_from_error_message(self, error_message: str) -> int:
        """
        Parse the wait time from OpenAI rate limit error messages.
        Args:
            error_message (str): The error message from the API.
        Returns:
            int: The number of seconds to wait before retrying.
        """
        # Try to extract retry time from error message
        retry_match = re.search(r"retry after (\d+)", error_message, re.IGNORECASE)
        if retry_match:
            return int(retry_match.group(1))
        
        # Default retry delay if no specific time is found
        return 30

    def parse_llmresult(self, llmresult: AIMessage) -> Dict[str, Dict]:
        # Parse the LLM result into a structured format.
        content = llmresult.content
        response_metadata = llmresult.response_metadata
        id_ = llmresult.id
        usage_metadata = llmresult.usage_metadata

        parsed_result = {
            "content": content,
            "response_metadata": {
                "model_name": response_metadata.get("model_name", ""),
                "system_fingerprint": response_metadata.get("system_fingerprint", ""),
                "finish_reason": response_metadata.get("finish_reason", ""),
                "logprobs": response_metadata.get("logprobs", None),
            },
            "id": id_,
            "usage_metadata": {
                "input_tokens": usage_metadata.get("input_tokens", 0),
                "output_tokens": usage_metadata.get("output_tokens", 0),
                "total_tokens": usage_metadata.get("total_tokens", 0),
            },
        }
        return parsed_result
