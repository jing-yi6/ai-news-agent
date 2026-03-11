"""
统一配置管理
"""
import logging
import os
from dataclasses import dataclass
from datetime import datetime
from typing import Self


def setup_logging(
    console_level: int = logging.INFO,
    file_level: int = logging.INFO,
    log_dir: str = "logs"
) -> str:
    """设置日志配置

    Args:
        console_level: 控制台日志级别（默认 INFO）
        file_level: 文件日志级别（默认 INFO）
        log_dir: 日志文件目录（默认 logs）

    Returns:
        生成的日志文件路径
    """
    # 生成带时间戳的日志文件名
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(log_dir, f"ai-news_{timestamp}.log")
    os.makedirs(log_dir, exist_ok=True)

    # 创建根 logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)  # 允许所有级别，由 handler 过滤

    # 清除现有 handlers
    root_logger.handlers.clear()

    # 控制台 handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(console_level)
    console_format = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S'
    )
    console_handler.setFormatter(console_format)
    root_logger.addHandler(console_handler)

    # 文件 handler
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(file_level)
    file_format = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(file_format)
    root_logger.addHandler(file_handler)

    # 过滤第三方库的日志（只保留 WARNING 及以上）
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("twscrape").setLevel(logging.WARNING)

    # 记录启动信息
    logger = logging.getLogger(__name__)
    logger.info(f"日志系统初始化完成")
    logger.info(f"日志文件: {log_file}")

    return log_file


def _load_dotenv():
    """加载 .env 文件"""
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass


@dataclass(frozen=True, slots=True)
class LLMConfig:
    """LLM 配置"""
    provider: str
    api_key: str
    base_url: str
    model: str
    temperature: float = 0.3
    max_tokens: int = 1000

    def __post_init__(self):
        """验证配置值"""
        # 验证 temperature 范围
        if not 0 <= self.temperature <= 2:
            raise ValueError(f"temperature must be between 0 and 2, got {self.temperature}")
        # 验证 max_tokens
        if self.max_tokens < 1:
            raise ValueError(f"max_tokens must be positive, got {self.max_tokens}")
        # 验证 provider
        valid_providers = {"openai", "anthropic"}
        if self.provider.lower() not in valid_providers:
            raise ValueError(f"provider must be one of {valid_providers}, got {self.provider}")

    @classmethod
    def from_env(cls) -> Self | None:
        """从环境变量加载"""
        if api_key := os.getenv("LLM_API_KEY"):
            return cls(
                provider=os.getenv("LLM_PROVIDER", "openai").lower(),
                api_key=api_key,
                base_url=os.getenv("LLM_BASE_URL", "https://api.openai.com/v1"),
                model=os.getenv("LLM_MODEL", "gpt-3.5-turbo"),
                temperature=float(os.getenv("LLM_TEMPERATURE", "0.3")),
                max_tokens=int(os.getenv("LLM_MAX_TOKENS", "1000")),
            )

        return None


@dataclass(frozen=True, slots=True)
class DataSourceConfig:
    """数据源配置"""
    name: str
    config: dict

    def __post_init__(self):
        """验证配置值"""
        valid_datasources = {"x", "mock"}
        if self.name.lower() not in valid_datasources:
            raise ValueError(f"datasource must be one of {valid_datasources}, got {self.name}")

        # 验证 rate_limit 如果存在
        rate_limit = self.config.get("rate_limit")
        if rate_limit is not None:
            try:
                rl = float(rate_limit)
                if rl < 0:
                    raise ValueError(f"rate_limit must be non-negative, got {rl}")
            except (ValueError, TypeError):
                raise ValueError(f"rate_limit must be a number, got {rate_limit}")

    @classmethod
    def from_env(cls) -> Self:
        """从环境变量加载"""
        name = os.getenv("DATASOURCE", "x").lower()

        if name == "mock":
            return cls(name="mock", config={})

        return cls(
            name=name,
            config={
                # twscrape 账号配置
                "username": os.getenv("X_USERNAME"),
                "password": os.getenv("X_PASSWORD"),
                "email": os.getenv("X_EMAIL"),
                "email_password": os.getenv("X_EMAIL_PASSWORD"),
                "cookies": os.getenv("X_COOKIES"),
                # 用户 ID（用于获取关注列表）
                "user_id": os.getenv("X_USER_ID"),
                # 请求速率限制（秒/次）
                "rate_limit": os.getenv("X_RATE_LIMIT", "1.0"),
            }
        )


@dataclass(frozen=True, slots=True)
class AppConfig:
    """应用配置"""
    llm: LLMConfig | None
    datasource: DataSourceConfig
    output_dir: str
    min_engagement: int
    require_ai_keywords: bool
    exclude_promotional: bool
    translate_sources: set[str]  # 需要翻译的数据源列表

    def __post_init__(self):
        """验证配置值"""
        # 验证 min_engagement
        if self.min_engagement < 0:
            raise ValueError(f"min_engagement must be non-negative, got {self.min_engagement}")

    @classmethod
    def load(cls) -> Self:
        """加载完整配置"""
        _load_dotenv()

        # 解析需要翻译的数据源（默认不翻译）
        translate_env = os.getenv("TRANSLATE_SOURCES", "").lower()
        translate_sources = set(s.strip() for s in translate_env.split(",") if s.strip())

        return cls(
            llm=LLMConfig.from_env(),
            datasource=DataSourceConfig.from_env(),
            output_dir=os.getenv("OUTPUT_DIR", "output"),
            min_engagement=int(os.getenv("MIN_ENGAGEMENT", "0")),
            require_ai_keywords=os.getenv("REQUIRE_AI_KEYWORDS", "false").lower() == "true",
            exclude_promotional=os.getenv("EXCLUDE_PROMOTIONAL", "false").lower() == "true",
            translate_sources=translate_sources,
        )
