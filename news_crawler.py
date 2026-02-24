import os
import time
import json
import re
import requests
import datetime
from urllib.parse import urljoin
from openai import OpenAI

# ================= 全局配置 =================
# 1. 统一使用的 AI 模型
AI_MODEL = "stepfun/step-3.5-flash:free" 

# 2. 目标数据源
SOURCES = [
    "https://www.ithome.com",
    "https://www.mydrivers.com"
]

# 3. 输出文件路径 (每次运行都会覆盖此文件)
OUTPUT_DIR = "data"
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "daily_tech_news.json")

# ===========================================

OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
)

def get_beijing_date():
    """获取北京时间今天的日期字符串 (YYYY-MM-DD)"""
    utc_now = datetime.datetime.utcnow()
    beijing_now = utc_now + datetime.timedelta(hours=8)
    return beijing_now.strftime("%Y-%m-%d")

def ensure_dir():
    """确保输出目录存在"""
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

def save_json_file(data):
    """
    保存数据到文件。
    使用 'w' 模式，这意味着每次写入都会清空旧内容，只保存最新一次的结果。
    """
    ensure_dir()
    try:
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        print(f"✅ 数据已覆盖保存至: {OUTPUT_FILE}")
    except Exception as e:
        print(f"❌ 保存文件失败: {e}")

def fetch_jina_content(url):
    """
    使用 Jina 读取网页，伪装成浏览器以避免 GitHub Actions IP 被封
    """
    print(f"🌐 正在请求 Jina 读取: {url}")
    jina_url = f"https://r.jina.ai/{url}"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Referer": "https://www.google.com/",
        "X-Return-Format": "markdown"
    }

    for attempt in range(3):
        try:
            # 设置较长的超时时间
            resp = requests.get(jina_url, headers=headers, timeout=40)
            
            if resp.status_code == 429:
                print("   ⚠️ 触发速率限制，等待 10 秒...")
                time.sleep(10)
                continue
            
            if resp.status_code != 200:
                print(f"   ❌ HTTP 错误 {resp.status_code}")
                continue

            text = resp.text
            # 简单的有效性检查
            if len(text) < 200:
                print(f"   ⚠️ 内容过短 ({len(text)} 字符)，可能是空页面或验证码。")
                continue
                
            return text
        except Exception as e:
            print(f"   ❌ 请求异常 (第 {attempt+1} 次): {e}")
            time.sleep(5)
            
    return ""

def clean_json_string(text):
    """清洗 AI 返回的 JSON 字符串"""
    if not text: return ""
    text = text.strip()
    match = re.search(r'```(?:json)?\s*(.*?)\s*```', text, re.DOTALL | re.IGNORECASE)
    if match: text = match.group(1).strip()
    return text

def get_latest_hot_news(all_markdown):
    """
    使用 AI 提取【当日】热点新闻
    """
    today_date = get_beijing_date()
    print(f"🧠 正在请求 AI ({AI_MODEL}) 提取 {today_date} 的新闻...")
    
    # 截取前 20000 字符，step-3.5-flash 处理长文本能力尚可
    context = all_markdown[:20000]
    
    prompt = f"""
    今天是北京时间：{today_date}。
    
    请分析以下网页内容，严格筛选出【今天 ({today_date})】发布的、最热门的 5 条【硬件科技产品】新闻（手机、电脑、芯片、数码等）。
    
    如果不确定日期，请优先选择列表中最靠前的新闻。
    
    请严格返回 JSON 数组格式，不要包含任何 markdown 标记或额外文字：
    [
        {{"title": "新闻标题", "url": "链接地址"}}
    ]
    
    内容来源：
    {context}
    """
    
    try:
        resp = client.chat.completions.create(
            model=AI_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1 # 低温度保证准确性
        )
        content = resp.choices[0].message.content
        cleaned_content = clean_json_string(content)
        
        try:
            data = json.loads(cleaned_content)
        except json.JSONDecodeError:
            # 尝试修复常见的 JSON 错误（如未闭合）
            if cleaned_content.strip().startswith("[") and not cleaned_content.strip().endswith("]"):
                 cleaned_content += "]"
                 data = json.loads(cleaned_content)
            else:
                print(f"❌ JSON 解析失败，AI 返回: {content}")
                return []

        # 链接补全与清洗
        valid_data = []
        for item in data:
            u = item.get("url", "")
            t = item.get("title", "")
            if not u: continue
            
            # 自动补全相对路径
            if u.startswith("/"):
                # 简单判断来源
                if "ithome" in all_markdown and "mydrivers" not in u:
                    u = urljoin("https://www.ithome.com", u)
                else:
                    u = urljoin("https://www.mydrivers.com", u)
            
            valid_data.append({"title": t, "url": u})
            
        return valid_data[:8] # 只取前5条
        
    except Exception as e:
        print(f"❌ AI 提取列表报错: {e}")
        return []

def get_article_details(title, url):
    """提取单篇新闻详情"""
    print(f"  -> 分析详情: {title}")
    
    # 强制休眠，防止并发请求导致 Jina 封锁
    time.sleep(3)
    
    md = fetch_jina_content(url)
    if not md:
        print("     (跳过：未获取到详情页内容)")
        return None
    
    prompt = f"""
    请阅读这篇科技新闻，提取核心内容总结（300字以内）和第一张产品图片的链接。
    
    文章内容：
    {md[:10000]}
    
    请严格返回 JSON 格式：
    {{
        "content": "这里是总结...",
        "images": ["图片URL"]
    }}
    """
    
    try:
        resp = client.chat.completions.create(
            model=AI_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1
        )
        return json.loads(clean_json_string(resp.choices[0].message.content))
    except Exception as e:
        print(f"     (详情提取失败: {e})")
        return {"content": "内容提取失败", "images": []}

def main():
    # 1. 启动时的兜底措施
    if not OPENROUTER_API_KEY:
        print("❌ 致命错误: 未配置 OPENROUTER_API_KEY")
        return

    # 2. 抓取所有来源的主页
    full_home_content = ""
    for site in SOURCES:
        text = fetch_jina_content(site)
        print(f"   [{site}] 获取长度: {len(text)}")
        if len(text) > 500:
            full_home_content += f"\n=== 来源: {site} ===\n{text}\n"
        time.sleep(2)

    if not full_home_content:
        print("❌ 所有来源抓取失败，无法进行后续分析。")
        # 生成一个空的 JSON 文件以避免 Action 报错，同时也清空了旧数据
        save_json_file([]) 
        return

    # 3. 提取今日热点
    news_list = get_latest_hot_news(full_home_content)
    print(f"✅ 提取到 {len(news_list)} 条今日新闻")

    if not news_list:
        print("⚠️ 未提取到有效新闻，可能是因为今天还没有更新或 AI 解析失败。")
        save_json_file([])
        return

    # 4. 循环提取详情
    final_result = []
    for news in news_list:
        details = get_article_details(news["title"], news["url"])
        if details:
            final_result.append({
                "资讯标题": news["title"],
                "内容": details.get("content", ""),
                "配图": details.get("images", [])
            })
    
    # 5. 保存结果（覆盖旧数据）
    if final_result:
        save_json_file(final_result)
        # 打印结果供日志检查
        print(json.dumps(final_result, ensure_ascii=False, indent=2))
    else:
        print("⚠️ 详情分析全部失败，保存空数组。")
        save_json_file([])

if __name__ == "__main__":
    main()
