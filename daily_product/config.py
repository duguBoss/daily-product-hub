"""全局配置模块."""

from __future__ import annotations

import os
from pathlib import Path


def _env_int(name: str, default: int) -> int:
    """从环境变量读取整数配置."""
    value = os.environ.get(name, "").strip()
    if not value:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _env_flag(name: str, default: bool) -> bool:
    """从环境变量读取布尔配置."""
    value = os.environ.get(name, "").strip().lower()
    if not value:
        return default
    return value in {"1", "true", "yes", "on"}


# ================= AI 模型配置 (与 NASA 项目同步) =================
# OpenRouter 模型系列（按优先级排序）
OPENROUTER_MODEL_SERIES = (
    "stepfun/step-3.5-flash:free",
    "qwen/qwen3.6-plus-preview:free",
    "nvidia/nemotron-3-super-120b-a12b:free",
    "arcee-ai/trinity-large-preview:free",
    "z-ai/glm-4.5-air:free",
    "nvidia/nemotron-3-nano-30b-a3b:free",
)

# Gemini 模型配置（备选）
PRIMARY_MODEL_NAME = "gemini-3.1-pro-preview"
FALLBACK_MODEL_NAME = "gemini-3-flash-preview"
EXTRA_FALLBACK_MODEL_NAME = "gemini-3.1-flash-lite-preview"
GEMINI_ADDITIONAL_FALLBACK_MODELS = (
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
    "gemini-2.5-pro",
)

# Groq 模型配置（备选）
GROQ_MODEL_SERIES = (
    "openai/gpt-oss-120b",
    "moonshotai/kimi-k2-instruct-0905",
    "groq/compound",
)

# API 配置
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
OPENROUTER_BASE_URL = os.environ.get("OPENROUTER_OPENAI_BASE_URL", "https://openrouter.ai/api/v1")
OPENROUTER_MAX_TOKENS = _env_int("OPENROUTER_MAX_TOKENS", 8192)
OPENROUTER_STREAM = _env_flag("OPENROUTER_STREAM", True)

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
GROQ_MAX_TOKENS = _env_int("GROQ_MAX_TOKENS", 8192)

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

# 请求超时配置 (秒)
REQUEST_TIMEOUT = _env_int("REQUEST_TIMEOUT", 45)
OPENROUTER_REQUEST_TIMEOUT = _env_int("OPENROUTER_REQUEST_TIMEOUT", max(REQUEST_TIMEOUT, 180))
GROQ_REQUEST_TIMEOUT = _env_int("GROQ_REQUEST_TIMEOUT", max(REQUEST_TIMEOUT, 180))
GEMINI_REQUEST_TIMEOUT = _env_int("GEMINI_REQUEST_TIMEOUT", REQUEST_TIMEOUT)

# 质量和重试策略 (与 NASA 项目同步)
MIN_QUALITY_SCORE = 92
MAX_MODEL_ATTEMPTS = 2

# 旧版兼容配置
AI_MODEL = OPENROUTER_MODEL_SERIES[0]
AI_REQUEST_TIMEOUT = OPENROUTER_REQUEST_TIMEOUT
MAX_RETRIES = MAX_MODEL_ATTEMPTS
RETRY_DELAY = 5

# ================= 数据源配置 =================
SOURCES = [
    "https://www.ithome.com",
    "https://www.mydrivers.com",
]

# ================= 输出配置 =================
OUTPUT_DIR = Path("data")
OUTPUT_FILE = OUTPUT_DIR / "daily_tech_news.json"

# 内容长度限制
MAX_CONTENT_LENGTH = 20000
MAX_DETAIL_LENGTH = 10000
MAX_SUMMARY_LENGTH = 300

# 新闻数量配置
NEWS_COUNT = 8

# Jina AI 配置
JINA_BASE_URL = "https://r.jina.ai"
JINA_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Referer": "https://www.google.com/",
    "X-Return-Format": "markdown",
}

# 请求间隔 (秒)
REQUEST_INTERVAL = 2
DETAIL_REQUEST_INTERVAL = 3
