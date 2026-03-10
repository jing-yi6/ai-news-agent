"""
统一配置管理
"""
import os
from dataclasses import dataclass
from typing import Self


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
