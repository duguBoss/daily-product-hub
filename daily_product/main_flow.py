"""主流程模块 - 整合所有步骤的执行流程."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .ai_client import get_ai_client
from .common import save_json_file
from .config import OUTPUT_DIR
from .fetching import fetch_all_sources
from .processor import extract_article_details, extract_news_list
from .weixin_formatter import save_weixin_json


def validate_setup() -> bool:
    """验证运行环境配置.
    
    Returns:
        配置是否有效
    """
    client = get_ai_client()
    
    if not client.is_configured():
        print("❌ 致命错误: 未配置 OPENROUTER_API_KEY")
        return False
    
    return True


def fetch_sources() -> str:
    """抓取所有数据源.
    
    Returns:
        合并后的所有来源内容
    """
    print("📡 开始抓取数据源...")
    content = fetch_all_sources()
    
    if not content:
        print("❌ 所有来源抓取失败，无法进行后续分析。")
        print("⚠️ 终止更新，保留原有数据。")
        return ""
    
    return content


def extract_news(content: str) -> list[dict[str, str]]:
    """提取今日热点新闻列表.
    
    Args:
        content: 网页内容
        
    Returns:
        新闻列表
    """
    print("🔍 提取今日热点新闻...")
    news_list = extract_news_list(content)
    print(f"✅ 提取到 {len(news_list)} 条今日新闻")
    
    if not news_list:
        print("⚠️ 未提取到有效新闻，可能是因为今天还没有更新或 AI 解析失败。")
        print("⚠️ 终止更新，保留原有数据。")
    
    return news_list


def process_details(news_list: list[dict[str, str]]) -> list[dict[str, Any]]:
    """处理新闻详情.
    
    Args:
        news_list: 新闻列表
        
    Returns:
        包含完整详情的新闻列表
    """
    if not news_list:
        return []
    
    print("📝 开始提取新闻详情...")
    final_result = extract_article_details(news_list)
    print(f"✅ 成功处理 {len(final_result)} 条新闻")
    
    return final_result


def save_results(final_result: list[dict[str, Any]]) -> bool:
    """保存处理结果.
    
    Args:
        final_result: 最终的新闻数据列表
        
    Returns:
        是否保存成功
    """
    if not final_result:
        print("❌ 所有详情分析均失败或无效。")
        print("⚠️ 终止更新，保留原有数据。")
        return False
    
    # 保存标准 JSON
    success = save_json_file(final_result)
    
    # 保存微信发文 JSON
    if success:
        weixin_output = Path(OUTPUT_DIR) / "daily_tech_news_weixin.json"
        save_weixin_json(final_result, str(weixin_output))
    
    if success:
        print("\n📊 处理结果预览:")
        print(json.dumps(final_result, ensure_ascii=False, indent=2))
    
    return success


def run_pipeline() -> bool:
    """运行完整的处理流程.
    
    Returns:
        流程是否成功完成
    """
    # 1. 验证配置
    if not validate_setup():
        return False
    
    # 2. 抓取数据源
    content = fetch_sources()
    if not content:
        return False
    
    # 3. 提取新闻列表
    news_list = extract_news(content)
    if not news_list:
        return False
    
    # 4. 提取详情
    final_result = process_details(news_list)
    
    # 5. 保存结果
    return save_results(final_result)
