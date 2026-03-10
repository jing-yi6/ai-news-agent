"""
模拟数据源，用于测试
"""
from datetime import datetime, timedelta, timezone
from typing import Iterator

from datasources.base import BaseDataSource, ContentItem


class MockDataSource(BaseDataSource):
    """模拟数据源"""

    def __init__(self, config: dict | None = None):
        super().__init__(config or {})

    def _generate_items(self) -> list[ContentItem]:
        """生成模拟数据"""
        now = datetime.now(timezone.utc)

        data = [
            ("OpenAI", "OpenAI", "GPT-5 preview with significant improvements in reasoning and coding"),
            ("DeepMind", "Google DeepMind", "AlphaFold 3 breakthrough in protein structure prediction"),
            ("karpathy", "Andrej Karpathy", "New tutorial on building LLMs from scratch"),
            ("AnthropicAI", "Anthropic", "Claude 3.5 Sonnet with enhanced coding abilities"),
            ("huggingface", "Hugging Face", "Mixtral 8x22B, Qwen2-72B, and Llama 3 70B added"),
        ]

        items = []
        for i, (username, name, text) in enumerate(data):
            items.append(ContentItem(
                id=f"{i}000000000",
                content=text,
                author_id=f"user_{i}",
                author_name=name,
                author_username=username,
                created_at=now - timedelta(hours=i * 2),
                url=f"https://x.com/{username}/status/{i}000000000",
                likes=10000 - i * 1000,
                retweets=3000 - i * 500,
            ))

        return items

    def fetch_by_users(self, usernames: list[str], **kwargs) -> Iterator[ContentItem]:
        """获取指定用户的内容"""
        username_set = {u.lstrip("@").lower() for u in usernames}
        for item in self._generate_items():
            if item.author_username.lower() in username_set:
                yield item

    def fetch_by_followings(self, user_id: str, **kwargs) -> Iterator[ContentItem]:
        """获取所有模拟内容"""
        yield from self._generate_items()

    def get_user_id(self, username: str) -> str | None:
        """模拟获取用户 ID"""
        return username.lstrip("@").lower()
