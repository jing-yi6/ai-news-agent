"""
统一配置管理
"""
import logging
import os
from dataclasses import dataclass
from typing import Self


def setup_logging(level: int = logging.INFO, log_file: str | None = None) -> None:
    """设置日志配置

    Args:
        level: 日志级别 (DEBUG, INFO, WARNING, ERROR)
        log_file: 日志文件路径，为 None 则只输出到控制台
    """
    handlers: list[logging.Handler] = [logging.StreamHandler()]

    if log_file:
        os.makedirs(os.path.dirname(log_file) or '.', exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(level)
        handlers.append(file_handler)

    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        handlers=handlers
    )


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

    def __post_init__(self):
        """验证配置值"""
        # 验证 min_engagement
        if self.min_engagement < 0:
            raise ValueError(f"min_engagement must be non-negative, got {self.min_engagement}")

    @classmethod
    def load(cls) -> Self:
        """加载完整配置"""
        _load_dotenv()

        return cls(
            llm=LLMConfig.from_env(),
            datasource=DataSourceConfig.from_env(),
            output_dir=os.getenv("OUTPUT_DIR", "output"),
            min_engagement=int(os.getenv("MIN_ENGAGEMENT", "0")),
            require_ai_keywords=os.getenv("REQUIRE_AI_KEYWORDS", "false").lower() == "true",
            exclude_promotional=os.getenv("EXCLUDE_PROMOTIONAL", "false").lower() == "true",
        )
