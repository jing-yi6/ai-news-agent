"""
内容去重器 - 基于昨天的日报文件中的 URL
"""
import logging
import os
import re
from datetime import datetime, timedelta

from datasources.base import ContentItem

logger = logging.getLogger(__name__)


class Deduplicator:
    """内容去重器 - 基于昨天的日报文件中的 URL"""

    def __init__(self, output_dir: str = "output"):
        self.output_dir = output_dir

    def _get_yesterday_file(self) -> str | None:
        """获取昨天的日报文件路径"""
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        filepath = os.path.join(self.output_dir, f"{yesterday}.md")
        return filepath if os.path.exists(filepath) else None

    def _extract_urls_from_file(self, filepath: str) -> set[str]:
        """从 Markdown 文件中提取所有内容 URL

        匹配格式: [🔗 查看原文](https://x.com/...)
        """
        urls = set()
        # 匹配 markdown 链接中的 URL
        pattern = re.compile(r'\[🔗 查看原文\]\(([^)]+)\)')
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                for line in f:
                    match = pattern.search(line)
                    if match:
                        urls.add(match.group(1))
        except Exception as e:
            logger.warning(f"读取昨天的日报文件失败: {e}")
            return set()
        return urls

    def get_seen_urls(self) -> set[str]:
        """获取昨天已记录的所有内容 URL"""
        yesterday_file = self._get_yesterday_file()
        if not yesterday_file:
            logger.info("未找到昨天的日报，跳过去重")
            return set()
        urls = self._extract_urls_from_file(yesterday_file)
        logger.info(f"从昨天的日报中提取到 {len(urls)} 条 URL")
        return urls

    def filter_new_items(self, items: list[ContentItem]) -> list[ContentItem]:
        """过滤出未在昨天出现过的新内容"""
        seen_urls = self.get_seen_urls()
        if not seen_urls:
            return items

        new_items = []
        duplicate_count = 0

        for item in items:
            if item.url in seen_urls:
                duplicate_count += 1
                logger.debug(f"跳过重复内容: {item.url}")
            else:
                new_items.append(item)

        if duplicate_count > 0:
            logger.info(f"过滤掉 {duplicate_count} 条昨日已抓取的内容")

        return new_items
