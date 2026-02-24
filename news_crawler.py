import os
import time
import json
import re
import requests
from urllib.parse import urljoin
from openai import OpenAI

# === 配置 ===
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
SOURCES = [
    "https://www.ithome.com",
    "https://www.mydrivers.com"
]
# 确保数据保存到 data 目录
OUTPUT_DIR = "data"
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "daily_tech_news.json")

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
)

def ensure_dir():
    """确保 data 目录存在"""
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
        print(f"📁 创建目录: {OUTPUT_DIR}")

def save_json_file(data):
    """保存 JSON 到 data/daily_tech_news.json"""
    ensure_dir()
    try:
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        print(f"✅ 文件已成功保存至: {OUTPUT_FILE}")
    except Exception as e:
        print(f"❌ 保存文件失败: {e}")

def fetch_jina_content(url):
    """
    使用 Jina 读取网页，不使用 API Key，但极力伪装成浏览器
    """
    print(f"🌐 正在请求 Jina 读取: {url}")
    
    # 构造 Jina URL
    jina_url = f"https://r.jina.ai/{url}"
    
    # 伪装成真实的 Chrome 浏览器，防止被识别为 GitHub 机器人
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Referer": "https://www.google.com/",
        "X-Return-Format": "markdown"
    }

    # 重试机制
    for attempt in range(3):
        try:
            # 增加 timeout 防止卡死
            response = requests.get(jina_url, headers=headers, timeout=30)
            
            # 如果是 429 (Too Many Requests) 或 403，说明 IP 被限制
            if response.status_code in [429, 403]:
                print(f"   ⚠️ IP 可能被限制 (HTTP {response.status_code})，等待 10 秒后重试...")
                time.sleep(10)
                continue
                
            response.raise_for_status()
            text = response.text
            
            # 检查是否返回了 Jina 的报错页面（有时候状态码是 200 但内容是报错）
            if "Usage Limit" in text or "Rate Limit" in text:
                print("   ❌ 触发了 Jina 的匿名使用限制。")
                return ""
                
            if len(text) < 200:
                print(f"   ⚠️ 内容过短 ({len(text)} 字符)，可能是空页面。")
                print(f"   📄 内容预览: {text[:100]}") # 打印出来看看到底返回了啥
                return ""
                
            return text
            
        except Exception as e:
            print(f"   ❌ 请求出错 (尝试 {attempt+1}/3): {e}")
            time.sleep(5)
            
    return ""

def clean_json_string(text):
    """强力清洗 JSON"""
    if not text: return ""
    text = text.strip()
    match = re.search(r'```(?:json)?\s*(.*?)\s*```', text, re.DOTALL | re.IGNORECASE)
    if match: text = match.group(1).strip()
    
    # 寻找最外层的 [] 或 {}
    s_arr = text.find('[')
    s_obj = text.find('{')
    start = -1
    
    if s_arr != -1 and s_obj != -1: start = min(s_arr, s_obj)
    elif s_arr != -1: start = s_arr
    elif s_obj != -1: start = s_obj
    
    if start != -1:
        text = text[start:]
        e_arr = text.rfind(']')
        e_obj = text.rfind('}')
        end = max(e_arr, e_obj)
        if end != -1:
            return text[:end+1]
    return text

def get_hot_news_links(all_markdown):
    """提取热点新闻链接"""
    print("🧠 正在分析热点新闻 (Gemini-Flash Free)...")
    
    # 截取前 15000 字符，通常足够包含首页列表
    shortened_md = all_markdown[:15000]
    
    prompt = f"""
    基于以下内容，提取今日最热门的 5 条【硬件/数码产品】新闻。
    
    内容：
    {shortened_md}
    
    要求：
    1. 必须是硬件（手机、电脑、芯片等）。
    2. 返回 JSON 数组：[{{"title": "标题", "url": "链接"}}]
    3. 如果链接是相对路径，保留原样，不要自己编造域名。
    """
    
    try:
        resp = client.chat.completions.create(
            model="stepfun/step-3.5-flash:free",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1
        )
        content = resp.choices[0].message.content
        
        try:
            data = json.loads(clean_json_string(content))
        except:
            print(f"❌ JSON 解析失败，AI 返回: {content}")
            return []

        # 链接补全逻辑
        valid_data = []
        for item in data:
            u = item.get("url", "")
            title = item.get("title", "")
            if not u: continue
            
            # 智能补全域名
            if u.startswith("/"):
                # 如果标题看起来像之家的，或者上下文主要来自之家
                if "ithome" in all_markdown and "mydrivers" not in u:
                     u = urljoin("https://www.ithome.com", u)
                else:
                     u = urljoin("https://www.mydrivers.com", u)
            
            valid_data.append({"title": title, "url": u})
            
        return valid_data[:5]
    except Exception as e:
        print(f"❌ AI 提取列表失败: {e}")
        return []

def get_article_details(title, url):
    """提取详情"""
    print(f"  -> 正在分析详情: {title}")
    
    # 强制休眠，避免 Jina 认为我们在 DDoS
    time.sleep(5) 
    
    md = fetch_jina_content(url)
    if not md: 
        print("     (获取内容失败，跳过)")
        return None
    
    prompt = f"""
    阅读文章：{md[:10000]}
    
    任务：
    1. 总结核心内容（200-400字）。
    2. 提取文中第一张产品图片的链接。
    
    返回 JSON：
    {{"content": "总结内容...", "images": ["图片链接"]}}
    """
    
    try:
        resp = client.chat.completions.create(
            model="google/gemini-2.5-flash:free",
            messages=[{"role": "user", "content": prompt}]
        )
        return json.loads(clean_json_string(resp.choices[0].message.content))
    except:
        return {"content": "提取失败", "images": []}

def main():
    # 1. 启动时先创建空文件，作为兜底
    ensure_dir()
    if not os.path.exists(OUTPUT_FILE):
        save_json_file([])

    if not OPENROUTER_API_KEY:
        print("❌ 错误: 未设置 OPENROUTER_API_KEY")
        return

    # 2. 抓取主页
    full_content = ""
    for site in SOURCES:
        text = fetch_jina_content(site)
        print(f"   [{site}] 获取长度: {len(text)}")
        if len(text) > 500:
            full_content += f"\n=== {site} ===\n{text}\n"
        
        # 每个站点之间休息 3 秒
        time.sleep(3) 

    if not full_content:
        print("❌ 所有站点内容均为空。请检查 GitHub Actions 日志中的 HTTP 状态码。")
        return

    # 3. 提取列表
    news_list = get_hot_news_links(full_content)
    print(f"✅ 提取到 {len(news_list)} 条新闻")

    # 4. 提取详情
    final_result = []
    for news in news_list:
        details = get_article_details(news["title"], news["url"])
        if details:
            final_result.append({
                "资讯标题": news["title"],
                "内容": details.get("content", ""),
                "配图": details.get("images", [])
            })

    # 5. 保存结果
    if final_result:
        save_json_file(final_result)
        print(json.dumps(final_result, ensure_ascii=False, indent=2))
    else:
        print("⚠️ 最终结果为空，未覆盖原文件。")

if __name__ == "__main__":
    main()
