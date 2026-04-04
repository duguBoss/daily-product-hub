"""主流程模块 - 整合所有步骤的执行流程."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .ai_client import get_ai_client
from .common import get_beijing_date, save_json_file
from .config import NEWS_COUNT, OUTPUT_DIR
from .fetching import fetch_all_sources
from .processor import extract_article_details, extract_news_list
from .state_manager import (
    add_published_items,
    filter_new_items,
    get_published_identifiers,
    load_published_state,
    save_published_state,
)
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
    
    # 加载已发布状态
    print("\n📋 加载已发布产品记录...")
    state = load_published_state()
    published_identifiers = get_published_identifiers(state)
    print(f"   已记录 {len(published_identifiers)} 个已发布产品")
    
    # 2. 抓取数据源
    content = fetch_sources()
    if not content:
        return False
    
    # 3. 提取新闻列表
    news_list = extract_news(content)
    if not news_list:
        return False
    
    # 4. 去重：过滤已发布过的产品
    print(f"\n🔄 开始去重检查...")
    new_news_list = filter_new_items(news_list, published_identifiers)
    print(f"   候选产品: {len(news_list)} 个")
    print(f"   新产品: {len(new_news_list)} 个")
    
    # 如果新产品不足5个，尝试从候选中补充（可能是状态文件丢失导致）
    if len(new_news_list) < NEWS_COUNT and len(news_list) >= NEWS_COUNT:
        print(f"   ⚠️ 新产品不足 {NEWS_COUNT} 个，从候选中补充...")
        # 使用原始列表，但优先使用新产品
        used_identifiers = {item.get("title", "") for item in new_news_list}
        for item in news_list:
            if len(new_news_list) >= NEWS_COUNT:
                break
            title = item.get("title", "")
            if title and title not in used_identifiers:
                new_news_list.append(item)
                used_identifiers.add(title)
        print(f"   补充后产品数: {len(new_news_list)} 个")
    
    if not new_news_list:
        print("❌ 没有新产品可发布")
        print("⚠️ 终止更新，保留原有数据。")
        return False
    
    # 限制为最多 NEWS_COUNT 个
    new_news_list = new_news_list[:NEWS_COUNT]
    print(f"   将处理前 {len(new_news_list)} 个产品")
    
    # 5. 提取详情
    final_result = process_details(new_news_list)
    
    # 6. 保存结果
    success = save_results(final_result)
    
    # 7. 更新已发布状态
    if success and final_result:
        today = get_beijing_date()
        add_published_items(state, final_result, today)
        save_published_state(state)
        print(f"\n💾 已更新发布记录，本次发布 {len(final_result)} 个产品")
    
    return success
