# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AI News Agent is a Python tool that fetches AI-related tweets from X (Twitter), filters and categorizes them, and generates daily Markdown digests. It uses `twscrape` for scraping (not X API), and supports LLM-based intelligent categorization.

## Common Commands

```bash
# Setup environment
conda env create -f environment.yml
conda activate ai-news-agent

# Configure
cp .env.example .env
# Edit .env with X credentials (cookies or username/password)

# Run with mock data (for testing)
python run.py --mock

# Run with X datasource
python run.py --users OpenAI DeepMind AnthropicAI

# Run with LLM categorization
python run.py --users OpenAI --use-llm

# See all options
python run.py --help
```

## Architecture

### Plugin-Based Design

The codebase uses a plugin architecture for extensibility:

1. **Datasources** (`datasources/`): Fetch content from different sources
   - `BaseDataSource`: Abstract base with async methods (`fetch_by_users`, `fetch_by_followings`, `get_user_id`)
   - `XDataSource`: Uses `twscrape` to scrape X/Twitter
   - `MockDataSource`: Provides test data
   - New datasources must inherit `BaseDataSource` and be registered in `datasources/__init__.py`

2. **LLM Providers** (`providers/`): Abstraction for different LLM APIs
   - `BaseLLMProvider`: Abstract base with `chat_complete()` method
   - `OpenAIProvider`: OpenAI-compatible APIs (OpenAI, Azure, Ollama, OpenRouter)
   - `AnthropicProvider`: Anthropic Claude
   - New providers must inherit `BaseLLMProvider` and be registered in `providers/__init__.py`

3. **Processors** (`processors/`): Data transformation pipeline
   - `ContentFilter`: Filters by keywords/engagement, categorizes content
   - `Summarizer`: Generates LLM-based summaries
   - `MarkdownFormatter`: Outputs Markdown digests

### Async Architecture

All datasource methods are async and return `AsyncIterator[ContentItem]`. The main entry point is `main_async()` which is called via `asyncio.run(main_async())` in `run.py`. This ensures:
- Single event loop entry point (no `asyncio.run()` conflicts)
- Jupyter/Notebook compatibility
- Proper async/await patterns throughout

### Configuration

Configuration is managed via `config.py` with environment variables:

**Required for X datasource:**
- `X_COOKIES` (recommended) or `X_USERNAME` + `X_PASSWORD`
- `X_EMAIL`, `X_EMAIL_PASSWORD` (optional, for login verification)

**Optional:**
- `X_USER_ID`: For fetching followings list
- `X_RATE_LIMIT`: Request rate limit in seconds (default: 1.0)
- `LLM_API_KEY`, `LLM_PROVIDER`, `LLM_BASE_URL`, `LLM_MODEL`: For LLM features

**Behavior flags:**
- `REQUIRE_AI_KEYWORDS`: Filter by AI keywords (default: false)
- `EXCLUDE_PROMOTIONAL`: Exclude promotional content (default: false)

### Data Flow

```
run.py
  → parse_args()
  → create_datasource()  # Based on --datasource or env
  → datasource.fetch_by_*()  # Async iteration
  → ContentFilter.filter_items()  # Keyword filtering
  → ContentFilter.categorize_items()  # LLM or keyword categorization
  → [Optional] Summarizer.extract_key_points()  # LLM summary
  → MarkdownFormatter.save_daily_summary()  # Output
```

### Rate Limiting

`XClient` passes `rate_limit` parameter to `twscrape.API(rate_limit=X)`. This controls request pacing to avoid account restrictions.

### Key Implementation Details

- **Classification**: `ContentFilter` uses LLM categorization only when both `use_llm_categorize=True` AND `llm_provider` is provided. Otherwise falls back to keyword matching.
- **Time Windows**: `get_time_window()` in `run.py` generates ISO 8601 timestamps for the past 24 hours.
- **Output**: Generated Markdown files are saved to `output/` directory with format `YYYY-MM-DD.md`.

### Testing

Use `--mock` flag to test without X credentials. Mock data is defined in `MockDataSource._generate_items()`.

### Adding Features

**New DataSource:**
1. Create class inheriting `BaseDataSource` in `datasources/`
2. Implement async methods returning `AsyncIterator[ContentItem]`
3. Register in `DATASOURCE_REGISTRY` in `datasources/__init__.py`

**New LLM Provider:**
1. Create class inheriting `BaseLLMProvider` in `providers/`
2. Implement `chat_complete()`, `_init_client()`, `is_available()`
3. Register in `PROVIDER_REGISTRY` in `providers/__init__.py`
