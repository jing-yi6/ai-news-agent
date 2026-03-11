"""
翻译器 - 将英文内容翻译为中文
"""
import asyncio
import logging

from providers.base import BaseLLMProvider, Message
from datasources.base import ContentItem

logger = logging.getLogger(__name__)


class Translator:
    """内容翻译器"""

    def __init__(self, provider: BaseLLMProvider | None = None):
        self.provider = provider

    async def translate(self, text: str) -> str | None:
        """将英文翻译为中文"""
        if not self.provider:
            logger.warning("No LLM provider available for translation")
            return None

        messages = [
            Message(role="system", content="你是一个专业的翻译助手。请将以下英文内容翻译成流畅自然的中文，保持原意不变。只输出翻译结果，不要添加解释。"),
            Message(role="user", content=f"翻译以下内容：\n\n{text}")
        ]

        try:
            response = await asyncio.to_thread(
                self.provider.chat_complete,
                messages,
                max_tokens=500,
                temperature=0.3
            )
            return response.content.strip()
        except Exception as e:
            logger.warning(f"Translation failed: {e}")
            return None

    async def translate_items(
        self,
        items: list[ContentItem],
        translate_sources: set[str] | None = None
    ) -> dict[str, str]:
        """翻译多个内容项（根据来源决定是否翻译）

        Args:
            items: 内容项列表
            translate_sources: 需要翻译的数据源集合，如 {"x", "twitter"}
        """
        translations = {}
        if not self.provider:
            return translations

        # 筛选需要翻译的条目
        items_to_translate = [
            item for item in items
            if item.source in translate_sources
        ]

        if not items_to_translate:
            logger.info("没有需要翻译的内容")
            return translations

        logger.info(f"需要翻译: {len(items_to_translate)}/{len(items)} 条")

        # 限制并发数
        semaphore = asyncio.Semaphore(5)

        async def translate_with_limit(item: ContentItem) -> tuple[str, str | None]:
            async with semaphore:
                translated = await self.translate(item.content)
                return item.id, translated

        # 并行翻译（只翻译筛选后的）
        tasks = [translate_with_limit(item) for item in items_to_translate]
        results = await asyncio.gather(*tasks)

        for item_id, translated in results:
            if translated:
                translations[item_id] = translated

        logger.info(f"Translated {len(translations)}/{len(items)} items")
        return translations
