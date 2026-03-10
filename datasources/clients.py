"""
API 客户端统一模块

所有数据源的 API 客户端集中在此处，便于管理和扩展。
添加新数据源时，在此文件中添加对应的客户端类。
"""
import asyncio
from dataclasses import dataclass
from datetime import datetime
from typing import List, Dict, Optional, Any


@dataclass
class Tweet:
    """推文数据结构"""
    id: str
    text: str
    created_at: datetime
    author_id: str
    author_username: str
    author_name: str
    like_count: int = 0
    reply_count: int = 0
    retweet_count: int = 0
    quote_count: int = 0


@dataclass
class User:
    """用户数据结构"""
    id: str
    username: str
    name: str
    description: str = ""
    followers_count: int = 0
    following_count: int = 0


class XClient:
    """X (Twitter) 客户端 - 使用 twscrape 库"""

    def __init__(self, account_config: Optional[Dict] = None, rate_limit: float = 1.0):
        """
        初始化 X 客户端

        Args:
            account_config: 账号配置
            rate_limit: 请求间隔（秒），默认 1 秒一次
        """
        self.account_config = account_config or {}
        self._api = None
        self._initialized = False
        self._rate_limit = rate_limit

    async def _init_api(self):
        """初始化 twscrape API"""
        if self._initialized:
            return

        try:
            from twscrape import API
        except ImportError:
            raise ImportError(
                "twscrape is required. Install it with: pip install twscrape"
            )

        # 初始化 API，设置速率限制（每秒 1 次请求）
        self._api = API(rate_limit=self._rate_limit)

        # 如果有账号配置，添加账号
        if self.account_config:
            username = self.account_config.get("username")
            password = self.account_config.get("password")
            email = self.account_config.get("email")
            email_password = self.account_config.get("email_password")
            cookies = self.account_config.get("cookies")

            if cookies:
                # 使用 cookies 登录
                await self._api.add_cookies(username, cookies)
            elif username and password:
                # 使用用户名密码登录
                await self._api.add_account(username, password, email or "", email_password or "")
                # 尝试登录获取 cookies
                await self._api.login(username)
            else:
                raise ValueError(
                    "Must provide either 'cookies' or 'username' and 'password' in account_config"
                )

        self._initialized = True

    def _to_user(self, user_data) -> Optional[User]:
        """将 twscrape User 对象转换为 User"""
        if not user_data:
            return None
        return User(
            id=str(user_data.id),
            username=user_data.username,
            name=user_data.display_name or user_data.username,
            description=getattr(user_data, 'description', ''),
            followers_count=getattr(user_data, 'followers_count', 0),
            following_count=getattr(user_data, 'following_count', 0),
        )

    def _to_tweet(self, tweet_data, author: Optional[User] = None) -> Optional[Tweet]:
        """将 twscrape Tweet 对象转换为 Tweet"""
        if not tweet_data:
            return None

        # 处理日期
        created_at = getattr(tweet_data, 'created_at', None)
        if isinstance(created_at, str):
            try:
                created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            except (ValueError, TypeError):
                created_at = datetime.now()
        elif not isinstance(created_at, datetime):
            created_at = datetime.now()

        # 获取作者信息
        if author:
            author_id = author.id
            author_username = author.username
            author_name = author.name
        else:
            author_id = str(getattr(tweet_data, 'user_id', ''))
            author_username = getattr(tweet_data, 'username', '')
            author_name = getattr(tweet_data, 'display_name', author_username)

        # 获取互动数据
        views = getattr(tweet_data, 'views', 0) or 0
        likes = getattr(tweet_data, 'likes', 0) or 0
        replies = getattr(tweet_data, 'replies', 0) or 0
        retweets = getattr(tweet_data, 'retweets', 0) or 0
        quotes = getattr(tweet_data, 'quotes', 0) or 0

        return Tweet(
            id=str(tweet_data.id),
            text=tweet_data.raw_text or tweet_data.text or '',
            created_at=created_at,
            author_id=author_id,
            author_username=author_username,
            author_name=author_name,
            like_count=likes,
            reply_count=replies,
            retweet_count=retweets,
            quote_count=quotes,
        )

    async def get_user_by_username(self, username: str) -> Optional[User]:
        """
        通过用户名获取用户信息

        Args:
            username: X 用户名 (不含 @)

        Returns:
            用户信息
        """
        await self._init_api()
        try:
            user_data = await self._api.user_by_login(username.lstrip("@"))
            return self._to_user(user_data)
        except Exception as e:
            print(f"Error getting user {username}: {e}")
            return None

    async def get_user_by_id(self, user_id: str) -> Optional[User]:
        """
        通过 ID 获取用户信息

        Args:
            user_id: 用户 ID

        Returns:
            用户信息
        """
        await self._init_api()
        try:
            user_data = await self._api.user_by_id(int(user_id))
            return self._to_user(user_data)
        except Exception as e:
            print(f"Error getting user {user_id}: {e}")
            return None

    async def get_user_tweets(
        self,
        user_id: str,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        max_results: int = 100,
        exclude_replies: bool = True,
        exclude_retweets: bool = False
    ) -> List[Tweet]:
        """
        获取用户推文

        Args:
            user_id: 用户 ID
            start_time: ISO 8601 格式开始时间 (如: 2024-01-01T00:00:00Z)
            end_time: ISO 8601 格式结束时间
            max_results: 最大返回数量
            exclude_replies: 是否排除回复
            exclude_retweets: 是否排除转发

        Returns:
            推文列表
        """
        await self._init_api()

        tweets = []
        try:
            # 获取用户推文
            async for tweet_data in self._api.user_tweets(int(user_id), limit=max_results):
                # 过滤回复
                if exclude_replies and getattr(tweet_data, 'is_reply', False):
                    continue

                # 过滤转发
                if exclude_retweets and getattr(tweet_data, 'is_retweet', False):
                    continue

                # 时间过滤
                if start_time or end_time:
                    created_at = getattr(tweet_data, 'created_at', None)
                    if created_at:
                        if isinstance(created_at, str):
                            try:
                                created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                            except (ValueError, TypeError):
                                continue

                        if start_time:
                            try:
                                start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                                if created_at < start_dt:
                                    continue
                            except (ValueError, TypeError):
                                pass

                        if end_time:
                            try:
                                end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
                                if created_at > end_dt:
                                    continue
                            except (ValueError, TypeError):
                                pass

                tweet = self._to_tweet(tweet_data)
                if tweet:
                    tweets.append(tweet)

                if len(tweets) >= max_results:
                    break

        except Exception as e:
            print(f"Error getting tweets for user {user_id}: {e}")

        return tweets[:max_results]

    async def get_user_following(self, user_id: str, max_results: int = 100) -> List[User]:
        """
        获取用户关注列表

        Args:
            user_id: 用户 ID
            max_results: 最大返回数量

        Returns:
            关注的用户列表
        """
        await self._init_api()

        following = []
        try:
            async for user_data in self._api.following(int(user_id), limit=max_results):
                user = self._to_user(user_data)
                if user:
                    following.append(user)

                if len(following) >= max_results:
                    break

        except Exception as e:
            print(f"Error getting following for user {user_id}: {e}")

        return following[:max_results]


# =============================================================================
# 添加新数据源的客户端时，在此处添加新的类
# =============================================================================
#
# class GitHubClient:
#     """GitHub API 客户端"""
#     BASE_URL = "https://api.github.com"
#
#     def __init__(self, token: Optional[str] = None):
#         self.token = token or os.getenv("GITHUB_TOKEN")
#         self.headers = {
#             "Authorization": f"Bearer {self.token}",
#             "Accept": "application/vnd.github.v3+json"
#         }
#
# class RedditClient:
#     """Reddit API 客户端"""
#     pass
#
# class HNClient:
#     """Hacker News API 客户端"""
#     pass
