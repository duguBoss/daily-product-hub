"""内容获取模块 - 处理网页抓取."""

from __future__ import annotations

import time
from typing import Any

import requests

from .common import normalize_url
from .config import (
    DETAIL_REQUEST_INTERVAL,
    JINA_BASE_URL,
    JINA_HEADERS,
    MAX_RETRIES,
    REQUEST_INTERVAL,
    REQUEST_TIMEOUT,
    RETRY_DELAY,
    SOURCES,
)


def fetch_jina_content(url: str) -> str:
    """使用 Jina AI 读取网页内容.
    
    伪装成浏览器以避免 IP 被封。
    
    Args:
        url: 目标网页 URL
        
    Returns:
        网页内容的 Markdown 格式文本，失败返回空字符串
    """
    print(f"🌐 正在请求 Jina 读取: {url}")
    jina_url = f"{JINA_BASE_URL}/{url}"
    
    for attempt in range(MAX_RETRIES):
        try:
            resp = requests.get(
                jina_url,
                headers=JINA_HEADERS,
                timeout=REQUEST_TIMEOUT,
            )
            
            if resp.status_code == 429:
                print("   ⚠️ 触发速率限制，等待 10 秒...")
                time.sleep(10)
                continue
            
            if resp.status_code != 200:
                print(f"   ❌ HTTP 错误 {resp.status_code}")
                if attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_DELAY)
                continue

            text = resp.text
            if len(text) < 200:
                print(f"   ⚠️ 内容过短 ({len(text)} 字符)，可能是空页面或验证码。")
                if attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_DELAY)
                continue
                
            return text
            
        except requests.Timeout:
            print(f"   ❌ 请求超时 (第 {attempt + 1} 次)")
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY)
        except Exception as e:
            print(f"   ❌ 请求异常 (第 {attempt + 1} 次): {e}")
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY)
            
    return ""


def fetch_all_sources() -> str:
    """抓取所有配置的数据源主页内容.
    
    Returns:
        合并后的所有来源内容
    """
    full_content = ""
    
    for site in SOURCES:
        text = fetch_jina_content(site)
        print(f"   [{site}] 获取长度: {len(text)}")
        
        if len(text) > 500:
            full_content += f"\n=== 来源: {site} ===\n{text}\n"
        
        time.sleep(REQUEST_INTERVAL)
    
    return full_content


def fetch_article_detail(url: str, title: str = "") -> dict[str, Any] | None:
    """获取单篇新闻的详情内容.
    
    Args:
        url: 新闻详情页 URL
        title: 新闻标题（用于日志）
        
    Returns:
        包含 url 和 content 的字典，失败返回 None
    """
    if title:
        print(f"  -> 分析详情: {title}")
    
    time.sleep(DETAIL_REQUEST_INTERVAL)
    
    content = fetch_jina_content(url)
    if not content:
        print("     (跳过：未获取到详情页内容)")
        return None
    
    return {
        "url": url,
        "content": content,
    }
