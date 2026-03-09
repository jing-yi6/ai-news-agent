#!/usr/bin/env python3
"""
AI News Agent - 每日 AI 资讯摘要生成器

使用方法:
    python run.py                          # 获取关注列表的推文
    python run.py --users user1 user2      # 获取指定用户的推文
    python run.py --mock                   # 使用模拟数据测试
    python run.py --date 2024-01-15        # 指定日期（用于测试）
"""
import os
import sys
import argparse
from datetime import datetime, timedelta
from typing import List, Optional

# 添加 src 到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.x_client import XClient
from src.fetcher import TweetFetcher
from src.filter import TweetFilter
from src.summarizer import TweetSummarizer
from src.formatter import MarkdownFormatter


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="AI News Agent - 每日 AI 资讯摘要生成器"
    )
    parser.add_argument(
        "--users",
        nargs="+",
        help="指定要获取的用户名列表（不含 @）"
    )
    parser.add_argument(
        "--user-id",
        help="指定用户 ID（用于获取关注列表）"
    )
    parser.add_argument(
        "--mock",
        action="store_true",
        help="使用模拟数据测试"
    )
    parser.add_argument(
        "--date",
        help="指定日期 (YYYY-MM-DD)，用于测试"
    )
    parser.add_argument(
        "--output",
        default="output",
        help="输出目录（默认: output）"
    )
    parser.add_argument(
        "--max-following",
        type=int,
        default=30,
        help="最多获取多少个关注用户（默认: 30）"
    )
    parser.add_argument(
        "--tweets-per-user",
        type=int,
        default=30,
        help="每个用户获取多少条推文（默认: 30）"
    )
    parser.add_argument(
        "--min-engagement",
        type=int,
        default=0,
        help="最小互动数过滤（默认: 0）"
    )
    parser.add_argument(
        "--use-llm",
        action="store_true",
        help="使用 LLM 生成摘要（需要 OPENAI_API_KEY 或 ANTHROPIC_API_KEY）"
    )
    
    return parser.parse_args()


def generate_mock_data() -> dict:
    """生成模拟数据用于测试"""
    from datetime import datetime, timezone
    
    now = datetime.now(timezone.utc)
    
    mock_tweets = {
        "OpenAI": [
            {
                "id": "1234567890",
                "text": "Excited to announce GPT-5 preview with significant improvements in reasoning and coding capabilities. Available to ChatGPT Plus subscribers next week!",
                "created_at": now.isoformat(),
                "author_username": "OpenAI",
                "author_name": "OpenAI",
                "public_metrics": {
                    "like_count": 15420,
                    "retweet_count": 3420,
                    "reply_count": 890,
                    "quote_count": 567
                }
            },
            {
                "id": "1234567891",
                "text": "New research paper on constitutional AI training methods published today. Check out our latest blog post for details.",
                "created_at": (now - timedelta(hours=2)).isoformat(),
                "author_username": "OpenAI",
                "author_name": "OpenAI",
                "public_metrics": {
                    "like_count": 8234,
                    "retweet_count": 1890,
                    "reply_count": 234,
                    "quote_count": 123
                }
            }
        ],
        "DeepMind": [
            {
                "id": "2234567890",
                "text": "AlphaFold 3 is here! Our latest breakthrough in protein structure prediction achieves unprecedented accuracy. Open source release coming soon.",
                "created_at": (now - timedelta(hours=4)).isoformat(),
                "author_username": "DeepMind",
                "author_name": "Google DeepMind",
                "public_metrics": {
                    "like_count": 22100,
                    "retweet_count": 5670,
                    "reply_count": 1200,
                    "quote_count": 890
                }
            }
        ],
        "karpathy": [
            {
                "id": "3234567890",
                "text": "Just released a new tutorial on building LLMs from scratch. 3 hours of deep dive into transformer architecture, attention mechanisms, and training pipelines.",
                "created_at": (now - timedelta(hours=6)).isoformat(),
                "author_username": "karpathy",
                "author_name": "Andrej Karpathy",
                "public_metrics": {
                    "like_count": 18500,
                    "retweet_count": 4200,
                    "reply_count": 567,
                    "quote_count": 340
                }
            }
        ],
        "AnthropicAI": [
            {
                "id": "4234567890",
                "text": "Claude 3.5 Sonnet is now available with enhanced coding abilities and longer context window (200K tokens). Try it today!",
                "created_at": (now - timedelta(hours=8)).isoformat(),
                "author_username": "AnthropicAI",
                "author_name": "Anthropic",
                "public_metrics": {
                    "like_count": 12300,
                    "retweet_count": 2800,
                    "reply_count": 456,
                    "quote_count": 234
                }
            }
        ],
        "huggingface": [
            {
                "id": "5234567890",
                "text": "New state-of-the-art open source models added to the Hub this week: Mixtral 8x22B, Qwen2-72B, and Llama 3 70B. All available for immediate download!",
                "created_at": (now - timedelta(hours=10)).isoformat(),
                "author_username": "huggingface",
                "author_name": "Hugging Face",
                "public_metrics": {
                    "like_count": 9800,
                    "retweet_count": 2100,
                    "reply_count": 234,
                    "quote_count": 178
                }
            }
        ]
    }
    
    return mock_tweets


def main():
    """主函数"""
    args = parse_args()
    
    print("=" * 60)
    print("🤖 AI News Agent - 每日 AI 资讯摘要生成器")
    print("=" * 60)
    print()
    
    # 使用模拟数据模式
    if args.mock:
        print("📝 使用模拟数据模式")
        all_tweets = generate_mock_data()
    else:
        # 检查环境变量
        bearer_token = os.getenv("X_BEARER_TOKEN")
        user_id = args.user_id or os.getenv("X_USER_ID")
        
        if not bearer_token:
            print("❌ 错误: 未设置 X_BEARER_TOKEN 环境变量")
            print("请复制 .env.example 为 .env 并填写你的 API 密钥")
            print()
            print("或者使用 --mock 参数运行测试模式:")
            print("  python run.py --mock")
            sys.exit(1)
        
        # 初始化客户端
        try:
            client = XClient(bearer_token=bearer_token)
            fetcher = TweetFetcher(client=client)
        except Exception as e:
            print(f"❌ 初始化 X API 客户端失败: {e}")
            sys.exit(1)
        
        # 获取推文
        print("🔍 开始获取推文...")
        print()
        
        if args.users:
            # 获取指定用户
            print(f"获取指定用户: {', '.join(args.users)}")
            all_tweets = fetcher.fetch_specific_users_tweets(
                usernames=args.users,
                tweets_per_user=args.tweets_per_user
            )
        elif user_id:
            # 获取关注列表
            print(f"获取用户 {user_id} 的关注列表")
            all_tweets = fetcher.fetch_following_tweets(
                user_id=user_id,
                max_following=args.max_following,
                tweets_per_user=args.tweets_per_user
            )
        else:
            # 未指定用户或用户ID
            print("❌ 错误: 未指定用户列表或用户 ID")
            print()
            print("请使用以下方式之一指定要获取的推文来源:")
            print("  1. 指定用户列表: python run.py --users user1 user2")
            print("  2. 指定用户 ID 获取关注列表: python run.py --user-id <user_id>")
            print("  3. 设置环境变量 X_USER_ID 并使用 --user-id 参数")
            print()
            print("或使用模拟数据测试:")
            print("  python run.py --mock")
            sys.exit(1)
    
    # 统计原始推文数
    total_raw = sum(len(tweets) for tweets in all_tweets.values())
    print()
    print(f"📊 原始推文数: {total_raw}")
    
    if total_raw == 0:
        print("⚠️ 未获取到任何推文")
        sys.exit(0)
    
    # 扁平化推文列表
    all_tweets_flat = []
    for username, tweets in all_tweets.items():
        all_tweets_flat.extend(tweets)
    
    # 过滤推文
    print("🔍 过滤 AI 相关内容...")
    filter_obj = TweetFilter(
        min_engagement=args.min_engagement,
        require_ai_keywords=True,
        exclude_promotional=True
    )
    filtered_tweets = filter_obj.filter_tweets(all_tweets_flat)
    print(f"📊 过滤后推文数: {len(filtered_tweets)}")
    
    if not filtered_tweets:
        print("⚠️ 过滤后没有符合条件的推文")
        sys.exit(0)
    
    # 分类推文
    print("📂 分类推文...")
    categorized = filter_obj.categorize_tweets(filtered_tweets)
    for category, tweets in categorized.items():
        print(f"  - {category}: {len(tweets)} 条")
    
    # 生成摘要
    if args.use_llm:
        print("📝 使用 LLM 生成摘要...")
        summarizer = TweetSummarizer(use_llm=True)
        summary_data = summarizer.generate_daily_summary(categorized)
    else:
        summarizer = TweetSummarizer(use_llm=False)
        summary_data = None
    
    # 格式化输出
    print("🎨 生成 Markdown 输出...")
    formatter = MarkdownFormatter(output_dir=args.output)
    
    date = args.date or datetime.now().strftime("%Y-%m-%d")
    output_file = formatter.save_daily_summary(
        categorized_tweets=categorized,
        date=date
    )
    
    # 同时生成快速预览
    quick_view_file = formatter.save_simple_list(
        tweets=filtered_tweets,
        filename=f"{date}_quick_view.md"
    )
    
    print()
    print("=" * 60)
    print("✅ 完成!")
    print("=" * 60)
    print()
    print(f"📄 详细摘要: {output_file}")
    print(f"📄 快速预览: {quick_view_file}")
    print()
    print(f"📊 统计:")
    print(f"  - 原始推文: {total_raw}")
    print(f"  - AI 相关: {len(filtered_tweets)}")
    print(f"  - 分类数: {len(categorized)}")
    print()


if __name__ == "__main__":
    main()
