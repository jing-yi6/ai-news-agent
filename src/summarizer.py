"""
摘要生成器
支持简单的本地摘要和可选的 LLM 增强摘要
"""
import os
import re
from typing import List, Dict, Any, Optional
from datetime import datetime


class TweetSummarizer:
    """推文摘要生成器"""
    
    def __init__(self, use_llm: bool = False):
        """
        初始化摘要生成器
        
        Args:
            use_llm: 是否使用 LLM 生成摘要
        """
        self.use_llm = use_llm
        
        if use_llm:
            self._init_llm()
    
    def _init_llm(self):
        """初始化 LLM 客户端"""
        # 检查是否有自定义 OpenAI 兼容端点
        openai_compatible_key = os.getenv("OPENAI_COMPATIBLE_API_KEY")
        openai_compatible_base = os.getenv("OPENAI_COMPATIBLE_BASE_URL")

        if openai_compatible_key and openai_compatible_base:
            try:
                import openai
                self.openai_client = openai.OpenAI(
                    api_key=openai_compatible_key,
                    base_url=openai_compatible_base
                )
                self.llm_provider = "openai_compatible"
                self.openai_model = os.getenv("OPENAI_COMPATIBLE_MODEL", "gpt-3.5-turbo")
                print(f"Using OpenAI compatible API: {openai_compatible_base}")
                return
            except ImportError:
                pass

        # 尝试初始化标准 OpenAI
        openai_key = os.getenv("OPENAI_API_KEY")
        openai_base = os.getenv("OPENAI_BASE_URL")  # 可选的自定义端点
        if openai_key:
            try:
                import openai
                client_kwargs = {"api_key": openai_key}
                if openai_base:
                    client_kwargs["base_url"] = openai_base
                self.openai_client = openai.OpenAI(**client_kwargs)
                self.llm_provider = "openai"
                self.openai_model = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
                return
            except ImportError:
                pass

        # 尝试初始化 Anthropic
        anthropic_key = os.getenv("ANTHROPIC_API_KEY")
        if anthropic_key:
            try:
                import anthropic
                self.anthropic_client = anthropic.Anthropic(api_key=anthropic_key)
                self.llm_provider = "anthropic"
                return
            except ImportError:
                pass

        # 没有可用的 LLM
        self.use_llm = False
        print("Warning: LLM not available. Using simple summarization.")
    
    def generate_summary(self, text: str, max_length: int = 100) -> str:
        """
        生成单条推文的摘要
        
        Args:
            text: 推文文本
            max_length: 最大长度
            
        Returns:
            摘要文本
        """
        if self.use_llm:
            return self._llm_summarize(text, max_length)
        else:
            return self._simple_summarize(text, max_length)
    
    def _simple_summarize(self, text: str, max_length: int = 100) -> str:
        """
        简单摘要：提取关键句子或截断
        
        Args:
            text: 推文文本
            max_length: 最大长度
            
        Returns:
            摘要文本
        """
        # 清理文本
        text = self._clean_text(text)
        
        # 如果文本较短，直接返回
        if len(text) <= max_length:
            return text
        
        # 尝试按句子分割
        sentences = re.split(r'[.!?。！？]\s+', text)
        
        summary = ""
        for sentence in sentences:
            if len(summary) + len(sentence) + 1 <= max_length:
                summary += sentence + ". "
            else:
                break
        
        # 如果第一句就太长，直接截断
        if not summary:
            summary = text[:max_length-3] + "..."
        
        return summary.strip()
    
    def _llm_summarize(self, text: str, max_length: int = 100) -> str:
        """
        使用 LLM 生成摘要
        
        Args:
            text: 推文文本
            max_length: 最大长度
            
        Returns:
            摘要文本
        """
        prompt = f"""请将以下 AI 相关推文总结为一句话（不超过 {max_length} 字符）：

推文内容：
{text}

摘要："""
        
        try:
            if self.llm_provider in ("openai", "openai_compatible"):
                response = self.openai_client.chat.completions.create(
                    model=getattr(self, "openai_model", "gpt-3.5-turbo"),
                    messages=[
                        {"role": "system", "content": "你是一个专业的 AI 资讯摘要助手。"},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=100,
                    temperature=0.3
                )
                return response.choices[0].message.content.strip()

            elif self.llm_provider == "anthropic":
                response = self.anthropic_client.messages.create(
                    model="claude-3-haiku-20240307",
                    max_tokens=100,
                    temperature=0.3,
                    messages=[
                        {"role": "user", "content": prompt}
                    ]
                )
                return response.content[0].text.strip()
        
        except Exception as e:
            print(f"LLM summarization failed: {e}")
            return self._simple_summarize(text, max_length)
        
        return self._simple_summarize(text, max_length)
    
    def _clean_text(self, text: str) -> str:
        """
        清理推文文本
        
        Args:
            text: 原始文本
            
        Returns:
            清理后的文本
        """
        # 移除 URL
        text = re.sub(r'https?://\S+', '', text)
        # 移除多余空格
        text = re.sub(r'\s+', ' ', text)
        # 移除 @用户名
        text = re.sub(r'@\w+', '', text)
        # 移除 # 标签符号但保留文字
        text = re.sub(r'#(\w+)', r'\1', text)
        
        return text.strip()
    
    def extract_key_points(self, tweets: List[Dict[str, Any]], max_points: int = 5) -> List[str]:
        """
        从多条推文中提取关键要点
        
        Args:
            tweets: 推文列表
            max_points: 最大要点数
            
        Returns:
            关键要点列表
        """
        if not tweets:
            return []
        
        # 按互动数排序
        sorted_tweets = sorted(
            tweets,
            key=lambda x: x.get("_engagement_score", 0),
            reverse=True
        )
        
        key_points = []
        for tweet in sorted_tweets[:max_points]:
            text = tweet.get("text", "")
            summary = self.generate_summary(text, max_length=80)
            if summary:
                key_points.append(summary)
        
        return key_points
    
    def generate_daily_summary(
        self, 
        categorized_tweets: Dict[str, List[Dict[str, Any]]]
    ) -> Dict[str, Any]:
        """
        生成每日摘要
        
        Args:
            categorized_tweets: 分类后的推文
            
        Returns:
            摘要数据
        """
        summary = {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "total_categories": len(categorized_tweets),
            "total_tweets": sum(len(tweets) for tweets in categorized_tweets.values()),
            "categories": {}
        }
        
        for category, tweets in categorized_tweets.items():
            key_points = self.extract_key_points(tweets, max_points=3)
            summary["categories"][category] = {
                "count": len(tweets),
                "key_points": key_points,
                "top_tweets": tweets[:3]  # 保留前3条推文详情
            }
        
        return summary
