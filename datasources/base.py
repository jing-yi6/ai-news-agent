"""
数据源抽象基类
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import AsyncIterator


@dataclass(frozen=True, slots=True)
class ContentItem:
    """统一的内容项数据结构"""
    id: str
    content: str
    author_id: str
    author_name: str
    author_username: str
    created_at: datetime
    url: str
    likes: int = 0
    replies: int = 0
    retweets: int = 0
    quotes: int = 0

    @property
    def engagement_score(self) -> int:
        """计算互动分数"""
        return self.likes + self.replies + self.retweets + self.quotes


class BaseDataSource(ABC):
    """数据源抽象基类"""

    def __init__(self, config: dict):
        self.config = config

    @abstractmethod
    async def fetch_by_users(self, usernames: list[str], **kwargs) -> AsyncIterator[ContentItem]:
        """异步获取指定用户的内容"""
        raise NotImplementedError

    @abstractmethod
    async def fetch_by_followings(self, user_id: str, **kwargs) -> AsyncIterator[ContentItem]:
        """异步获取用户关注列表的内容"""
        raise NotImplementedError

    @abstractmethod
    async def get_user_id(self, username: str) -> str | None:
        """异步将用户名转换为用户 ID"""
        raise NotImplementedError
