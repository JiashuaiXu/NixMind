"""
Ollama client implementation for NixMind.
"""

import asyncio
import aiohttp
import json
from typing import List, Dict, Any, Optional
import logging

from .base import BaseLLM, LLMResponse, Message


class OllamaClient(BaseLLM):
    """Ollama LLM client implementation."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize Ollama client."""
        super().__init__(config)
        self.api_base = config.get("api_base", "http://localhost:11434")
        self.logger = logging.getLogger(__name__)
    
    async def generate(
        self,
        messages: List[Message],
        **kwargs
    ) -> LLMResponse:
        """Generate a response using Ollama."""
        url = f"{self.api_base}/api/chat"
        
        # Convert messages to Ollama format
        ollama_messages = [
            {"role": msg.role, "content": msg.content}
            for msg in messages
        ]
        
        payload = {
            "model": self.model_name,
            "messages": ollama_messages,
            "stream": False,
            "options": {
                "temperature": self.temperature,
                "num_predict": self.max_tokens,
            }
        }
        
        # Add any additional options from kwargs
        if "temperature" in kwargs:
            payload["options"]["temperature"] = kwargs["temperature"]
        if "max_tokens" in kwargs:
            payload["options"]["num_predict"] = kwargs["max_tokens"]
        
        try:
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(url, json=payload) as response:
                    if response.status == 200:
                        data = await response.json()
                        return LLMResponse(
                            content=data["message"]["content"],
                            model=data.get("model", self.model_name),
                            usage=data.get("usage"),
                            metadata=data
                        )
                    else:
                        error_text = await response.text()
                        raise Exception(f"Ollama API error {response.status}: {error_text}")
        
        except asyncio.TimeoutError:
            raise Exception(f"Ollama request timed out after {self.timeout} seconds")
        except aiohttp.ClientError as e:
            raise Exception(f"Ollama client error: {e}")
        except Exception as e:
            self.logger.error(f"Error generating response from Ollama: {e}")
            raise
    
    async def is_available(self) -> bool:
        """Check if Ollama service is available."""
        url = f"{self.api_base}/api/tags"
        
        try:
            timeout = aiohttp.ClientTimeout(total=5)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url) as response:
                    return response.status == 200
        except Exception:
            return False
    
    async def list_models(self) -> List[str]:
        """List available models from Ollama."""
        url = f"{self.api_base}/api/tags"
        
        try:
            timeout = aiohttp.ClientTimeout(total=10)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        return [model["name"] for model in data.get("models", [])]
                    else:
                        return []
        except Exception as e:
            self.logger.error(f"Error listing Ollama models: {e}")
            return []
    
    async def pull_model(self, model_name: str) -> bool:
        """Pull a model from Ollama registry."""
        url = f"{self.api_base}/api/pull"
        
        payload = {"name": model_name}
        
        try:
            timeout = aiohttp.ClientTimeout(total=300)  # 5 minutes for model download
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(url, json=payload) as response:
                    if response.status == 200:
                        # Stream the pull progress (for now just wait for completion)
                        async for line in response.content:
                            if line:
                                try:
                                    status = json.loads(line)
                                    if status.get("status") == "success":
                                        return True
                                except json.JSONDecodeError:
                                    continue
                        return True
                    else:
                        return False
        except Exception as e:
            self.logger.error(f"Error pulling Ollama model {model_name}: {e}")
            return False