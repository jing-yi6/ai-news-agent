"""
API 客户端统一模块

所有数据源的 API 客户端集中在此处，便于管理和扩展。
添加新数据源时，在此文件中添加对应的客户端类。
"""
import asyncio
import json
import logging
import re
from dataclasses import dataclass
from datetime import datetime
from typing import List, Dict, Optional, Any

logger = logging.getLogger(__name__)

def _patched_get_scripts_list(text: str):
    """修复 Twitter 返回的畸形 JSON"""
    scripts = text.split('e=>e+"."+')[1].split('[e]+"a.js"')[0]

    try:
        for k, v in json.loads(scripts).items():
            yield f"https://abs.twimg.com/responsive-web/client-web/{k}.{v}a.js"
    except json.decoder.JSONDecodeError:
        # 修复未加引号的键，如: node_modules_pnpm_ws_8_18_0_node_modules_ws_browser_js
        fixed_scripts = re.sub(
            r'([,\{])(\s*)([\w]+_[\w_]+)(\s*):',
            r'\1\2"\3"\4:',
            scripts
        )
        for k, v in json.loads(fixed_scripts).items():
            yield f"https://abs.twimg.com/responsive-web/client-web/{k}.{v}a.js"

# 应用 patch（在导入 twscrape 之前）
try:
    from twscrape import xclid
    xclid.get_scripts_list = _patched_get_scripts_list
except ImportError:
    pass  # twscrape 未安装时跳过


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
        self._last_request_time: Optional[float] = None
        self._lock = asyncio.Lock()

    async def _rate_limit_wait(self):
        """等待以满足速率限制"""
        async with self._lock:
            if self._last_request_time is not None:
                elapsed = asyncio.get_event_loop().time() - self._last_request_time
                if elapsed < self._rate_limit:
                    await asyncio.sleep(self._rate_limit - elapsed)
            self._last_request_time = asyncio.get_event_loop().time()

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

        # 初始化 API
        self._api = API()

        # 如果有账号配置，添加账号
        if self.account_config:
            username = self.account_config.get("username")
            password = self.account_config.get("password")
            email = self.account_config.get("email")
            email_password = self.account_config.get("email_password")
            cookies = self.account_config.get("cookies")

            if cookies and username:
                # 使用 cookies 登录（需要用户名和 cookies）
                await self._api.pool.add_account(username, "", "", "", cookies=cookies)
            elif username and password:
                # 使用用户名密码登录
                await self._api.pool.add_account(username, password, email or "", email_password or "")
                # 尝试登录获取 cookies
                await self._api.pool.login(username)
            else:
                raise ValueError(
                    "Must provide either 'cookies' with 'username', or 'username' and 'password' in account_config"
                )

        self._initialized = True

    def _to_user(self, user_data) -> Optional[User]:
        """将 twscrape User 对象转换为 User"""
        if not user_data:
            return None
        return User(
            id=str(user_data.id),
            username=user_data.username,
            name=getattr(user_data, 'displayname', user_data.username),
            description=getattr(user_data, 'rawDescription', ''),
            followers_count=getattr(user_data, 'followersCount', 0),
            following_count=getattr(user_data, 'friendsCount', 0),
        )

    def _to_tweet(self, tweet_data, author: Optional[User] = None) -> Optional[Tweet]:
        """将 twscrape Tweet 对象转换为 Tweet"""
        if not tweet_data:
            return None

        # 处理日期 
        created_at = getattr(tweet_data, 'date', None)
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
            author_id = str(getattr(tweet_data.user, 'id', ''))
            author_username = getattr(tweet_data.user, 'username', '')
            author_name = getattr(tweet_data.user, 'displayname', author_username)

        # 获取互动数据 (twscrape 用驼峰命名)
        likes = getattr(tweet_data, 'likeCount', 0) or 0
        replies = getattr(tweet_data, 'replyCount', 0) or 0
        retweets = getattr(tweet_data, 'retweetCount', 0) or 0
        quotes = getattr(tweet_data, 'quoteCount', 0) or 0

        text = getattr(tweet_data, 'rawContent', '') or ''

        return Tweet(
            id=str(tweet_data.id),
            text=text,
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
        await self._rate_limit_wait()
        try:
            user_data = await self._api.user_by_login(username.lstrip("@"))
            return self._to_user(user_data)
        except Exception as e:
            logger.warning(f"Error getting user {username}: {e}")
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
        await self._rate_limit_wait()
        try:
            user_data = await self._api.user_by_id(int(user_id))
            return self._to_user(user_data)
        except Exception as e:
            logger.warning(f"Error getting user {user_id}: {e}")
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
        await self._rate_limit_wait()

        tweets = []
        try:
            # 获取用户推文
            async for tweet_data in self._api.user_tweets(int(user_id), limit=max_results):
                # 过滤回复 (inReplyToTweetId 不为 None 表示是回复)
                if exclude_replies and tweet_data.inReplyToTweetId is not None:
                    continue

                # 过滤转发 (retweetedTweet 不为 None 表示是转发)
                if exclude_retweets and tweet_data.retweetedTweet is not None:
                    continue

                # 时间过滤
                if start_time or end_time:
                    created_at = getattr(tweet_data, 'date', None)  # twscrape 使用 'date' 而不是 'created_at'
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
            logger.error(f"Error getting tweets for user {user_id}: {e}")

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
        await self._rate_limit_wait()

        following = []
        try:
            async for user_data in self._api.following(int(user_id), limit=max_results):
                user = self._to_user(user_data)
                if user:
                    following.append(user)

                if len(following) >= max_results:
                    break

        except Exception as e:
            logger.error(f"Error getting following for user {user_id}: {e}")

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
