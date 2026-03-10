#!/usr/bin/env python3
"""
AI News Agent - 每日 AI 资讯摘要生成器
"""
import argparse
import asyncio
import logging
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from config import AppConfig, setup_logging
from providers import create_llm_provider
from datasources import create_datasource
from processors import ContentFilter, Summarizer, MarkdownFormatter

# 获取 logger
logger = logging.getLogger(__name__)


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description="AI News Agent - 每日 AI 资讯摘要生成器")
    parser.add_argument("--users", nargs="+", help="指定用户名列表（不含 @）")
    parser.add_argument("--user-id", help="指定用户 ID（用于获取关注列表）")
    parser.add_argument("--mock", action="store_true", help="使用模拟数据测试")
    parser.add_argument("--datasource", help="数据源类型 (x, mock)")
    parser.add_argument("--date", help="指定日期 (YYYY-MM-DD)")
    parser.add_argument("--output", default="output", help="输出目录")
    parser.add_argument("--max-following", type=int, default=30, help="最多获取关注用户数")
    parser.add_argument("--tweets-per-user", type=int, default=10, help="每个用户获取推文数")
    parser.add_argument("--min-engagement", type=int, default=0, help="最小互动数过滤")
    parser.add_argument("--use-llm", action="store_true", help="使用 LLM 生成摘要")
    return parser.parse_args()


def get_time_window(days_back: int = 1) -> tuple[str, str]:
    """获取时间窗口"""
    if days_back < 0:
        raise ValueError(f"days_back must be non-negative, got {days_back}")
    if days_back > 365:
        raise ValueError(f"days_back must be <= 365, got {days_back}")

    now = datetime.now(timezone.utc)
    start = (now - timedelta(days=days_back)).replace(hour=0, minute=0, second=0, microsecond=0)
    end = now.replace(hour=23, minute=59, second=59, microsecond=0)
    return start.strftime("%Y-%m-%dT%H:%M:%SZ"), end.strftime("%Y-%m-%dT%H:%M:%SZ")


async def main_async():
    """异步主函数"""
    args = parse_args()

    # 设置日志（只记录 WARNING 及以上，生成带时间戳的日志文件）
    log_dir = os.getenv("LOG_DIR", "logs")
    log_file = setup_logging(log_dir=log_dir)

    logger.info("=" * 60)
    logger.info("🤖 AI News Agent")
    logger.info("=" * 60)

    # 加载配置
    config = AppConfig.load()

    # 确定数据源
    datasource_name = args.datasource or ("mock" if args.mock else config.datasource.name)

    # 创建数据源
    datasource = create_datasource(
        datasource_name,
        config.datasource.config if datasource_name == config.datasource.name else {}
    )
    logger.info(f"📡 数据源: {datasource_name}")

    # 创建 LLM Provider（如果启用）
    provider = None
    if args.use_llm and config.llm:
        try:
            provider = create_llm_provider(
                config.llm.provider,
                config.llm.api_key,
                config.llm.base_url,
                config.llm.model
            )
            logger.info(f"🤖 LLM: {config.llm.provider} ({config.llm.model})")
        except Exception as e:
            logger.warning(f"LLM 初始化失败: {e}")

    # 获取数据
    logger.info("\n🔍 获取内容...")
    start_time, end_time = get_time_window()

    items = []
    if args.users:
        logger.info(f"用户: {', '.join(args.users)}")
        async for item in datasource.fetch_by_users(
            args.users,
            max_results=args.tweets_per_user,
            start_time=start_time,
            end_time=end_time
        ):
            items.append(item)
    else:
        user_id = args.user_id or config.datasource.config.get("user_id")
        if not user_id and datasource_name != "mock":
            logger.error("❌ 错误: 未指定用户列表或用户 ID")
            sys.exit(1)

        logger.info(f"关注列表: {user_id or 'mock'}")
        async for item in datasource.fetch_by_followings(
            user_id or "mock",
            max_following=args.max_following,
            tweets_per_user=args.tweets_per_user,
            start_time=start_time,
            end_time=end_time
        ):
            items.append(item)

    logger.info(f"📊 原始内容: {len(items)}")

    if not items:
        logger.warning("⚠️ 未获取到任何内容")
        return

    # 过滤
    logger.info("🔍 过滤 AI 相关内容...")
    filter_ = ContentFilter(
        min_engagement=args.min_engagement or config.min_engagement,
        require_ai_keywords=config.require_ai_keywords,
        exclude_promotional=config.exclude_promotional,
        llm_provider=provider,
        use_llm_categorize=args.use_llm and provider is not None
    )
    filtered = filter_.filter_items(iter(items))
    logger.info(f"📊 过滤后: {len(filtered)}")

    if not filtered:
        logger.warning("⚠️ 没有符合条件的内容")
        return

    # 分类
    logger.info("📂 分类内容...")
    categories = await filter_.categorize_items(filtered)
    for cat, cat_items in categories.items():
        logger.info(f"  - {cat}: {len(cat_items)}")

    # 生成摘要
    if provider:
        logger.info("📝 生成关键要点...")
        summarizer = Summarizer(provider)
        for cat, cat_items in categories.items():
            points = await summarizer.extract_key_points(cat_items, max_points=3)
            if points:
                logger.info(f"  [{cat}] {points[0][:50]}...")

    # 格式化输出
    logger.info("\n🎨 生成输出...")
    formatter = MarkdownFormatter(output_dir=args.output or config.output_dir)

    date = args.date or datetime.now().strftime("%Y-%m-%d")
    summary_file = formatter.save_daily_summary(categories, date=date)

    logger.info("")
    logger.info("=" * 60)
    logger.info("✅ 完成!")
    logger.info("=" * 60)
    logger.info(f"📄 详细摘要: {summary_file}")
    logger.info(f"📊 总计: {len(filtered)} 条 / {len(categories)} 个分类")


def main():
    """同步入口 - 统一事件循环入口"""
    asyncio.run(main_async())


if __name__ == "__main__":
    main()
