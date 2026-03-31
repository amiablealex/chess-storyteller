"""
LLM Provider abstraction layer.
Each provider implements the same interface — swap freely via config.
"""

from abc import ABC, abstractmethod
from typing import Optional


class LLMProvider(ABC):
    """Base class for all LLM providers."""

    def __init__(self, api_key: str, model: str, max_tokens: int = 4096, temperature: float = 0.7):
        self.api_key = api_key
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature

    @abstractmethod
    def generate(self, system_prompt: str, user_prompt: str) -> str:
        """Generate a response given system and user prompts. Returns the text content."""
        pass

    @property
    @abstractmethod
    def provider_name(self) -> str:
        pass


# Provider registry
_PROVIDERS: dict[str, type[LLMProvider]] = {}


def register_provider(name: str):
    """Decorator to register a provider class."""
    def decorator(cls):
        _PROVIDERS[name] = cls
        return cls
    return decorator


def get_provider(config: dict) -> LLMProvider:
    """Instantiate the configured LLM provider."""
    llm_config = config["llm"]
    provider_name = llm_config["provider"]

    if provider_name not in _PROVIDERS:
        available = ", ".join(_PROVIDERS.keys())
        raise ValueError(f"Unknown LLM provider '{provider_name}'. Available: {available}")

    cls = _PROVIDERS[provider_name]
    return cls(
        api_key=llm_config["api_key"],
        model=llm_config["model"],
        max_tokens=llm_config.get("max_tokens", 4096),
        temperature=llm_config.get("temperature", 0.7),
    )


# Import all providers so they self-register
from providers import anthropic_provider, openai_provider, google_provider
