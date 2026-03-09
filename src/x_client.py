"""
X (Twitter) API v2 客户端封装
"""
import os
import time
from typing import List, Dict, Optional, Any
import requests

# 尝试加载 .env 文件（如果 python-dotenv 可用）
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


class XClient:
    """X API v2 客户端"""
    
    BASE_URL = "https://api.twitter.com/2"
    
    def __init__(self, bearer_token: Optional[str] = None):
        """
        初始化 X API 客户端
        
        Args:
            bearer_token: X API Bearer Token，如果不提供则从环境变量读取
        """
        self.bearer_token = bearer_token or os.getenv("X_BEARER_TOKEN")
        if not self.bearer_token:
            raise ValueError("X_BEARER_TOKEN is required. Set it in .env file or pass to constructor.")
        
        self.headers = {
            "Authorization": f"Bearer {self.bearer_token}",
            "Content-Type": "application/json"
        }
        self.rate_limit_remaining = None
        self.rate_limit_reset = None
    
    def _make_request(self, endpoint: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """
        发送 API 请求
        
        Args:
            endpoint: API 端点路径
            params: 查询参数
            
        Returns:
            API 响应数据
        """
        url = f"{self.BASE_URL}{endpoint}"
        
        # 检查速率限制
        if self.rate_limit_remaining is not None and self.rate_limit_remaining <= 1:
            if self.rate_limit_reset:
                wait_time = max(0, self.rate_limit_reset - int(time.time()) + 1)
                if wait_time > 0:
                    print(f"Rate limit reached. Waiting {wait_time} seconds...")
                    time.sleep(wait_time)
        
        response = requests.get(url, headers=self.headers, params=params)
        
        # 更新速率限制信息
        self.rate_limit_remaining = int(response.headers.get("x-rate-limit-remaining", 0))
        self.rate_limit_reset = int(response.headers.get("x-rate-limit-reset", 0))
        
        if response.status_code == 429:
            # 速率限制，等待后重试
            reset_time = int(response.headers.get("x-rate-limit-reset", int(time.time()) + 60))
            wait_time = max(0, reset_time - int(time.time()) + 1)
            print(f"Rate limited. Waiting {wait_time} seconds...")
            time.sleep(wait_time)
            return self._make_request(endpoint, params)
        
        response.raise_for_status()
        return response.json()
    
    def get_user_following(self, user_id: str, max_results: int = 100) -> List[Dict[str, Any]]:
        """
        获取用户关注列表
        
        Args:
            user_id: 用户 ID
            max_results: 最大返回数量
            
        Returns:
            关注的用户列表
        """
        endpoint = f"/users/{user_id}/following"
        params = {
            "max_results": min(max_results, 1000),  # API 限制
            "user.fields": "id,username,name,description,public_metrics"
        }
        
        following = []
        next_token = None
        
        while len(following) < max_results:
            if next_token:
                params["pagination_token"] = next_token
            
            data = self._make_request(endpoint, params)
            
            if "data" in data:
                following.extend(data["data"])
            
            # 检查是否有更多页面
            if "meta" in data and "next_token" in data["meta"]:
                next_token = data["meta"]["next_token"]
            else:
                break
            
            # 达到数量限制
            if len(following) >= max_results:
                break
        
        return following[:max_results]
    
    def get_user_tweets(
        self, 
        user_id: str, 
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        max_results: int = 100,
        exclude_replies: bool = True,
        exclude_retweets: bool = False
    ) -> List[Dict[str, Any]]:
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
        endpoint = f"/users/{user_id}/tweets"
        params = {
            "max_results": min(max_results, 100),
            "tweet.fields": "id,created_at,text,public_metrics,entities,referenced_tweets",
            "expansions": "author_id",
            "user.fields": "username,name"
        }
        
        # 添加排除选项
        exclude = []
        if exclude_replies:
            exclude.append("replies")
        if exclude_retweets:
            exclude.append("retweets")
        if exclude:
            params["exclude"] = ",".join(exclude)
        
        # 添加时间范围
        if start_time:
            params["start_time"] = start_time
        if end_time:
            params["end_time"] = end_time
        
        tweets = []
        next_token = None
        
        while len(tweets) < max_results:
            if next_token:
                params["pagination_token"] = next_token
            
            data = self._make_request(endpoint, params)
            
            if "data" in data:
                tweets.extend(data["data"])
            
            # 检查是否有更多页面
            if "meta" in data and "next_token" in data["meta"]:
                next_token = data["meta"]["next_token"]
            else:
                break
            
            if len(tweets) >= max_results:
                break
        
        return tweets[:max_results]
    
    def get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        """
        通过用户名获取用户信息
        
        Args:
            username: X 用户名 (不含 @)
            
        Returns:
            用户信息
        """
        endpoint = f"/users/by/username/{username}"
        params = {
            "user.fields": "id,username,name,description,public_metrics"
        }
        
        data = self._make_request(endpoint, params)
        return data.get("data")
    
    def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        通过 ID 获取用户信息
        
        Args:
            user_id: 用户 ID
            
        Returns:
            用户信息
        """
        endpoint = f"/users/{user_id}"
        params = {
            "user.fields": "id,username,name,description,public_metrics"
        }
        
        data = self._make_request(endpoint, params)
        return data.get("data")
