"""AI 客户端模块 - 处理与多模型 API 的交互 (与 NASA 项目同步)."""

from __future__ import annotations

import json
import time
from typing import Any

from .ai_providers import build_model_candidates, is_quota_or_rate_limit_error
from .common import clean_json_string, fix_json_if_needed
from .config import (
    MAX_CONTENT_LENGTH,
    MAX_DETAIL_LENGTH,
    MAX_MODEL_ATTEMPTS,
    MAX_SUMMARY_LENGTH,
    NEWS_COUNT,
)


class AIClient:
    """多模型 AI 客户端 (与 NASA 项目同步)."""

    def __init__(self) -> None:
        """初始化 AI 客户端."""
        self.candidates = build_model_candidates()

    def is_configured(self) -> bool:
        """检查是否有可用的模型."""
        return len(self.candidates) > 0

    def _call_with_fallback(self, prompt: str) -> str | None:
        """使用多模型候选列表调用，支持自动回退."""
        attempts = 0
        last_error = None
        for provider, model_name, api_key, call_func in self.candidates:
            if attempts >= MAX_MODEL_ATTEMPTS:
                break
            try:
                print(f"🧠 尝试 {provider}/{model_name}...")
                result = call_func(api_key, prompt, model_name)
                print(f"   ✅ {provider}/{model_name} 成功")
                return result
            except Exception as e:
                error_msg = str(e)
                print(f"   ❌ {provider}/{model_name} 失败: {error_msg}")
                last_error = e
                if is_quota_or_rate_limit_error(error_msg):
                    attempts += 1
                    if attempts < MAX_MODEL_ATTEMPTS:
                        print(f"   ⏳ 切换到下一个模型...")
                        time.sleep(1)
                else:
                    attempts += 1
        print(f"❌ 所有模型尝试失败: {last_error}")
        return None

    def extract_news_list(self, content: str, today_date: str) -> list[dict[str, str]]:
        """从网页内容中提取今日热点新闻列表."""
        context = content[:MAX_CONTENT_LENGTH]
        prompt = f"""今天是北京时间：{today_date}。
请分析以下网页内容，严格筛选出【今天 ({today_date})】发布的、最热门的 {NEWS_COUNT} 条【硬件科技产品】新闻。
请严格返回 JSON 数组格式：
[{{"title": "新闻标题", "url": "链接地址"}}]
内容来源：{context}"""
        print(f"🧠 正在请求 AI 提取 {today_date} 的新闻...")
        response = self._call_with_fallback(prompt)
        if not response:
            return []
        cleaned = clean_json_string(response)
        try:
            data = json.loads(cleaned)
            return data[:NEWS_COUNT]
        except json.JSONDecodeError:
            try:
                fixed = fix_json_if_needed(cleaned)
                data = json.loads(fixed)
                return data[:NEWS_COUNT]
            except json.JSONDecodeError:
                print("❌ 无法解析 AI 返回的新闻列表")
                return []

    def extract_article_details(self, title: str, content: str) -> dict[str, Any] | None:
        """提取单篇新闻的详情."""
        context = content[:MAX_DETAIL_LENGTH]
        prompt = f"""请阅读这篇科技新闻，提取核心内容总结（{MAX_SUMMARY_LENGTH}字以内）和第一张产品图片的链接。
文章内容：{context}
请严格返回 JSON 格式：{{"content": "总结...", "images": ["图片URL"]}}"""
        response = self._call_with_fallback(prompt)
        if not response:
            return None
        cleaned = clean_json_string(response)
        try:
            data = json.loads(cleaned)
            return {"content": data.get("content", ""), "images": data.get("images", [])}
        except json.JSONDecodeError:
            print("⚠️ 详情 JSON 解析失败")
            return None


_client: AIClient | None = None


def get_ai_client() -> AIClient:
    """获取全局 AI 客户端实例."""
    global _client
    if _client is None:
        _client = AIClient()
    return _client
