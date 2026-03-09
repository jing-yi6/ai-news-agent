"""
推文获取逻辑
"""
import os
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional, Any
from .x_client import XClient


class TweetFetcher:
    """推文获取器"""
    
    def __init__(self, client: Optional[XClient] = None):
        """
        初始化推文获取器
        
        Args:
            client: XClient 实例，如果不提供则创建新实例
        """
        self.client = client or XClient()
    
    def get_time_window(self, days_back: int = 1) -> tuple:
        """
        获取时间窗口

        Args:
            days_back: 回退天数，默认为1（前一天）

        Returns:
            (start_time, end_time) ISO 8601 格式元组
        """
        now = datetime.now(timezone.utc)

        # 前一天 00:00
        start = now - timedelta(days=days_back)
        start = start.replace(hour=0, minute=0, second=0, microsecond=0)

        # 当天 23:59
        end = now.replace(hour=23, minute=59, second=59, microsecond=0)

        # 转换为 ISO 8601 格式 (UTC)
        start_time = start.strftime("%Y-%m-%dT%H:%M:%SZ")
        end_time = end.strftime("%Y-%m-%dT%H:%M:%SZ")

        return start_time, end_time
    
    def fetch_following_tweets(
        self, 
        user_id: str, 
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        max_following: int = 50,
        tweets_per_user: int = 10,
        exclude_replies: bool = True
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        获取关注列表中用户的推文
        
        Args:
            user_id: 用户 ID
            start_time: 开始时间 (ISO 8601)
            end_time: 结束时间 (ISO 8601)
            max_following: 最多获取多少个关注用户
            tweets_per_user: 每个用户获取多少条推文
            exclude_replies: 是否排除回复
            
        Returns:
            {username: [tweets]} 格式的字典
        """
        # 默认使用前一天到当天的时间窗口
        if start_time is None or end_time is None:
            start_time, end_time = self.get_time_window()
        
        print(f"Fetching tweets from {start_time} to {end_time}")
        
        # 获取关注列表
        print(f"Fetching following list for user {user_id}...")
        following = self.client.get_user_following(user_id, max_results=max_following)
        print(f"Found {len(following)} following users")
        
        all_tweets = {}
        
        for user in following:
            user_id = user.get("id")
            username = user.get("username", "unknown")
            name = user.get("name", username)
            
            print(f"Fetching tweets from @{username} ({name})...")
            
            try:
                tweets = self.client.get_user_tweets(
                    user_id=user_id,
                    start_time=start_time,
                    end_time=end_time,
                    max_results=tweets_per_user,
                    exclude_replies=exclude_replies,
                    exclude_retweets=False
                )
                
                if tweets:
                    # 添加用户信息到每条推文
                    for tweet in tweets:
                        tweet["author_username"] = username
                        tweet["author_name"] = name
                    
                    all_tweets[username] = tweets
                    print(f"  -> Got {len(tweets)} tweets")
                else:
                    print(f"  -> No tweets in time window")
                    
            except Exception as e:
                print(f"  -> Error: {e}")
                continue
        
        return all_tweets
    
    def fetch_specific_users_tweets(
        self,
        usernames: List[str],
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        tweets_per_user: int = 10
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        获取指定用户的推文
        
        Args:
            usernames: X 用户名列表 (不含 @)
            start_time: 开始时间
            end_time: 结束时间
            tweets_per_user: 每个用户获取多少条推文
            
        Returns:
            {username: [tweets]} 格式的字典
        """
        if start_time is None or end_time is None:
            start_time, end_time = self.get_time_window()
        
        all_tweets = {}
        
        for username in usernames:
            username = username.lstrip("@")  # 移除 @ 符号
            print(f"Fetching tweets from @{username}...")
            
            try:
                # 获取用户 ID
                user = self.client.get_user_by_username(username)
                if not user:
                    print(f"  -> User @{username} not found")
                    continue
                
                user_id = user.get("id")
                name = user.get("name", username)
                
                tweets = self.client.get_user_tweets(
                    user_id=user_id,
                    start_time=start_time,
                    end_time=end_time,
                    max_results=tweets_per_user,
                    exclude_replies=True
                )
                
                if tweets:
                    for tweet in tweets:
                        tweet["author_username"] = username
                        tweet["author_name"] = name
                    
                    all_tweets[username] = tweets
                    print(f"  -> Got {len(tweets)} tweets")
                else:
                    print(f"  -> No tweets in time window")
                    
            except Exception as e:
                print(f"  -> Error: {e}")
                continue
        
        return all_tweets
