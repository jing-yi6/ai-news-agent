"""
AI 相关内容过滤
"""
import re
from typing import List, Dict, Any, Optional
from datetime import datetime


class TweetFilter:
    """推文过滤器"""
    
    # AI 相关关键词
    AI_KEYWORDS = [
        # 模型/技术
        "AI", "artificial intelligence",
        "LLM", "large language model",
        "GPT", "GPT-4", "GPT-5", "GPT-3",
        "Claude", "Gemini", "Llama", "Mistral",
        "transformer", "neural network", "deep learning",
        "machine learning", "ML",
        "generative AI", "GenAI",
        "multimodal", "diffusion",
        "RAG", "fine-tuning", "pre-training",
        "AGI", "artificial general intelligence",
        
        # 公司/产品
        "OpenAI", "Anthropic", "DeepMind", "Google AI", "Meta AI",
        "Hugging Face", "Stability AI", "Midjourney",
        "ChatGPT", "Copilot", "Bard",
        
        # 研究/学术
        "paper", "research", "benchmark",
        "arXiv", "NeurIPS", "ICML", "ICLR", "CVPR",
        "training", "inference", "token",
        "parameter", "billion parameters",
        
        # 应用
        "chatbot", "assistant",
        "code generation", "text generation",
        "image generation", "video generation",
        "AI agent", "autonomous agent",
    ]
    
    # 排除的关键词 (减少误报)
    EXCLUDE_KEYWORDS = [
        "crypto", "bitcoin", "blockchain", "NFT",
        "giveaway", "airdrop", "free",
        "follow me", "follow back",
    ]
    
    def __init__(self, 
                 min_engagement: int = 0,
                 require_ai_keywords: bool = True,
                 exclude_promotional: bool = True):
        """
        初始化过滤器
        
        Args:
            min_engagement: 最小互动数 (点赞 + 转发)
            require_ai_keywords: 是否要求包含 AI 关键词
            exclude_promotional: 是否排除推广内容
        """
        self.min_engagement = min_engagement
        self.require_ai_keywords = require_ai_keywords
        self.exclude_promotional = exclude_promotional
        
        # 编译正则表达式
        self.ai_pattern = re.compile(
            r'\b(' + '|'.join(re.escape(kw) for kw in self.AI_KEYWORDS) + r')\b',
            re.IGNORECASE
        )
        self.exclude_pattern = re.compile(
            r'\b(' + '|'.join(re.escape(kw) for kw in self.EXCLUDE_KEYWORDS) + r')\b',
            re.IGNORECASE
        )
    
    def calculate_engagement(self, tweet: Dict[str, Any]) -> int:
        """
        计算推文互动数
        
        Args:
            tweet: 推文数据
            
        Returns:
            互动总数
        """
        metrics = tweet.get("public_metrics", {})
        likes = metrics.get("like_count", 0)
        retweets = metrics.get("retweet_count", 0)
        replies = metrics.get("reply_count", 0)
        quotes = metrics.get("quote_count", 0)
        
        return likes + retweets + replies + quotes
    
    def contains_ai_keywords(self, text: str) -> bool:
        """
        检查文本是否包含 AI 相关关键词
        
        Args:
            text: 推文文本
            
        Returns:
            是否包含 AI 关键词
        """
        return bool(self.ai_pattern.search(text))
    
    def is_promotional(self, text: str) -> bool:
        """
        检查是否为推广内容
        
        Args:
            text: 推文文本
            
        Returns:
            是否为推广内容
        """
        return bool(self.exclude_pattern.search(text))
    
    def filter_tweet(self, tweet: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        过滤单条推文
        
        Args:
            tweet: 推文数据
            
        Returns:
            如果通过过滤返回推文，否则返回 None
        """
        text = tweet.get("text", "")
        
        # 检查互动数
        engagement = self.calculate_engagement(tweet)
        if engagement < self.min_engagement:
            return None
        
        # 检查 AI 关键词
        if self.require_ai_keywords and not self.contains_ai_keywords(text):
            return None
        
        # 检查推广内容
        if self.exclude_promotional and self.is_promotional(text):
            return None
        
        # 添加过滤信息
        tweet["_engagement_score"] = engagement
        tweet["_ai_relevant"] = self.contains_ai_keywords(text)
        
        return tweet
    
    def filter_tweets(self, tweets: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        过滤推文列表
        
        Args:
            tweets: 推文列表
            
        Returns:
            过滤后的推文列表
        """
        filtered = []
        
        for tweet in tweets:
            result = self.filter_tweet(tweet)
            if result:
                filtered.append(result)
        
        # 按互动数排序
        filtered.sort(key=lambda x: x.get("_engagement_score", 0), reverse=True)
        
        return filtered
    
    def filter_all_tweets(
        self, 
        all_tweets: Dict[str, List[Dict[str, Any]]]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        过滤所有用户的推文
        
        Args:
            all_tweets: {username: [tweets]} 格式的字典
            
        Returns:
            过滤后的字典
        """
        filtered = {}
        
        for username, tweets in all_tweets.items():
            filtered_tweets = self.filter_tweets(tweets)
            if filtered_tweets:
                filtered[username] = filtered_tweets
        
        return filtered
    
    def categorize_tweet(self, tweet: Dict[str, Any]) -> str:
        """
        对推文进行分类
        
        Args:
            tweet: 推文数据
            
        Returns:
            分类标签
        """
        text = tweet.get("text", "").lower()
        
        # 模型发布
        if any(kw in text for kw in ["announcing", "introducing", "release", "launch", "new model"]):
            return "模型发布"
        
        # 研究进展
        if any(kw in text for kw in ["paper", "research", "arxiv", "study", "benchmark", "sota"]):
            return "研究进展"
        
        # 产品更新
        if any(kw in text for kw in ["update", "feature", "new in", "now available", "beta"]):
            return "产品更新"
        
        # 教程/资源
        if any(kw in text for kw in ["tutorial", "guide", "how to", "learn", "course", "documentation"]):
            return "教程资源"
        
        # 行业动态
        if any(kw in text for kw in ["funding", "investment", "acquisition", "partnership", "hiring"]):
            return "行业动态"
        
        # 默认分类
        return "其他资讯"
    
    def categorize_tweets(
        self, 
        tweets: List[Dict[str, Any]]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        对推文列表进行分类
        
        Args:
            tweets: 推文列表
            
        Returns:
            {分类: [tweets]} 格式的字典
        """
        categories = {}
        
        for tweet in tweets:
            category = self.categorize_tweet(tweet)
            if category not in categories:
                categories[category] = []
            categories[category].append(tweet)
        
        return categories
