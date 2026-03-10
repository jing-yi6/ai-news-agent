"""
LLM Provider 抽象基类
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class Message:
    """统一的消息格式"""
    role: str  # "system", "user", "assistant"
    content: str


@dataclass(frozen=True, slots=True)
class LLMResponse:
    """统一的 LLM 响应格式"""
    content: str
    prompt_tokens: int
    completion_tokens: int
    model: str

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens


class BaseLLMProvider(ABC):
    """LLM Provider 抽象基类"""

    def __init__(self, api_key: str, base_url: str, model: str, **kwargs):
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
        self.extra_config = kwargs
        self._client: Any = None

    @abstractmethod
    def chat_complete(self, messages: list[Message], **kwargs) -> LLMResponse:
        """统一对话接口"""
        raise NotImplementedError

    @classmethod
    @abstractmethod
    def is_available(cls) -> bool:
        """检查 provider 是否可用（依赖库是否安装）"""
        raise NotImplementedError

    def _get_client(self):
        """延迟初始化客户端"""
        if self._client is None:
            self._client = self._init_client()
        return self._client

    @abstractmethod
    def _init_client(self) -> Any:
        """初始化客户端（子类实现）"""
        raise NotImplementedError
