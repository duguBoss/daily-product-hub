"""AI 提供商模块 - 各 AI 服务的底层调用实现 (与 NASA 项目同步)."""

from __future__ import annotations

import re
from typing import Callable

import requests

from .config import (
    EXTRA_FALLBACK_MODEL_NAME,
    FALLBACK_MODEL_NAME,
    GEMINI_ADDITIONAL_FALLBACK_MODELS,
    GEMINI_API_KEY,
    GEMINI_REQUEST_TIMEOUT,
    GROQ_API_KEY,
    GROQ_MAX_TOKENS,
    GROQ_MODEL_SERIES,
    GROQ_REQUEST_TIMEOUT,
    OPENROUTER_API_KEY,
    OPENROUTER_BASE_URL,
    OPENROUTER_MAX_TOKENS,
    OPENROUTER_MODEL_SERIES,
    PRIMARY_MODEL_NAME,
)


def _request_timeout(read_timeout: int) -> tuple[int, int]:
    """返回连接超时和读取超时元组."""
    return (20, read_timeout)


def _response_excerpt(response: requests.Response, limit: int = 400) -> str:
    """获取响应内容的摘要."""
    try:
        body = response.text
    except Exception:
        body = ""
    return re.sub(r"\s+", " ", body).strip()[:limit]


def is_quota_or_rate_limit_error(error_text: str) -> bool:
    """检查错误是否为配额或速率限制错误."""
    text = error_text.lower()
    return (
        "resource_exhausted" in text
        or "quota exceeded" in text
        or "insufficient_quota" in text
        or "rate limit" in text
        or "too many requests" in text
        or "(429)" in text
        or " 429" in text
    )


def call_openrouter(api_key: str, prompt: str, model_name: str) -> str:
    """调用 OpenRouter API."""
    try:
        from openai import OpenAI
    except ImportError:
        raise RuntimeError("openai package not installed. Run: pip install openai")
    client = OpenAI(base_url=OPENROUTER_BASE_URL, api_key=api_key)
    completion = client.chat.completions.create(
        model=model_name,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=OPENROUTER_MAX_TOKENS,
        temperature=0.55,
        top_p=0.9,
        extra_headers={
            "HTTP-Referer": "https://github.com/duguBoss/daily-product-hub",
            "X-Title": "daily-product-hub",
        },
    )
    if not completion.choices:
        raise RuntimeError("OpenRouter returned empty choices.")
    return completion.choices[0].message.content or ""


def call_groq(api_key: str, prompt: str, model_name: str) -> str:
    """调用 Groq API."""
    try:
        from groq import Groq
    except ImportError:
        raise RuntimeError("groq package not installed. Run: pip install groq")
    client = Groq(api_key=api_key)
    completion = client.chat.completions.create(
        model=model_name,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.55,
        max_completion_tokens=GROQ_MAX_TOKENS,
        top_p=0.9,
        stream=True,
        stop=None,
    )
    chunks: list[str] = []
    for chunk in completion:
        content = chunk.choices[0].delta.content
        if content:
            chunks.append(content)
    result = "".join(chunks).strip()
    if not result:
        raise RuntimeError(f"Groq:{model_name} returned empty content")
    return result


def call_gemini(api_key: str, prompt: str, model_name: str) -> str:
    """调用 Gemini API."""
    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"{model_name}:generateContent?key={api_key}"
    )
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.55, "topP": 0.9, "responseMimeType": "application/json"},
    }
    response = requests.post(
        url,
        headers={"Content-Type": "application/json"},
        json=payload,
        timeout=_request_timeout(GEMINI_REQUEST_TIMEOUT),
    )
    if response.status_code != 200:
        raise RuntimeError(f"{model_name} failed ({response.status_code}): {_response_excerpt(response)}")
    result_json = response.json()
    candidate = (result_json.get("candidates") or [{}])[0]
    content = candidate.get("content", {})
    parts = content.get("parts") or []
    if not parts:
        raise RuntimeError(f"{model_name} returned empty content.")
    return parts[0].get("text", "")


def build_model_candidates() -> list[tuple[str, str, str, Callable[[str, str, str], str]]]:
    """构建模型候选列表（按优先级排序）."""
    candidates: list[tuple[str, str, str, Callable[[str, str, str], str]]] = []
    # OpenRouter 优先
    if OPENROUTER_API_KEY:
        models = [m.strip() for m in OPENROUTER_MODEL_SERIES if m.strip()]
        env_model = __import__("os").environ.get("OPENROUTER_MODEL_NAME", "").strip()
        if env_model:
            models = [env_model, *[m for m in models if m != env_model]]
        for model_name in models:
            candidates.append(("openrouter", model_name, OPENROUTER_API_KEY, call_openrouter))
    # Groq 备选
    if GROQ_API_KEY:
        models = [m.strip() for m in GROQ_MODEL_SERIES if m.strip()]
        env_model = __import__("os").environ.get("GROQ_MODEL_NAME", "").strip()
        if env_model:
            models = [env_model, *[m for m in models if m != env_model]]
        for model_name in models:
            candidates.append(("groq", model_name, GROQ_API_KEY, call_groq))
    # Gemini 最后备选
    if GEMINI_API_KEY:
        models = [
            PRIMARY_MODEL_NAME, FALLBACK_MODEL_NAME, EXTRA_FALLBACK_MODEL_NAME,
            *list(GEMINI_ADDITIONAL_FALLBACK_MODELS),
        ]
        for model_name in models:
            if model_name:
                candidates.append(("gemini", model_name, GEMINI_API_KEY, call_gemini))
    return candidates
