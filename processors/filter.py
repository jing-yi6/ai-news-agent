"""
内容过滤器
"""
import re
from typing import Iterator, TYPE_CHECKING

from datasources.base import ContentItem

if TYPE_CHECKING:
    from providers.base import BaseLLMProvider


# 分类提示词模板
CATEGORIZE_PROMPT = """你是一个专业的AI资讯分类助手。请将以下内容分类到以下类别之一：

类别选项：
- 模型发布：新模型发布、模型版本更新、新功能上线
- 研究进展：论文发表、技术突破、 benchmark 结果、学术研究
- 产品更新：产品功能更新、UI改进、新特性上线、Beta版本
- 教程资源：教程、指南、学习资源、文档、代码示例、最佳实践
- 行业动态：融资、投资、收购、合作、招聘、公司动态
- 其他资讯：不属于以上类别的AI相关内容

请只输出类别名称，不要输出其他内容。

内容：
{text}

类别："""


class ContentFilter:
    """内容过滤器"""

    # AI 相关关键词
    AI_KEYWORDS = [
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
        "OpenAI", "Anthropic", "DeepMind", "Google AI", "Meta AI",
        "Hugging Face", "Stability AI", "Midjourney",
        "ChatGPT", "Copilot", "Bard",
        "paper", "research", "benchmark",
        "arXiv", "NeurIPS", "ICML", "ICLR", "CVPR",
        "training", "inference", "token",
        "parameter", "billion parameters",
        "chatbot", "assistant",
        "code generation", "text generation",
        "image generation", "video generation",
        "AI agent", "autonomous agent",
    ]

    # 排除的关键词
    EXCLUDE_KEYWORDS = [
        "crypto", "bitcoin", "blockchain", "NFT",
        "giveaway", "airdrop", "free",
        "follow me", "follow back",
    ]

    def __init__(
        self,
        min_engagement: int = 0,
        require_ai_keywords: bool = True,
        exclude_promotional: bool = False,
        llm_provider: "BaseLLMProvider | None" = None,
        use_llm_categorize: bool = True
    ):
        self.min_engagement = min_engagement
        self.require_ai_keywords = require_ai_keywords
        self.exclude_promotional = exclude_promotional
        self.llm_provider = llm_provider
        self.use_llm_categorize = use_llm_categorize

        # 编译正则表达式
        self.ai_pattern = re.compile(
            r'\b(' + '|'.join(re.escape(kw) for kw in self.AI_KEYWORDS) + r')\b',
            re.IGNORECASE
        )
        self.exclude_pattern = re.compile(
            r'\b(' + '|'.join(re.escape(kw) for kw in self.EXCLUDE_KEYWORDS) + r')\b',
            re.IGNORECASE
        )

    def filter_items(self, items: Iterator[ContentItem]) -> list[ContentItem]:
        """过滤内容"""
        filtered = []

        for item in items:
            # 检查互动数
            if item.engagement_score < self.min_engagement:
                continue

            # 检查 AI 关键词
            if self.require_ai_keywords and not self.ai_pattern.search(item.content):
                continue

            # 检查推广内容
            if self.exclude_promotional and self.exclude_pattern.search(item.content):
                continue

            filtered.append(item)

        # 按互动数排序
        filtered.sort(key=lambda x: x.engagement_score, reverse=True)
        return filtered

    def _categorize_with_llm(self, item: ContentItem) -> str:
        """使用 LLM 对内容进行智能分类"""
        if not self.llm_provider:
            # 如果没有 LLM provider，回退到关键词分类
            return self._categorize_with_keywords(item)

        try:
            from providers.base import Message

            prompt = CATEGORIZE_PROMPT.format(text=item.content[:500])
            messages = [
                Message(role="system", content="你是一个专业的AI资讯分类助手。"),
                Message(role="user", content=prompt)
            ]

            response = self.llm_provider.chat_complete(messages, temperature=0.1, max_tokens=50)
            category = response.content.strip()

            # 映射到标准类别
            category_map = {
                "模型发布": ["模型发布", "model", "发布", "release", "launch"],
                "研究进展": ["研究进展", "research", "论文", "paper", "study"],
                "产品更新": ["产品更新", "product", "更新", "update", "feature"],
                "教程资源": ["教程资源", "tutorial", "教程", "guide", "学习"],
                "行业动态": ["行业动态", "industry", "融资", "funding", "收购"],
                "其他资讯": ["其他资讯", "其他", "other"],
            }

            # 找到匹配的类别
            for standard, keywords in category_map.items():
                if any(kw in category for kw in keywords):
                    return standard

            # 如果没有匹配，返回原文
            return category

        except Exception as e:
            print(f"LLM 分类失败: {e}, 使用关键词分类")
            return self._categorize_with_keywords(item)

    def _categorize_with_keywords(self, item: ContentItem) -> str:
        """使用关键词匹配进行分类（作为 fallback）"""
        text = item.content.lower()

        if any(kw in text for kw in ["announcing", "introducing", "release", "launch", "new model"]):
            return "模型发布"

        if any(kw in text for kw in ["paper", "research", "arxiv", "study", "benchmark", "sota"]):
            return "研究进展"

        if any(kw in text for kw in ["update", "feature", "new in", "now available", "beta"]):
            return "产品更新"

        if any(kw in text for kw in ["tutorial", "guide", "how to", "learn", "course", "documentation"]):
            return "教程资源"

        if any(kw in text for kw in ["funding", "investment", "acquisition", "partnership", "hiring"]):
            return "行业动态"

        return "其他资讯"

    def categorize(self, item: ContentItem) -> str:
        """分类单条内容"""
        if self.use_llm_categorize and self.llm_provider:
            return self._categorize_with_llm(item)
        return self._categorize_with_keywords(item)

    def categorize_items(self, items: list[ContentItem]) -> dict[str, list[ContentItem]]:
        """分类内容列表"""
        categories: dict[str, list[ContentItem]] = {}

        for item in items:
            category = self.categorize(item)
            categories.setdefault(category, []).append(item)

        return categories