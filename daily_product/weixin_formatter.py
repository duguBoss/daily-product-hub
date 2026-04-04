"""微信发文格式生成模块 - 生成微信编辑器可用的 HTML 和 JSON."""

from __future__ import annotations

import html
import json
import re
from datetime import datetime
from typing import Any

from .weixin_template import (
    CARD_WITH_IMAGE_TEMPLATE,
    CARD_WITHOUT_IMAGE_TEMPLATE,
    FOOTER_IMG,
    FOOTER_TEMPLATE,
    HEADER_IMG,
    HEADER_TEMPLATE,
    IMAGE_BASE64_TEMPLATE,
    IMAGE_URL_TEMPLATE,
)


def compact_text(text: str) -> str:
    """清理文本中的多余空白."""
    return re.sub(r"\s+", " ", text).strip()


def format_content(content: str) -> str:
    """格式化正文内容，处理换行和段落间距.
    
    Args:
        content: 原始内容文本
        
    Returns:
        格式化后的 HTML 内容
    """
    # 转义 HTML 特殊字符
    escaped = html.escape(content, quote=True)
    # 将换行符转换为 14px 段落间距
    return escaped.replace("\n", '<section style="height:14px;"></section>')


def build_image_html(images: list[Any]) -> str:
    """构建图片 HTML.
    
    Args:
        images: 图片列表，每项是包含 github_url 的字典
        
    Returns:
        图片 HTML 字符串
    """
    if not images:
        return ""
    
    first_image = images[0]
    
    # 优先使用 github_url
    if isinstance(first_image, dict):
        if "github_url" in first_image:
            return IMAGE_URL_TEMPLATE.format(image_src=html.escape(first_image["github_url"], quote=True))
        elif "data" in first_image:
            return IMAGE_BASE64_TEMPLATE.format(image_data=first_image["data"])
        elif "url" in first_image:
            return IMAGE_URL_TEMPLATE.format(image_src=html.escape(first_image["url"], quote=True))
    elif isinstance(first_image, str):
        return IMAGE_URL_TEMPLATE.format(image_src=html.escape(first_image, quote=True))
    
    return ""


def build_weixin_html(items: list[dict[str, Any]]) -> str:
    """构建微信文章 HTML - 科技终端卡片风格.
    
    Args:
        items: 新闻列表，每项包含 资讯标题、内容、配图
        
    Returns:
        微信编辑器可用的 HTML 字符串
    """
    if not items:
        return ""
    
    html_parts = []
    
    # 1. 顶部引导部分
    html_parts.append(HEADER_TEMPLATE.format(header_img=HEADER_IMG))
    
    # 2. 循环生成新闻模块
    for i, item in enumerate(items):
        idx = str(i + 1).zfill(2)
        title = compact_text(item.get("资讯标题", ""))
        content = format_content(item.get("内容", ""))
        images = item.get("配图", [])
        
        if not title or not content:
            continue
        
        # 构建图片 HTML
        image_html = build_image_html(images)
        
        # 根据是否有图片选择不同模板
        if image_html:
            card = CARD_WITH_IMAGE_TEMPLATE.format(
                idx=idx,
                title=title,
                image_html=image_html,
                content=content,
            )
        else:
            card = CARD_WITHOUT_IMAGE_TEMPLATE.format(
                idx=idx,
                title=title,
                content=content,
            )
        html_parts.append(card)
    
    # 3. 页面底部收尾图片
    html_parts.append(FOOTER_TEMPLATE.format(footer_img=FOOTER_IMG))
    
    # 4. 拼接并压缩代码
    full_html = "".join(html_parts)
    full_html = full_html.replace("\n", "").replace("    ", "")
    
    return full_html


def build_weixin_json(items: list[dict[str, Any]]) -> dict[str, Any]:
    """构建微信发文用的 JSON 数据.
    
    Args:
        items: 新闻列表
        
    Returns:
        包含微信 HTML、标题、封面图等信息的字典
    """
    if not items:
        return {}
    
    html_content = build_weixin_html(items)
    
    # 提取标题列表
    titles = [compact_text(item.get("资讯标题", "")) for item in items if item.get("资讯标题")]
    
    # 提取封面图（收集所有新闻的第一张图片的 GitHub URL）
    covers = []
    for item in items:
        images = item.get("配图", [])
        if images and len(images) > 0:
            first_image = images[0]
            # 优先使用 github_url
            if isinstance(first_image, dict):
                if "github_url" in first_image:
                    covers.append(first_image["github_url"])
                elif "url" in first_image:
                    covers.append(first_image["url"])
            elif isinstance(first_image, str):
                covers.append(first_image)
    
    # 生成最吸引人的总标题（使用第一条新闻的标题）
    main_title = titles[0] if titles else "今日科技新品推荐"
    
    # 构建微信 JSON 格式
    weixin_data = {
        "wexinhtml": html_content,
        "count": len(titles),
        "generated_at": datetime.now().isoformat(),
        "key1": main_title,  # 最吸引人的总标题
    }
    
    # 添加封面图列表
    if covers:
        weixin_data["covers"] = covers
    
    return weixin_data


def save_weixin_json(items: list[dict[str, Any]], output_path: str) -> bool:
    """保存微信发文 JSON 到文件.
    
    Args:
        items: 新闻列表
        output_path: 输出文件路径
        
    Returns:
        是否保存成功
    """
    try:
        weixin_data = build_weixin_json(items)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(weixin_data, f, ensure_ascii=False, indent=2)
        print(f"✅ 微信发文 JSON 已保存至: {output_path}")
        return True
    except Exception as e:
        print(f"❌ 保存微信 JSON 失败: {e}")
        return False
