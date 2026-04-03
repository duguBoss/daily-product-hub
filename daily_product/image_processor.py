"""图片处理模块 - 下载、格式转换和压缩."""

from __future__ import annotations

import hashlib
import io
import os
from pathlib import Path
from typing import Any

import requests

from .config import REQUEST_TIMEOUT


MAX_FILE_SIZE = 5 * 1024 * 1024


def download_image(url: str) -> bytes | None:
    """下载图片.
    
    Args:
        url: 图片 URL
        
    Returns:
        图片二进制数据，失败返回 None
    """
    try:
        resp = requests.get(url, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        return resp.content
    except Exception as e:
        print(f"   ⚠️ 图片下载失败: {url}, 错误: {e}")
        return None


def generate_filename(url: str) -> str:
    """根据 URL 生成唯一的文件名.
    
    Args:
        url: 图片 URL
        
    Returns:
        MD5 哈希作为文件名
    """
    return hashlib.md5(url.encode()).hexdigest()


def resize_image_to_max_size(
    image_data: bytes,
    max_size_bytes: int = MAX_FILE_SIZE,
    min_quality: int = 30,
) -> bytes:
    """调整图片大小以满足最大文件大小限制.
    
    使用 PIL 将图片转为 JPG 并逐步降低质量直到满足大小要求。
    
    Args:
        image_data: 原始图片数据
        max_size_bytes: 最大文件大小（字节）
        min_quality: 最低质量参数
        
    Returns:
        调整后的图片数据
    """
    try:
        from PIL import Image
        
        img = Image.open(io.BytesIO(image_data))
        
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
        
        quality = 95
        output = io.BytesIO()
        
        while quality >= min_quality:
            output.seek(0)
            output.truncate()
            img.save(output, format="JPEG", quality=quality)
            
            size = output.tell()
            if size <= max_size_bytes:
                return output.getvalue()
            
            quality -= 10
        
        return output.getvalue()
        
    except ImportError:
        print("   ⚠️ PIL 未安装，无法处理图片格式转换和压缩")
        return image_data
    except Exception as e:
        print(f"   ⚠️ 图片处理失败: {e}")
        return image_data


def process_image(url: str) -> dict[str, Any] | None:
    """处理单张图片：下载、转换格式、压缩.
    
    Args:
        url: 图片 URL
        
    Returns:
        处理结果，包含处理后的数据（base64）和原始 URL，失败返回 None
    """
    import base64
    
    if not url:
        return None
    
    print(f"   📷 正在处理图片: {url}")
    
    image_data = download_image(url)
    if not image_data:
        return None
    
    original_size = len(image_data)
    print(f"     原始大小: {original_size / 1024:.1f} KB")
    
    processed_data = resize_image_to_max_size(image_data)
    
    processed_size = len(processed_data)
    print(f"     处理后大小: {processed_size / 1024:.1f} KB")
    
    if processed_size > original_size:
        processed_data = image_data
        processed_size = original_size
        print(f"     (使用原始数据)")
    else:
        ratio = (1 - processed_size / original_size) * 100 if original_size > 0 else 0
        print(f"     压缩比: {ratio:.1f}%")
    
    base64_data = base64.b64encode(processed_data).decode("utf-8")
    
    return {
        "url": url,
        "data": base64_data,
        "original_size": original_size,
        "processed_size": processed_size,
    }


def process_images(urls: list[str]) -> list[dict[str, Any]]:
    """批量处理图片.
    
    Args:
        urls: 图片 URL 列表
        
    Returns:
        处理后的图片数据列表
    """
    results = []
    
    for url in urls:
        if not url:
            continue
        
        result = process_image(url)
        if result:
            results.append(result)
    
    return results
