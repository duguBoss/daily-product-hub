"""Daily Product Hub - 硬件科技新闻爬虫入口.

重构后的模块化版本，将功能拆分为独立的子模块：
- config: 全局配置
- common: 通用工具函数
- ai_client: AI 客户端
- fetching: 网页内容获取
- processor: 数据处理
- main_flow: 主执行流程
"""

from __future__ import annotations

from daily_product.main_flow import run_pipeline


def main() -> None:
    """程序入口."""
    try:
        success = run_pipeline()
        if not success:
            print("⚠️ 流程未能成功完成，保留原有数据。")
    except Exception as e:
        print(f"💥 脚本发生未捕获异常退出: {e}")
        print("⚠️ 终止更新，保留原有数据。")


if __name__ == "__main__":
    main()
