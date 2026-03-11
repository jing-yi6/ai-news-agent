"""
X (Twitter) 数据源实现 - 使用 twscrape
"""
import asyncio
import logging
from typing import AsyncIterator

from datasources.base import BaseDataSource, ContentItem
from datasources.clients import XClient, Tweet, User

logger = logging.getLogger(__name__)


class XDataSource(BaseDataSource):
    """X (Twitter) 数据源 - 使用 twscrape 抓取"""

    def __init__(self, config: dict):
        super().__init__(config)
        self._client = None
        # 从配置中获取账号信息
        self._account_config = {
            "username": config.get("username"),
            "password": config.get("password"),
            "email": config.get("email"),
            "email_password": config.get("email_password"),
            "cookies": config.get("cookies"),
        }

    def _get_client(self):
        if self._client is None:
            # 检查是否有账号配置
            if not any(self._account_config.values()):
                raise ValueError(
                    "X 数据源需要账号配置。请提供以下之一:\n"
                    "  - cookies + username: 在 .env 中设置 X_USERNAME 和 X_COOKIES\n"
                    "  - username + password: 在 .env 中设置 X_USERNAME 和 X_PASSWORD"
                )
            # 获取速率限制配置（默认 1.0 秒/次）
            rate_limit = self.config.get("rate_limit", 1.0)
            self._client = XClient(account_config=self._account_config, rate_limit=float(rate_limit))
        return self._client

    def _tweet_to_item(self, tweet: Tweet) -> ContentItem:
        """将 Tweet 转换为 ContentItem"""
        return ContentItem(
            id=tweet.id,
            content=tweet.text,
            author_id=tweet.author_id,
            author_name=tweet.author_name,
            author_username=tweet.author_username,
            created_at=tweet.created_at,
            url=f"https://x.com/{tweet.author_username}/status/{tweet.id}",
            source="x",  # 标记数据来源
            likes=tweet.like_count,
            replies=tweet.reply_count,
            retweets=tweet.retweet_count,
            quotes=tweet.quote_count,
        )

    async def fetch_by_users(self, usernames: list[str], **kwargs) -> AsyncIterator[ContentItem]:
        """异步获取指定用户的推文"""
        client = self._get_client()
        max_results = kwargs.get("max_results", 10)
        start_time = kwargs.get("start_time")
        end_time = kwargs.get("end_time")

        async def fetch_single_user(username: str) -> list[Tweet]:
            """获取单个用户的推文"""
            username = username.lstrip("@")
            user = await client.get_user_by_username(username)
            if not user:
                logger.warning(f"Could not find user @{username}")
                return []
            return await client.get_user_tweets(
                user_id=user.id,
                max_results=max_results,
                start_time=start_time,
                end_time=end_time
            )

        # 并行获取所有用户的推文
        tasks = [fetch_single_user(username) for username in usernames]
        results = await asyncio.gather(*tasks)

        for tweets in results:
            for tweet in tweets:
                yield self._tweet_to_item(tweet)

    async def fetch_by_followings(self, user_id: str, **kwargs) -> AsyncIterator[ContentItem]:
        """异步获取关注列表的推文"""
        client = self._get_client()
        max_following = kwargs.get("max_following", 50)
        tweets_per_user = kwargs.get("tweets_per_user", 10)
        start_time = kwargs.get("start_time")
        end_time = kwargs.get("end_time")

        following = await client.get_user_following(user_id, max_results=max_following)

        async def fetch_user_tweets(user: User) -> list[Tweet]:
            """获取单个关注用户的推文"""
            return await client.get_user_tweets(
                user_id=user.id,
                max_results=tweets_per_user,
                start_time=start_time,
                end_time=end_time
            )

        # 并行获取所有关注用户的推文
        tasks = [fetch_user_tweets(user) for user in following]
        results = await asyncio.gather(*tasks)

        for tweets in results:
            for tweet in tweets:
                yield self._tweet_to_item(tweet)

    async def get_user_id(self, username: str) -> str | None:
        """异步获取用户 ID"""
        client = self._get_client()
        user = await client.get_user_by_username(username.lstrip("@"))
        return user.id if user else None
