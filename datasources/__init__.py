"""
数据源工厂
"""
from datasources.base import BaseDataSource, ContentItem
from datasources.x_datasource import XDataSource
from datasources.mock_datasource import MockDataSource

# 注册表
DATASOURCE_REGISTRY: dict[str, type[BaseDataSource]] = {
    "x": XDataSource,
    "mock": MockDataSource,
}


def create_datasource(name: str, config: dict) -> BaseDataSource:
    """创建数据源实例"""
    name = name.lower()

    if name not in DATASOURCE_REGISTRY:
        available = ", ".join(DATASOURCE_REGISTRY.keys())
        raise ValueError(f"Unknown datasource: {name}. Available: {available}")

    return DATASOURCE_REGISTRY[name](config)


def list_available_datasources() -> list[str]:
    """列出可用的数据源"""
    return list(DATASOURCE_REGISTRY.keys())


__all__ = [
    "BaseDataSource",
    "ContentItem",
    "XDataSource",
    "MockDataSource",
    "create_datasource",
    "list_available_datasources",
    "DATASOURCE_REGISTRY",
]
