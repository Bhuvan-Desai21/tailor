"""
LLM Service - Central LLM Orchestration

Provides a unified interface to multiple LLM providers via LiteLLM.
Features:
- Category-based model selection
- Ollama auto-detection
- Streaming support
- Automatic API key injection from keyring
"""

import os
import json
import asyncio
from pathlib import Path
from typing import Optional, List, Dict, Any, AsyncGenerator, Union
from dataclasses import dataclass, field

from loguru import logger

import litellm
from litellm import acompletion

try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False

from .keyring_service import get_keyring_service, PROVIDERS


@dataclass
class ModelInfo:
    """Information about an available model."""
    id: str
    name: str
    provider: str
    categories: List[str]
    context_window: Optional[int] = None
    is_local: bool = False


@dataclass  
class OllamaModel:
    """Information about an Ollama model."""
    name: str
    size: str
    modified_at: str
    digest: str


@dataclass
class LLMResponse:
    """Response from an LLM completion."""
    content: str
    model: str
    usage: Dict[str, int] = field(default_factory=dict)
    finish_reason: Optional[str] = None


class LLMService:
    """
    Central LLM orchestration service.
    
    Handles:
    - Model selection by category
    - Provider authentication
    - Ollama detection
    - Streaming completions
    """
    

    
    def __init__(self, vault_path: Path, config: Dict[str, Any]):
        self._logger = logger.bind(component="LLMService")
        self.vault_path = vault_path
        self.config = config
        
        # Load models registry
        self._registry = self._load_registry()
        
        # Initialize keyring and set env vars
        self._keyring = get_keyring_service()
        self._keyring.set_env_vars()
        
        # Category configuration from vault config
        self._categories = config.get("categories", {})
        self._defaults = config.get("defaults", {
            "temperature": 0.7,
            "max_tokens": 4096
        })
        
        # Cached Ollama models
        self._ollama_models: Optional[List[OllamaModel]] = None
        self._ollama_available: Optional[bool] = None
        

    
    def _load_registry(self) -> Dict[str, Any]:
        """Load the models registry JSON."""
        registry_path = Path(__file__).parent.parent / "models_registry.json"
        try:
            with open(registry_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            self._logger.error(f"Failed to load models registry: {e}")
            return {"recommended": {}, "categories": {}}

    async def _fetch_litellm_data(self) -> Dict[str, Any]:
        """Fetch model data from LiteLLM source."""
        # Use local litellm.model_cost instead of fetching
        return litellm.model_cost
    
    # =========================================================================
    # Ollama Detection
    # =========================================================================
    
    async def detect_ollama(self, force_refresh: bool = False) -> List[OllamaModel]:
        """
        Detect if Ollama is running and list available models.
        
        Args:
            force_refresh: If True, bypass cache and re-detect
            
        Returns:
            List of available Ollama models
        """
        if not force_refresh and self._ollama_models is not None:
            return self._ollama_models
        
        if not HTTPX_AVAILABLE:
            self._ollama_available = False
            self._ollama_models = []
            return []
        
        base_url = self.config.get("providers", {}).get("ollama", {}).get(
            "base_url", "http://localhost:11434"
        )
        
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{base_url}/api/tags")
                
                if response.status_code == 200:
                    data = response.json()
                    models = []
                    for model in data.get("models", []):
                        models.append(OllamaModel(
                            name=model.get("name", ""),
                            size=self._format_size(model.get("size", 0)),
                            modified_at=model.get("modified_at", ""),
                            digest=model.get("digest", "")[:12]
                        ))
                    
                    self._ollama_available = True
                    self._ollama_models = models
                    self._logger.info(f"Ollama detected with {len(models)} models")
                    return models
                else:
                    self._ollama_available = False
                    self._ollama_models = []
                    return []
                    
        except Exception as e:
            self._logger.debug(f"Ollama not detected: {e}")
            self._ollama_available = False
            self._ollama_models = []
            return []
    
    def _format_size(self, size_bytes: int) -> str:
        """Format bytes to human readable size."""
        for unit in ["B", "KB", "MB", "GB"]:
            if size_bytes < 1024:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.1f} TB"
    
    def _get_ollama_categories(self, model_name: str) -> List[str]:
        """
        Determine categories for an Ollama model based on its name.
        Uses keywords defined in the registry categories.
        """
        name_lower = model_name.lower().split(":")[0]
        matched_categories = set()
        
        categories_config = self._registry.get("categories", {})
        
        for category_id, config in categories_config.items():
            keywords = config.get("ollama_keywords", [])
            for keyword in keywords:
                if keyword in name_lower:
                    matched_categories.add(category_id)
                    break # One match per category is enough

        return list(matched_categories) or ["fast"]
    
    async def is_ollama_available(self) -> bool:
        """Check if Ollama is running."""
        if self._ollama_available is None:
            await self.detect_ollama()
        return self._ollama_available or False
    
    # =========================================================================
    # Model Discovery
    # =========================================================================
    
    async def get_available_models(self) -> Dict[str, List[ModelInfo]]:
        """
        Get all models available to the user grouped by provider.
        
        Returns:
            Dict mapping provider IDs to lists of available models
        """
        available = {}
        configured_providers = self._keyring.list_configured_providers()
        
        # Fetch LiteLLM data (could be cached)
        litellm_data = await self._fetch_litellm_data()
        
        # Get recommended models by category from the new structure
        categories_config = self._registry.get("categories", {})
        
        # Invert recommended to get list of used models
        used_models = set()
        model_to_categories = {}
        
        for cat_id, config in categories_config.items():
            recs = config.get("recommended", [])
            for model_id in recs:
                used_models.add(model_id)
                if model_id not in model_to_categories:
                    model_to_categories[model_id] = []
                model_to_categories[model_id].append(cat_id)
            
        # Group by provider (heuristic based on model name)
        for model_id in used_models:
            # Simple heuristic for provider
            if "gpt" in model_id or "text-embedding" in model_id or "whisper" in model_id:
                provider = "openai"
            elif "claude" in model_id:
                provider = "anthropic"
            elif "gemini" in model_id:
                provider = "google"
            elif "mistral" in model_id or "codestral" in model_id:
                provider = "mistral"
            elif "llama" in model_id:
                provider = "groq" # Defaulting Llama to Groq for now
            else:
                provider = "unknown"

            # Get specs from LiteLLM data if available
            specs = litellm_data.get(model_id, {})
            
            categories = model_to_categories.get(model_id, [])

            model_info = ModelInfo(
                id=model_id,
                name=model_id, # Can improve with formatted name
                provider=provider,
                categories=categories,
                context_window=specs.get("max_input_tokens") or specs.get("max_tokens"),
                is_local=False
            )
            
            if provider not in available:
                available[provider] = []
            available[provider].append(model_info)
        
        # Add Ollama models
        ollama_models = await self.detect_ollama()
        if ollama_models:
            ollama_list = []
            for model in ollama_models:
                ollama_list.append(ModelInfo(
                    id=model.name,
                    name=model.name,
                    provider="ollama",
                    categories=self._get_ollama_categories(model.name),
                    context_window=None,
                    is_local=True
                ))
            available["ollama"] = ollama_list
        
        return available
    
    async def get_models_for_category(self, category: str) -> List[ModelInfo]:
        """
        Get all available models that support a specific category.
        
        Args:
            category: Category ID (e.g., 'thinking', 'fast')
            
        Returns:
            List of models that support this category
        """
        all_models = await self.get_available_models()
        matching = []
        
        for provider_models in all_models.values():
            for model in provider_models:
                if category in model.categories:
                    matching.append(model)
        
        return matching
    
    def get_model_for_category(self, category: str) -> Optional[str]:
        """
        Get the configured model for a category.
        
        Args:
            category: Category ID
            
        Returns:
            Model ID in format 'provider/model' or None
        """
        # Check user configuration
        model = self._categories.get(category)
        if model:
            return model
        
        # Check for fallback
        category_info = self._registry.get("categories", {}).get(category, {})
        fallback = category_info.get("fallback")
        if fallback:
            return self.get_model_for_category(fallback)
        
        return None
    
    # =========================================================================
    # LLM Completions
    # =========================================================================
    
    async def complete(
        self,
        messages: List[Dict[str, str]],
        category: str = "fast",
        model: Optional[str] = None,
        stream: bool = False,
        **kwargs
    ) -> Union[LLMResponse, AsyncGenerator[str, None]]:
        """
        Generate a completion using the appropriate model.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            category: Model category to use (if model not specified)
            model: Specific model ID to use (overrides category)
            stream: If True, return an async generator of tokens
            **kwargs: Additional parameters passed to LiteLLM
            
        Returns:
            LLMResponse or AsyncGenerator if streaming
        """

        
        # Determine model to use
        model_id = model or self.get_model_for_category(category)
        if not model_id:
            raise ValueError(f"No model configured for category: {category}")
        
        # Format model for LiteLLM (provider/model format)
        litellm_model = self._format_model_for_litellm(model_id)
        
        # Merge defaults with kwargs
        params = {
            "temperature": self._defaults.get("temperature", 0.7),
            "max_tokens": self._defaults.get("max_tokens", 4096),
            **kwargs
        }
        
        self._logger.debug(f"Completing with model: {litellm_model}")
        
        if stream:
            return self._stream_completion(litellm_model, messages, params)
        else:
            return await self._sync_completion(litellm_model, messages, params)
    
    async def _sync_completion(
        self,
        model: str,
        messages: List[Dict[str, str]],
        params: Dict[str, Any]
    ) -> LLMResponse:
        """Synchronous (non-streaming) completion."""
        try:
            response = await acompletion(
                model=model,
                messages=messages,
                **params
            )
            
            return LLMResponse(
                content=response.choices[0].message.content or "",
                model=model,
                usage={
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens
                } if response.usage else {},
                finish_reason=response.choices[0].finish_reason
            )
        except Exception as e:
            self._logger.error(f"Completion failed: {e}")
            raise
    
    async def _stream_completion(
        self,
        model: str,
        messages: List[Dict[str, str]],
        params: Dict[str, Any]
    ) -> AsyncGenerator[str, None]:
        """Streaming completion - yields tokens as they arrive."""
        try:
            response = await acompletion(
                model=model,
                messages=messages,
                stream=True,
                **params
            )
            
            async for chunk in response:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
                    
        except Exception as e:
            self._logger.error(f"Stream completion failed: {e}")
            raise
    
    def _format_model_for_litellm(self, model_id: str) -> str:
        """
        Format a model ID for LiteLLM.
        
        If already in 'provider/model' format, return as-is.
        Otherwise, try to infer the provider.
        """
        if "/" in model_id:
            return model_id
        
        # Heuristic for provider prefixes
        if "gpt" in model_id or "text-embedding" in model_id or "whisper" in model_id:
            return f"openai/{model_id}"
        elif "claude" in model_id:
            return f"anthropic/{model_id}"
        elif "gemini" in model_id:
            return f"google/{model_id}"
        elif "mistral" in model_id or "codestral" in model_id:
            return f"mistral/{model_id}"
        elif "llama" in model_id and "ollama" not in model_id:
             # Default Llama to Groq unless it's Ollama
            return f"groq/{model_id}"

        # Check if it's an Ollama model
        if self._ollama_models:
            for m in self._ollama_models:
                if m.name == model_id or m.name.startswith(model_id):
                    return f"ollama/{model_id}"
        
        # Return as-is and let LiteLLM figure it out
        return model_id
    
    # =========================================================================
    # Configuration
    # =========================================================================
    
    def set_category_model(self, category: str, model: str) -> None:
        """
        Set the model for a category (in memory).
        
        Note: Call save_config() to persist to .vault.json
        """
        self._categories[category] = model
    
    def get_category_config(self) -> Dict[str, str]:
        """Get current category configuration."""
        return dict(self._categories)
    
    def get_categories_info(self) -> Dict[str, Dict[str, Any]]:
        """Get metadata about all categories."""
        return self._registry.get("categories", {})


# Module-level singleton
_llm_service: Optional[LLMService] = None


def get_llm_service(vault_path: Optional[Path] = None, config: Optional[Dict] = None) -> LLMService:
    """Get the singleton LLMService instance."""
    global _llm_service
    if _llm_service is None:
        if vault_path is None or config is None:
            raise RuntimeError("LLMService not initialized. Provide vault_path and config.")
        _llm_service = LLMService(vault_path, config)
    return _llm_service


def reset_llm_service() -> None:
    """Reset the singleton (for testing or vault restart)."""
    global _llm_service
    _llm_service = None
