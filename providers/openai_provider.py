"""
OpenAI 兼容格式 Provider
支持 OpenAI、Azure、Ollama、vLLM、OpenRouter 等
"""
from typing import Any

from providers.base import BaseLLMProvider, Message, LLMResponse


class OpenAIProvider(BaseLLMProvider):
    """OpenAI 兼容格式 Provider"""

    @classmethod
    def is_available(cls) -> bool:
        try:
            import openai
            return True
        except ImportError:
            return False

    def _init_client(self) -> Any:
        import openai
        client_kwargs = {"api_key": self.api_key}
        if self.base_url:
            client_kwargs["base_url"] = self.base_url
        return openai.OpenAI(**client_kwargs)

    def chat_complete(self, messages: list[Message], **kwargs) -> LLMResponse:
        client = self._get_client()

        response = client.chat.completions.create(
            model=self.model,
            messages=[{"role": m.role, "content": m.content} for m in messages],
            max_tokens=kwargs.get("max_tokens", 1000),
            temperature=kwargs.get("temperature", 0.3),
        )

        return LLMResponse(
            content=response.choices[0].message.content,
            prompt_tokens=response.usage.prompt_tokens,
            completion_tokens=response.usage.completion_tokens,
            model=self.model
        )
