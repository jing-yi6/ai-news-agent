"""
X (Twitter) 数据源实现 - 使用 twscrape
"""
from typing import Iterator

from datasources.base import BaseDataSource, ContentItem
from datasources.clients import XClient, Tweet, User


class XDataSource(BaseDataSource):
    """X (Twitter) 数据源 - 使用 twscrape 抓取"""

    def __init__(self, config: dict):
        super().__init__(config)
        self._client = None
        # 从配置中获取账号信息
        self._account_config = {
            "username": config.get("username") or config.get("X_USERNAME"),
            "password": config.get("password") or config.get("X_PASSWORD"),
            "email": config.get("email") or config.get("X_EMAIL"),
            "email_password": config.get("email_password") or config.get("X_EMAIL_PASSWORD"),
            "cookies": config.get("cookies") or config.get("X_COOKIES"),
        }

    def _get_client(self):
        if self._client is None:
            # 检查是否有账号配置
            if not any(self._account_config.values()):
                raise ValueError(
                    "X 数据源需要账号配置。请在配置中提供:\n"
                    "  - cookies: Twitter cookies 字符串，或\n"
                    "  - username + password: Twitter 用户名和密码"
                )
            self._client = XClient(account_config=self._account_config)
        return self._client

    def _tweet_to_item(self, tweet: Tweet, author: User | None = None) -> ContentItem:
        """将 Tweet 转换为 ContentItem"""
        return ContentItem(
            id=tweet.id,
            content=tweet.text,
            author_id=tweet.author_id,
            author_name=tweet.author_name,
            author_username=tweet.author_username,
            created_at=tweet.created_at,
            url=f"https://x.com/{tweet.author_username}/status/{tweet.id}",
            likes=tweet.like_count,
            replies=tweet.reply_count,
            retweets=tweet.retweet_count,
            quotes=tweet.quote_count,
        )

    def fetch_by_users(self, usernames: list[str], **kwargs) -> Iterator[ContentItem]:
        """获取指定用户的推文"""
        client = self._get_client()
        max_results = kwargs.get("max_results", 10)
        start_time = kwargs.get("start_time")
        end_time = kwargs.get("end_time")

        for username in usernames:
            username = username.lstrip("@")
            user = client.get_user_by_username_sync(username)
            if not user:
                print(f"Warning: Could not find user @{username}")
                continue

            tweets = client.get_user_tweets_sync(
                user_id=user.id,
                max_results=max_results,
                start_time=start_time,
                end_time=end_time
            )

            for tweet in tweets:
                yield self._tweet_to_item(tweet, author=user)

    def fetch_by_followings(self, user_id: str, **kwargs) -> Iterator[ContentItem]:
        """获取关注列表的推文"""
        client = self._get_client()
        max_following = kwargs.get("max_following", 50)
        tweets_per_user = kwargs.get("tweets_per_user", 10)
        start_time = kwargs.get("start_time")
        end_time = kwargs.get("end_time")

        following = client.get_user_following_sync(user_id, max_results=max_following)

        for user in following:
            tweets = client.get_user_tweets_sync(
                user_id=user.id,
                max_results=tweets_per_user,
                start_time=start_time,
                end_time=end_time
            )
            for tweet in tweets:
                yield self._tweet_to_item(tweet, author=user)

    def get_user_id(self, username: str) -> str | None:
        """获取用户 ID"""
        client = self._get_client()
        user = client.get_user_by_username_sync(username.lstrip("@"))
        return user.id if user else None
