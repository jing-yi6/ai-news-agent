"""
Anthropic Provider
支持 Claude 系列模型
"""
from typing import Any

from providers.base import BaseLLMProvider, Message, LLMResponse


class AnthropicProvider(BaseLLMProvider):
    """Anthropic Claude Provider"""

    @classmethod
    def is_available(cls) -> bool:
        try:
            import anthropic
            return True
        except ImportError:
            return False

    def _init_client(self) -> Any:
        import anthropic
        return anthropic.Anthropic(api_key=self.api_key)

    def chat_complete(self, messages: list[Message], **kwargs) -> LLMResponse:
        client = self._get_client()

        # 分离 system 和对话消息
        system_msg = None
        chat_messages = []

        for msg in messages:
            if msg.role == "system":
                system_msg = msg.content
            else:
                chat_messages.append({"role": msg.role, "content": msg.content})

        api_kwargs = {
            "model": self.model,
            "messages": chat_messages,
            "max_tokens": kwargs.get("max_tokens", 1000),
            "temperature": kwargs.get("temperature", 0.3),
        }
        if system_msg:
            api_kwargs["system"] = system_msg

        response = client.messages.create(**api_kwargs)

        return LLMResponse(
            content=response.content[0].text,
            prompt_tokens=response.usage.input_tokens,
            completion_tokens=response.usage.output_tokens,
            model=self.model
        )
