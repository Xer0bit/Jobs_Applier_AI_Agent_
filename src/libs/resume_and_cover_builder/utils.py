"""
This module contains utility functions for the Resume and Cover Letter Builder service.
"""

import json
import time
import re
from datetime import datetime
from typing import Dict, List, Any
from langchain_core.messages.ai import AIMessage
from langchain_core.prompt_values import StringPromptValue
from .config import global_config
from loguru import logger

class LLMLogger:
    def __init__(self, llm: Any):
        self.llm = llm

    @staticmethod
    def log_request(prompts, parsed_reply: Dict[str, Dict]):
        calls_log = global_config.LOG_OUTPUT_FILE_PATH / "llm_calls.json"
        
        # Handle different prompt formats
        if isinstance(prompts, StringPromptValue):
            prompts = prompts.text
        elif isinstance(prompts, Dict):
            # Convert prompts to a dictionary if they are not in the expected format
            try:
                prompts = {
                    f"prompt_{i+1}": prompt.content
                    for i, prompt in enumerate(prompts.messages)
                }
            except (AttributeError, TypeError):
                # If conversion fails, just convert to string
                prompts = str(prompts)
        elif isinstance(prompts, list):
            try:
                prompts = {
                    f"prompt_{i+1}": prompt.get("content", str(prompt))
                    for i, prompt in enumerate(prompts)
                }
            except (AttributeError, TypeError):
                prompts = str(prompts)
        else:
            prompts = str(prompts)

        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Extract token usage details from the response with safe defaults
        token_usage = parsed_reply.get("usage_metadata", {})
        output_tokens = token_usage.get("output_tokens", 0)
        input_tokens = token_usage.get("input_tokens", 0)
        total_tokens = token_usage.get("total_tokens", 0)

        # Extract model details from the response
        response_metadata = parsed_reply.get("response_metadata", {})
        model_name = response_metadata.get("model_name", "llama3.3")
        
        # For local models, we don't have real token costs
        total_cost = 0.0

        # Create a log entry with all relevant information
        log_entry = {
            "model": model_name,
            "time": current_time,
            "prompts": prompts,
            "replies": parsed_reply.get("content", ""),  # Response content
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
    def __init__(self, llm):
        self.llm = llm
        logger.debug(f"LoggerChatModel successfully initialized with LLM type: {type(llm).__name__}")

    def __call__(self, messages: List[Dict[str, str]]) -> str:
        max_retries = 3
        retry_delay = 5

        for attempt in range(max_retries):
            try:
                logger.debug(f"Calling LLM with messages (attempt {attempt+1}/{max_retries})")
                
                # Format messages appropriately for Ollama
                if isinstance(messages, list):
                    # Extract content from each message to create a single prompt
                    text_prompt = "\n\n".join([m.get("content", str(m)) for m in messages])
                else:
                    text_prompt = str(messages)
                
                # Call the model
                response_text = self.llm(text_prompt)
                
                # Create an AIMessage-compatible response
                ai_message = AIMessage(content=response_text)
                
                # Add metadata for compatibility with the rest of the system
                ai_message.response_metadata = {"model_name": "llama3.3", "finish_reason": "stop"}
                ai_message.id = "local_model_response"
                ai_message.usage_metadata = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}
                
                # Log the request
                parsed_reply = self.parse_llmresult(ai_message)
                LLMLogger.log_request(prompts=messages, parsed_reply=parsed_reply)
                
                return ai_message
                
            except Exception as e:
                logger.error(f"Error occurred when calling LLM: {str(e)}")
                if attempt < max_retries - 1:
                    logger.info(f"Retrying in {retry_delay} seconds... (Attempt {attempt+1}/{max_retries})")
                    time.sleep(retry_delay)
                    retry_delay *= 2
                else:
                    logger.critical("All retry attempts failed")
                    raise

        logger.critical(f"Failed to get a response from the model after {max_retries} attempts")
        raise Exception(f"Failed to get a response from the model after {max_retries} attempts")

    def parse_llmresult(self, llmresult: AIMessage) -> Dict[str, Dict]:
        """Parse LLM result into a standardized format."""
        try:
            content = llmresult.content
            
            # Use metadata if available, otherwise use defaults
            if hasattr(llmresult, 'response_metadata') and llmresult.response_metadata:
                response_metadata = llmresult.response_metadata
            else:
                response_metadata = {"model_name": "llama3.3", "finish_reason": "stop"}
                
            if hasattr(llmresult, 'id') and llmresult.id:
                id_ = llmresult.id
            else:
                id_ = "local_model_response"
                
            if hasattr(llmresult, 'usage_metadata') and llmresult.usage_metadata:
                usage_metadata = llmresult.usage_metadata
            else:
                usage_metadata = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}

            parsed_result = {
                "content": content,
                "response_metadata": {
                    "model_name": response_metadata.get("model_name", "llama3.3"),
                    "system_fingerprint": response_metadata.get("system_fingerprint", ""),
                    "finish_reason": response_metadata.get("finish_reason", "stop"),
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
        except Exception as e:
            logger.error(f"Error parsing LLM result: {str(e)}")
            # Return a default structure when parsing fails
            return {
                "content": str(llmresult),
                "response_metadata": {
                    "model_name": "llama3.3",
                    "system_fingerprint": "",
                    "finish_reason": "stop",
                    "logprobs": None,
                },
                "id": "error_parsing_response",
                "usage_metadata": {
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "total_tokens": 0,
                },
            }
