"""
Base LLM interface for NixMind.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import asyncio


@dataclass
class LLMResponse:
    """Response from an LLM."""
    content: str
    model: str
    usage: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class Message:
    """A message in a conversation."""
    role: str  # "system", "user", "assistant"
    content: str
    metadata: Optional[Dict[str, Any]] = None


class BaseLLM(ABC):
    """Base class for all LLM providers."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize the LLM with configuration."""
        self.config = config
        self.model_name = config.get("model_name", "default")
        self.temperature = config.get("temperature", 0.1)
        self.max_tokens = config.get("max_tokens", 2048)
        self.timeout = config.get("timeout", 60)
    
    @abstractmethod
    async def generate(
        self,
        messages: List[Message],
        **kwargs
    ) -> LLMResponse:
        """Generate a response from the LLM."""
        pass
    
    @abstractmethod
    async def is_available(self) -> bool:
        """Check if the LLM service is available."""
        pass
    
    @abstractmethod
    async def list_models(self) -> List[str]:
        """List available models."""
        pass
    
    def create_system_message(self, content: str) -> Message:
        """Create a system message."""
        return Message(role="system", content=content)
    
    def create_user_message(self, content: str) -> Message:
        """Create a user message."""
        return Message(role="user", content=content)
    
    def create_assistant_message(self, content: str) -> Message:
        """Create an assistant message."""
        return Message(role="assistant", content=content)