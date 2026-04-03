"""数据处理模块 - 处理新闻列表和详情提取."""

from __future__ import annotations

from typing import Any

from .ai_client import get_ai_client
from .common import get_beijing_date, is_valid_content, normalize_url
from .fetching import fetch_article_detail
from .image_processor import process_images


def extract_news_list(content: str) -> list[dict[str, str]]:
    """从网页内容中提取今日热点新闻列表.
    
    Args:
        content: 合并后的网页内容
        
    Returns:
        新闻列表，每项包含 title 和 url
    """
    client = get_ai_client()
    today = get_beijing_date()
    
    raw_list = client.extract_news_list(content, today)
    
    # 链接补全与清洗
    valid_data = []
    for item in raw_list:
        url = item.get("url", "")
        title = item.get("title", "")
        
        if not url:
            continue
        
        url = normalize_url(url, content)
        valid_data.append({"title": title, "url": url})
    
    return valid_data


def extract_article_details(
    news_list: list[dict[str, str]],
) -> list[dict[str, Any]]:
    """批量提取新闻详情.
    
    Args:
        news_list: 新闻列表，每项包含 title 和 url
        
    Returns:
        包含完整信息的新闻列表
    """
    client = get_ai_client()
    final_result = []
    
    for news in news_list:
        title = news.get("title", "")
        url = news.get("url", "")
        
        if not url:
            continue
        
        detail = fetch_article_detail(url, title)
        if not detail:
            continue
        
        ai_result = client.extract_article_details(title, detail["content"])
        
        if not ai_result:
            print(f"   ⚠️ AI 提取详情失败，跳过: {title}")
            continue
        
        content = ai_result.get("content", "")
        
        if not is_valid_content(content):
            print(f"   ⚠️ 内容无效，跳过: {title}")
            continue
        
        image_urls = ai_result.get("images", [])
        processed_images = process_images(image_urls) if image_urls else []
        
        final_result.append({
            "资讯标题": title,
            "内容": content,
            "配图": processed_images,
        })
    
    return final_result


def process_single_article(
    title: str,
    url: str,
) -> dict[str, Any] | None:
    """处理单篇新闻.
    
    Args:
        title: 新闻标题
        url: 新闻链接
        
    Returns:
        处理后的新闻数据，失败返回 None
    """
    client = get_ai_client()
    
    detail = fetch_article_detail(url, title)
    if not detail:
        return None
    
    ai_result = client.extract_article_details(title, detail["content"])
    if not ai_result:
        print(f"   ⚠️ AI 提取详情失败，跳过: {title}")
        return None
    
    content = ai_result.get("content", "")
    if not is_valid_content(content):
        print(f"   ⚠️ 内容无效，跳过: {title}")
        return None
    
    image_urls = ai_result.get("images", [])
    processed_images = process_images(image_urls) if image_urls else []
    
    return {
        "资讯标题": title,
        "内容": content,
        "配图": processed_images,
    }
