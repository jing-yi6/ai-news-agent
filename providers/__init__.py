"""
LLM Provider 工厂
"""
from providers.base import BaseLLMProvider, Message, LLMResponse
from providers.openai_provider import OpenAIProvider
from providers.anthropic_provider import AnthropicProvider

# Provider 注册表
PROVIDER_REGISTRY: dict[str, type[BaseLLMProvider]] = {
    "openai": OpenAIProvider,
    "anthropic": AnthropicProvider,
}


def create_llm_provider(
    provider_type: str,
    api_key: str,
    base_url: str,
    model: str,
    **kwargs
) -> BaseLLMProvider:
    """创建 LLM Provider 实例"""
    provider_type = provider_type.lower()

    if provider_type not in PROVIDER_REGISTRY:
        available = ", ".join(PROVIDER_REGISTRY.keys())
        raise ValueError(f"Unknown provider: {provider_type}. Available: {available}")

    provider_class = PROVIDER_REGISTRY[provider_type]
    return provider_class(api_key, base_url, model, **kwargs)


def list_available_providers() -> list[str]:
    """列出可用的 provider"""
    return [
        name for name, provider_class in PROVIDER_REGISTRY.items()
        if provider_class.is_available()
    ]


def auto_detect_provider(api_key: str, model: str) -> BaseLLMProvider | None:
    """根据 API key 自动检测 Provider"""
    if api_key.startswith("sk-ant") and AnthropicProvider.is_available():
        return AnthropicProvider(api_key, "", model)

    if OpenAIProvider.is_available():
        return OpenAIProvider(api_key, "", model)

    return None


__all__ = [
    "BaseLLMProvider",
    "Message",
    "LLMResponse",
    "OpenAIProvider",
    "AnthropicProvider",
    "create_llm_provider",
    "list_available_providers",
    "auto_detect_provider",
    "PROVIDER_REGISTRY",
]
