"""Base Agent class using Google Vertex AI Gemini API.

Provides common functionality for all specialized agents including
LLM interaction, memory access, and structured output handling.
"""

import json
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, Generic, Optional, Type, TypeVar

from google import genai
from google.genai import types
from pydantic import BaseModel

from ..config import settings
from ..rag.memory_store import MemoryStore

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


class BaseAgent(ABC, Generic[T]):
    """Abstract base class for all agents in the system.
    
    Provides:
    - Integration with Google Gemini API
    - Access to shared RAG memory store
    - Structured output parsing with Pydantic
    - Retry logic and error handling
    
    Subclasses must implement:
    - agent_name: Descriptive name for logging
    - system_prompt: Instructions for the agent's behavior
    - output_schema: Pydantic model for structured output
    """
    
    # Model configuration
    DEFAULT_MODEL = "gemini-2.0-flash"
    DEFAULT_TEMPERATURE = 0.7
    MAX_RETRIES = 3
    
    def __init__(
        self,
        memory: Optional[MemoryStore] = None,
        model_name: Optional[str] = None,
        temperature: Optional[float] = None,
    ):
        """Initialize the agent.
        
        Args:
            memory: Shared memory store. Creates new instance if None.
            model_name: Gemini model to use. Defaults to gemini-2.0-flash.
            temperature: Generation temperature. Defaults to 0.7.
        """
        self._memory = memory or MemoryStore()
        self._model_name = model_name or self.DEFAULT_MODEL
        self._temperature = temperature or self.DEFAULT_TEMPERATURE
        
        # Initialize Gemini client
        if settings.google_cloud_project:
            self._client = genai.Client(
                vertexai=True,
                project=settings.google_cloud_project,
                location=settings.google_cloud_location
            )
        else:
            self._client = genai.Client(api_key=settings.google_api_key)
        
        logger.info(f"Initialized {self.agent_name} with model {self._model_name}")
    
    @property
    @abstractmethod
    def agent_name(self) -> str:
        """Return the agent's descriptive name."""
        pass
    
    @property
    @abstractmethod
    def system_prompt(self) -> str:
        """Return the system prompt that defines agent behavior."""
        pass
    
    @property
    @abstractmethod
    def output_schema(self) -> Type[T]:
        """Return the Pydantic model for structured output."""
        pass
    
    @property
    def memory(self) -> MemoryStore:
        """Access the shared memory store."""
        return self._memory
    
    def _build_generation_config(self) -> types.GenerateContentConfig:
        """Build the generation configuration for Gemini API."""
        return types.GenerateContentConfig(
            temperature=self._temperature,
            system_instruction=self.system_prompt,
            response_mime_type="application/json",
            response_schema=self.output_schema,
        )
    
    async def generate(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> T:
        """Generate a response using the LLM.
        
        Args:
            prompt: The user prompt / task description
            context: Additional context to include in the prompt
            
        Returns:
            Parsed output matching the output_schema
            
        Raises:
            ValueError: If response cannot be parsed after retries
        """
        # Build full prompt with context
        full_prompt = prompt
        if context:
            context_str = json.dumps(context, indent=2, default=str)
            full_prompt = f"Context:\n{context_str}\n\nTask:\n{prompt}"
        
        logger.debug(f"{self.agent_name} generating response for prompt: {prompt[:100]}...")
        
        for attempt in range(self.MAX_RETRIES):
            try:
                response = await self._client.aio.models.generate_content(
                    model=self._model_name,
                    contents=full_prompt,
                    config=self._build_generation_config(),
                )
                
                # Parse the JSON response
                response_text = response.text
                parsed = self.output_schema.model_validate_json(response_text)
                
                logger.debug(f"{self.agent_name} successfully generated response")
                return parsed
                
            except json.JSONDecodeError as e:
                logger.warning(f"{self.agent_name} JSON parse error (attempt {attempt + 1}): {e}")
                if attempt == self.MAX_RETRIES - 1:
                    raise ValueError(f"Failed to parse response after {self.MAX_RETRIES} attempts")
                    
            except Exception as e:
                logger.error(f"{self.agent_name} generation error (attempt {attempt + 1}): {e}")
                if attempt == self.MAX_RETRIES - 1:
                    raise
        
        raise ValueError("Generation failed")
    
    def generate_sync(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> T:
        """Synchronous version of generate().
        
        Args:
            prompt: The user prompt / task description
            context: Additional context to include in the prompt
            
        Returns:
            Parsed output matching the output_schema
        """
        # Build full prompt with context
        full_prompt = prompt
        if context:
            context_str = json.dumps(context, indent=2, default=str)
            full_prompt = f"Context:\n{context_str}\n\nTask:\n{prompt}"
        
        logger.debug(f"{self.agent_name} generating response (sync)...")
        
        for attempt in range(self.MAX_RETRIES):
            try:
                response = self._client.models.generate_content(
                    model=self._model_name,
                    contents=full_prompt,
                    config=self._build_generation_config(),
                )
                
                response_text = response.text
                parsed = self.output_schema.model_validate_json(response_text)
                
                logger.debug(f"{self.agent_name} successfully generated response")
                return parsed
                
            except json.JSONDecodeError as e:
                logger.warning(f"{self.agent_name} JSON parse error (attempt {attempt + 1}): {e}")
                if attempt == self.MAX_RETRIES - 1:
                    raise ValueError(f"Failed to parse response after {self.MAX_RETRIES} attempts")
                    
            except Exception as e:
                logger.error(f"{self.agent_name} generation error (attempt {attempt + 1}): {e}")
                if attempt == self.MAX_RETRIES - 1:
                    raise
        
        raise ValueError("Generation failed")
    
    def query_memory(self, query: str, collection: str = "curriculum", limit: int = 5) -> list:
        """Query the memory store for relevant information.
        
        Args:
            query: Search query
            collection: Collection to search
            limit: Maximum results
            
        Returns:
            List of relevant documents
        """
        # Use the appropriate search method based on collection
        if collection == "curriculum":
            return self._memory.search_topic_plans(query, limit)
        else:
            logger.warning(f"Query for collection '{collection}' not implemented")
            return []
