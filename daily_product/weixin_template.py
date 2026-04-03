"""微信 HTML 模板配置 - 定义微信文章的结构和样式."""

from __future__ import annotations

# ================= 资源链接 =================
HEADER_IMG = "https://mmbiz.qpic.cn/mmbiz_gif/xm1dT1jCe8lIO3P2oFVtd1x040PKGCRPN033gUTrHQQz0Licdqug5X1QgUPQBRCicoTqdYMrpgk7etibXLkK9rwcg/0?wx_fmt=gif&from=appmsg"
FOOTER_IMG = "https://mmbiz.qpic.cn/mmbiz_png/qHfXxy1pes10fIch7kKDnTcV7tJMdWticbFaZx6aXXLjxHFsQWCWr3TyiaVY11COWfF8yJnIQiasxfWKQ4dYAAvyFYZET5bT9PXJnuKzjVjEgM/640?wx_fmt=png"

# ================= 模板组件 =================

# 页面头部
HEADER_TEMPLATE = """<section style="margin: 0 0 15px 0; text-align: center;"><img src="{header_img}" style="width: 100%; display: block; border-radius: 8px;"></section>"""

# 新闻卡片模板（含图片）
CARD_WITH_IMAGE_TEMPLATE = """<section style="margin: 0 0 35px 0; background-color: #ffffff; border-radius: 12px; box-shadow: 0 12px 28px rgba(0, 82, 217, 0.08); border-top: 5px solid #0052d9; box-sizing: border-box;"><section style="padding: 24px 20px 20px 20px;"><section style="display: flex; align-items: center; margin-bottom: 12px;"><section style="background-color: #0052d9; color: #ffffff; font-family: 'Helvetica Neue', Arial, sans-serif; font-size: 11px; font-weight: bold; padding: 2px 8px; border-radius: 3px; letter-spacing: 1px; flex-shrink: 0; line-height: 1.2;">CORE {idx}</section><section style="margin-left: 12px; flex: 1; height: 1px; background-color: rgba(0, 82, 217, 0.15);"></section></section><section style="font-size: 21px; font-weight: 900; color: #1a1a1a; line-height: 1.5; text-align: justify; letter-spacing: 0.5px;">{title}</section></section><section style="width: 100%; margin: 0; padding: 0; line-height: 0; background-color: #ffffff;">{image_html}</section><section style="padding: 24px 20px 30px 20px;"><section style="font-size: 15px; color: #3f3f3f; line-height: 1.85; text-align: justify; letter-spacing: 0.8px; font-family: system-ui, -apple-system, sans-serif;">{content}</section><section style="margin-top: 28px; display: flex; align-items: center; justify-content: space-between;"><section style="display: flex; align-items: center;"><section style="width: 5px; height: 5px; background-color: #0052d9; margin-right: 5px; border-radius: 1px;"></section><section style="width: 5px; height: 5px; background-color: #0052d9; opacity: 0.5; margin-right: 5px; border-radius: 1px;"></section><section style="width: 5px; height: 5px; background-color: #0052d9; opacity: 0.2; border-radius: 1px;"></section></section><section style="font-size: 11px; color: #0052d9; font-weight: 700; opacity: 0.85; letter-spacing: 1.5px; font-family: Consolas, 'Courier New', monospace;">SYS.ACTIVE</section></section></section></section>"""

# 新闻卡片模板（无图片）
CARD_WITHOUT_IMAGE_TEMPLATE = """<section style="margin: 0 0 35px 0; background-color: #ffffff; border-radius: 12px; box-shadow: 0 12px 28px rgba(0, 82, 217, 0.08); border-top: 5px solid #0052d9; box-sizing: border-box;"><section style="padding: 24px 20px 20px 20px;"><section style="display: flex; align-items: center; margin-bottom: 12px;"><section style="background-color: #0052d9; color: #ffffff; font-family: 'Helvetica Neue', Arial, sans-serif; font-size: 11px; font-weight: bold; padding: 2px 8px; border-radius: 3px; letter-spacing: 1px; flex-shrink: 0; line-height: 1.2;">CORE {idx}</section><section style="margin-left: 12px; flex: 1; height: 1px; background-color: rgba(0, 82, 217, 0.15);"></section></section><section style="font-size: 21px; font-weight: 900; color: #1a1a1a; line-height: 1.5; text-align: justify; letter-spacing: 0.5px;">{title}</section></section><section style="padding: 0 20px 30px 20px;"><section style="font-size: 15px; color: #3f3f3f; line-height: 1.85; text-align: justify; letter-spacing: 0.8px; font-family: system-ui, -apple-system, sans-serif;">{content}</section><section style="margin-top: 28px; display: flex; align-items: center; justify-content: space-between;"><section style="display: flex; align-items: center;"><section style="width: 5px; height: 5px; background-color: #0052d9; margin-right: 5px; border-radius: 1px;"></section><section style="width: 5px; height: 5px; background-color: #0052d9; opacity: 0.5; margin-right: 5px; border-radius: 1px;"></section><section style="width: 5px; height: 5px; background-color: #0052d9; opacity: 0.2; border-radius: 1px;"></section></section><section style="font-size: 11px; color: #0052d9; font-weight: 700; opacity: 0.85; letter-spacing: 1.5px; font-family: Consolas, 'Courier New', monospace;">SYS.ACTIVE</section></section></section></section>"""

# 图片模板 - URL 格式
IMAGE_URL_TEMPLATE = """<img src="{image_src}" style="width: 100%; display: block; height: auto; border: none; object-fit: cover;" />"""

# 图片模板 - Base64 格式
IMAGE_BASE64_TEMPLATE = """<img src="data:image/jpeg;base64,{image_data}" style="width: 100%; display: block; height: auto; border: none; object-fit: cover;" />"""

# 页面底部
FOOTER_TEMPLATE = """<section style="margin: 20px 0 0 0; text-align: center;"><img src="{footer_img}" style="width: 100%; display: block; height: auto;"></section>"""
