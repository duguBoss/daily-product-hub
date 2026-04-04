"""图片处理模块 - 下载、格式转换和压缩."""

from __future__ import annotations

import hashlib
import io
import os
from pathlib import Path
from typing import Any

import requests

from .config import (
    GITHUB_BRANCH,
    GITHUB_REPO,
    IMAGES_DIR,
    REQUEST_TIMEOUT,
)


MAX_FILE_SIZE = 5 * 1024 * 1024
MAX_IMAGE_HEIGHT = 600  # 最大图片高度（像素），超过则裁剪


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


def limit_image_height(
    image_data: bytes,
    max_height: int = MAX_IMAGE_HEIGHT,
) -> bytes:
    """限制图片高度，超过则裁剪.

    从顶部开始裁剪，保留图片的上半部分（通常产品主体在上方）。

    Args:
        image_data: 原始图片数据
        max_height: 最大高度（像素）

    Returns:
        处理后的图片数据
    """
    try:
        from PIL import Image

        img = Image.open(io.BytesIO(image_data))
        width, height = img.size

        # 如果高度未超过限制，直接返回原图
        if height <= max_height:
            return image_data

        print(f"     图片高度 {height}px 超过限制 {max_height}px，进行裁剪")

        # 从顶部裁剪，保留上半部分
        crop_box = (0, 0, width, max_height)
        img_cropped = img.crop(crop_box)

        # 保存为 JPEG
        output = io.BytesIO()
        if img_cropped.mode in ("RGBA", "P"):
            img_cropped = img_cropped.convert("RGB")
        img_cropped.save(output, format="JPEG", quality=95)

        return output.getvalue()

    except ImportError:
        print("   ⚠️ PIL 未安装，无法裁剪图片")
        return image_data
    except Exception as e:
        print(f"   ⚠️ 图片裁剪失败: {e}")
        return image_data


def convert_to_jpg(image_data: bytes) -> bytes:
    """将任何格式的图片转换为 JPG 格式.

    Args:
        image_data: 原始图片二进制数据

    Returns:
        JPG 格式的图片数据
    """
    try:
        from PIL import Image

        img = Image.open(io.BytesIO(image_data))

        # 转换为 RGB 模式（处理 RGBA、P 等模式）
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")

        # 保存为 JPG
        output = io.BytesIO()
        img.save(output, format="JPEG", quality=95)
        return output.getvalue()

    except ImportError:
        print("   ⚠️ PIL 未安装，无法转换图片格式，使用原始数据")
        return image_data
    except Exception as e:
        print(f"   ⚠️ 图片格式转换失败: {e}，使用原始数据")
        return image_data


def save_image_to_file(image_data: bytes, filename: str) -> Path | None:
    """保存图片到本地文件（确保为 JPG 格式）.

    Args:
        image_data: 图片二进制数据（会被转换为 JPG）
        filename: 文件名

    Returns:
        保存的文件路径，失败返回 None
    """
    try:
        # 确保目录存在
        IMAGES_DIR.mkdir(parents=True, exist_ok=True)

        # 确保图片为 JPG 格式
        jpg_data = convert_to_jpg(image_data)

        # 保存图片
        file_path = IMAGES_DIR / f"{filename}.jpg"
        with open(file_path, "wb") as f:
            f.write(jpg_data)

        return file_path
    except Exception as e:
        print(f"   ⚠️ 保存图片失败: {e}")
        return None


def get_github_raw_url(filename: str) -> str:
    """生成 GitHub raw 链接.

    Args:
        filename: 文件名（不含扩展名）

    Returns:
        GitHub raw 链接
    """
    return f"https://raw.githubusercontent.com/{GITHUB_REPO}/{GITHUB_BRANCH}/data/images/{filename}.jpg"


def process_image(url: str) -> dict[str, Any] | None:
    """处理单张图片：下载、限制高度、转换格式、压缩、保存到本地.

    Args:
        url: 图片 URL

    Returns:
        处理结果，包含 GitHub URL、本地路径和原始 URL，失败返回 None
    """
    if not url:
        return None

    print(f"   📷 正在处理图片: {url}")

    image_data = download_image(url)
    if not image_data:
        return None

    original_size = len(image_data)
    print(f"     原始大小: {original_size / 1024:.1f} KB")

    # 第一步：限制高度
    image_data = limit_image_height(image_data, MAX_IMAGE_HEIGHT)

    # 第二步：压缩文件大小
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

    # 生成文件名并保存到本地
    filename = generate_filename(url)
    file_path = save_image_to_file(processed_data, filename)

    if not file_path:
        return None

    # 生成 GitHub raw URL
    github_url = get_github_raw_url(filename)
    print(f"     已保存到: {file_path}")
    print(f"     GitHub URL: {github_url}")

    return {
        "url": url,
        "github_url": github_url,
        "local_path": str(file_path),
        "filename": filename,
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
