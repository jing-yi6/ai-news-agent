"""
摘要生成器
"""
import re

from providers.base import BaseLLMProvider, Message
from datasources.base import ContentItem


class Summarizer:
    """摘要生成器"""

    def __init__(self, provider: BaseLLMProvider | None = None):
        self.provider = provider

    def summarize(self, text: str, max_length: int = 100) -> str:
        """生成摘要"""
        if not self.provider:
            return self._simple_summarize(text, max_length)

        messages = [
            Message(role="system", content="你是一个专业的 AI 资讯摘要助手。"),
            Message(role="user", content=f"请将以下 AI 相关推文总结为一句话（不超过 {max_length} 字符）：\n\n{text}\n\n摘要：")
        ]

        try:
            response = self.provider.chat_complete(messages, max_tokens=100)
            return response.content.strip()
        except Exception as e:
            print(f"LLM summarization failed: {e}")
            return self._simple_summarize(text, max_length)

    def _simple_summarize(self, text: str, max_length: int) -> str:
        """简单摘要"""
        text = self._clean_text(text)

        if len(text) <= max_length:
            return text

        # 按句子分割
        sentences = re.split(r'[.!?。！？]\s+', text)
        summary = ""
        for sentence in sentences:
            if len(summary) + len(sentence) + 1 <= max_length:
                summary += sentence + ". "
            else:
                break

        return summary.strip() or text[:max_length - 3] + "..."

    def _clean_text(self, text: str) -> str:
        """清理文本"""
        text = re.sub(r'https?://\S+', '', text)  # 移除 URL
        text = re.sub(r'\s+', ' ', text)          # 移除多余空格
        text = re.sub(r'@\w+', '', text)          # 移除 @用户名
        text = re.sub(r'#(\w+)', r'\1', text)     # 移除 # 符号
        return text.strip()

    def extract_key_points(self, items: list[ContentItem], max_points: int = 5) -> list[str]:
        """提取关键要点"""
        sorted_items = sorted(items, key=lambda x: x.engagement_score, reverse=True)

        key_points = []
        for item in sorted_items[:max_points]:
            summary = self.summarize(item.content, max_length=80)
            if summary:
                key_points.append(summary)

        return key_points
