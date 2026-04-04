"""状态管理模块 - 处理已发布产品的记录和去重."""

from __future__ import annotations

import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from .config import MAX_SEEN_ITEMS, STATE_DIR, STATE_FILE


def load_published_state() -> dict[str, Any]:
    """加载已发布产品的状态.
    
    Returns:
        包含已发布产品信息的状态字典
    """
    if not STATE_FILE.exists():
        return {"published_items": [], "last_publish_date": ""}
    
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        print(f"⚠️ 加载状态文件失败: {e}，将创建新状态")
        return {"published_items": [], "last_publish_date": ""}


def save_published_state(state: dict[str, Any]) -> None:
    """保存已发布产品的状态.
    
    Args:
        state: 状态字典
    """
    try:
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
    except IOError as e:
        print(f"⚠️ 保存状态文件失败: {e}")


def get_published_identifiers(state: dict[str, Any]) -> set[str]:
    """获取已发布产品的唯一标识集合.
    
    使用产品标题作为唯一标识（去除空格和特殊字符后的小写形式）
    
    Args:
        state: 状态字典
        
    Returns:
        已发布产品标识集合
    """
    items = state.get("published_items", [])
    identifiers = set()
    for item in items:
        title = item.get("title", "")
        if title:
            # 使用标题的简化形式作为标识
            identifier = _normalize_identifier(title)
            identifiers.add(identifier)
    return identifiers


def _normalize_identifier(title: str) -> str:
    """标准化产品标题作为唯一标识.
    
    Args:
        title: 产品标题
        
    Returns:
        标准化后的标识字符串
    """
    # 移除多余空格，转小写，提取核心产品名
    normalized = title.lower().strip()
    # 移除常见的无意义词汇
    stop_words = ["发布", "上市", "开售", "首销", "新品", "正式", "推出", "上线"]
    for word in stop_words:
        normalized = normalized.replace(word, "")
    # 移除标点符号和多余空格
    import re
    normalized = re.sub(r'[^\w\s]', '', normalized)
    normalized = re.sub(r'\s+', '', normalized)
    return normalized


def add_published_items(state: dict[str, Any], items: list[dict[str, Any]], date_str: str) -> None:
    """添加新发布的产品到状态.
    
    Args:
        state: 状态字典
        items: 新发布的产品列表
        date_str: 发布日期字符串
    """
    published_items = state.get("published_items", [])
    
    for item in items:
        title = item.get("资讯标题", "")
        if title:
            published_items.append({
                "title": title,
                "date": date_str,
                "added_at": datetime.now().isoformat(),
            })
    
    # 限制历史记录数量，保留最新的
    if len(published_items) > MAX_SEEN_ITEMS:
        published_items = published_items[-MAX_SEEN_ITEMS:]
    
    state["published_items"] = published_items
    state["last_publish_date"] = date_str


def filter_new_items(
    candidates: list[dict[str, str]],
    published_identifiers: set[str],
) -> list[dict[str, str]]:
    """过滤掉已发布过的产品.
    
    Args:
        candidates: 候选产品列表
        published_identifiers: 已发布产品标识集合
        
    Returns:
        未发布过的新产品列表
    """
    new_items = []
    for item in candidates:
        title = item.get("title", "")
        identifier = _normalize_identifier(title)
        
        if identifier in published_identifiers:
            print(f"   🔄 已发布过，跳过: {title[:50]}...")
            continue
        
        new_items.append(item)
    
    return new_items


def cleanup_old_state(state: dict[str, Any], keep_days: int = 30) -> dict[str, Any]:
    """清理过旧的已发布记录.
    
    Args:
        state: 状态字典
        keep_days: 保留多少天的记录
        
    Returns:
        清理后的状态字典
    """
    published_items = state.get("published_items", [])
    if not published_items:
        return state
    
    cutoff_date = datetime.now() - timedelta(days=keep_days)
    
    filtered_items = []
    for item in published_items:
        added_at = item.get("added_at", "")
        if added_at:
            try:
                item_date = datetime.fromisoformat(added_at)
                if item_date >= cutoff_date:
                    filtered_items.append(item)
            except ValueError:
                # 日期格式错误，保留该项
                filtered_items.append(item)
        else:
            filtered_items.append(item)
    
    state["published_items"] = filtered_items
    return state
