"""通用工具函数模块."""

from __future__ import annotations

import datetime
import json
import re
from pathlib import Path
from typing import Any

from .config import OUTPUT_DIR, OUTPUT_FILE


def get_beijing_date() -> str:
    """获取北京时间今天的日期字符串 (YYYY-MM-DD)."""
    utc_now = datetime.datetime.utcnow()
    beijing_now = utc_now + datetime.timedelta(hours=8)
    return beijing_now.strftime("%Y-%m-%d")


def ensure_dir() -> None:
    """确保输出目录存在."""
    if not OUTPUT_DIR.exists():
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def save_json_file(data: list[dict[str, Any]]) -> bool:
    """保存数据到 JSON 文件.
    
    使用 'w' 模式，每次写入都会清空旧内容，只保存最新一次的结果.
    
    Args:
        data: 要保存的数据列表
        
    Returns:
        是否保存成功
    """
    ensure_dir()
    try:
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        print(f"✅ 数据已覆盖保存至: {OUTPUT_FILE}")
        return True
    except Exception as e:
        print(f"❌ 保存文件失败: {e}")
        return False


def clean_json_string(text: str) -> str:
    """清洗 AI 返回的 JSON 字符串.
    
    去除 markdown 代码块标记，提取纯 JSON 内容.
    
    Args:
        text: AI 返回的原始文本
        
    Returns:
        清洗后的 JSON 字符串
    """
    if not text:
        return ""
    text = text.strip()
    match = re.search(r'```(?:json)?\s*(.*?)\s*```', text, re.DOTALL | re.IGNORECASE)
    if match:
        text = match.group(1).strip()
    return text


def fix_json_if_needed(text: str) -> str:
    """尝试修复常见的 JSON 格式错误.
    
    例如未闭合的数组等.
    
    Args:
        text: JSON 字符串
        
    Returns:
        修复后的字符串
    """
    text = text.strip()
    if text.startswith("[") and not text.endswith("]"):
        text += "]"
    return text


def normalize_url(url: str, source_hint: str = "") -> str:
    """补全相对路径 URL.
    
    Args:
        url: 原始 URL，可能是相对路径
        source_hint: 内容来源提示，用于判断补全的域名
        
    Returns:
        完整的绝对 URL
    """
    if not url:
        return url
        
    if url.startswith("http://") or url.startswith("https://"):
        return url
        
    if url.startswith("/"):
        if "ithome" in source_hint and "mydrivers" not in url:
            return f"https://www.ithome.com{url}"
        else:
            return f"https://www.mydrivers.com{url}"
    
    return url


def is_valid_content(content: str | None) -> bool:
    """检查内容是否有效.
    
    排除空内容、提取失败标记等无效内容.
    
    Args:
        content: 内容字符串
        
    Returns:
        是否有效
    """
    if not content:
        return False
    invalid_markers = ["内容提取失败", "提取失败"]
    return not any(marker in content for marker in invalid_markers)
