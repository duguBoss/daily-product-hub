import os
import time
import json
import re
import requests
from urllib.parse import urljoin
from openai import OpenAI

# === 配置 ===
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
# 备用模型列表，如果第一个失败尝试第二个 (免费模型不稳定)
AI_MODELS = [
    "stepfun/step-3.5-flash:free",
    "z-ai/glm-4.5-air:free"
]
SOURCES = [
    "https://www.ithome.com",
    "https://www.mydrivers.com"
]
OUTPUT_DIR = "data"
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "daily_tech_news.json")

# 初始化客户端
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
)

def ensure_dir():
    """确保 data 目录存在"""
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
        print(f"创建目录: {OUTPUT_DIR}")

def save_json_file(data):
    """保存到 data/daily_tech_news.json"""
    ensure_dir()
    try:
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        print(f"✅ 文件已保存至: {OUTPUT_FILE}")
    except Exception as e:
        print(f"❌ 保存文件失败: {e}")

def fetch_jina_content(url):
    """抓取网页，增加重试和验证"""
    print(f"🌐 正在请求 Jina 读取: {url}")
    headers = {
        "X-Return-Format": "markdown",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    for _ in range(2): # 重试2次
        try:
            resp = requests.get(f"https://r.jina.ai/{url}", headers=headers, timeout=30)
            if resp.status_code == 200:
                text = resp.text
                if len(text) < 200:
                    print(f"⚠️ 警告: 内容过短 ({len(text)} 字符)，可能是被反爬拦截验证码。")
                    return ""
                return text
        except Exception as e:
            print(f"   请求出错: {e}")
            time.sleep(2)
    return ""

def clean_json_string(text):
    """深度清洗 JSON 字符串"""
    if not text: return ""
    text = text.strip()
    # 移除 Markdown 代码块
    match = re.search(r'```(?:json)?\s*(.*?)\s*```', text, re.DOTALL | re.IGNORECASE)
    if match: text = match.group(1).strip()
    
    # 寻找最外层的 [] 或 {}
    s1, s2 = text.find('['), text.find('{')
    start = -1
    if s1 != -1 and s2 != -1: start = min(s1, s2)
    elif s1 != -1: start = s1
    elif s2 != -1: start = s2
    
    if start != -1:
        # 简单截取，假设最后是对应的结束符
        text = text[start:]
        e1, e2 = text.rfind(']'), text.rfind('}')
        end = -1
        if e1 != -1 and e2 != -1: end = max(e1, e2)
        elif e1 != -1: end = e1
        elif e2 != -1: end = e2
        if end != -1:
            text = text[:end+1]
            
    return text

def call_ai_with_retry(messages):
    """尝试调用 AI，失败则切换模型"""
    for model in AI_MODELS:
        try:
            # print(f"🤖 正在调用模型: {model}")
            resp = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0.3 # 降低随机性
            )
            content = resp.choices[0].message.content
            if content:
                return content
        except Exception as e:
            print(f"⚠️ 模型 {model} 调用失败: {e}")
            time.sleep(1)
    return ""

def get_hot_news_links(all_markdown):
    """提取热点新闻链接"""
    print("🧠 正在分析热点新闻...")
    
    # 为了防止 Gemini 免费版过载，这里不使用多轮对话，直接截取 Markdown 的前 15000 字符
    # 免费版处理超长上下文非常慢且容易超时，15000字符通常包含了当天所有重要新闻标题
    shortened_md = all_markdown[:15000]
    
    prompt = f"""
    基于以下科技新闻网站的内容，提取今日最热门的5条【硬件/数码产品】新闻。
    
    内容来源：
    {shortened_md}
    
    要求：
    1. 必须是硬件产品（手机、显卡、芯片、电脑等）。
    2. 返回标准 JSON 数组，无 Markdown 标记。
    3. 格式：[{{"title": "标题", "url": "链接"}}]
    4. 如果链接是相对路径，请保留原样。
    """
    
    messages = [{"role": "user", "content": prompt}]
    resp = call_ai_with_retry(messages)
    
    try:
        json_str = clean_json_string(resp)
        data = json.loads(json_str)
        
        # 修正链接
        valid_data = []
        for item in data:
            u = item.get("url", "")
            if not u: continue
            if u.startswith("/"):
                # 简单补全
                base = "https://www.ithome.com" if "ithome" in u or "html" in u else "https://www.mydrivers.com"
                u = urljoin(base, u)
            valid_data.append({"title": item["title"], "url": u})
        return valid_data[:5]
    except Exception as e:
        print(f"❌ 解析热点列表失败: {e}")
        print(f"AI 原文: {resp}")
        return []

def get_article_details(title, url):
    """提取单篇详情"""
    print(f"  -> 分析详情: {title}")
    md = fetch_jina_content(url)
    if not md: return None
    
    # 截取详情页前 8000 字符防止 tokens 溢出
    md_short = md[:8000]
    
    prompt = f"""
    阅读文章：{md_short}
    
    任务：
    1. 总结核心内容（200-400字）。
    2. 提取文中第一张相关产品图片的链接（以http开头）。
    
    返回 JSON：
    {{"content": "总结内容...", "images": ["图片链接"]}}
    """
    
    resp = call_ai_with_retry([{"role": "user", "content": prompt}])
    try:
        json_str = clean_json_string(resp)
        return json.loads(json_str)
    except:
        return {"content": "提取失败", "images": []}

def main():
    # 1. 预先创建空文件，防止 Workflow 报错
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
        print(f"   站点 {site} 获取长度: {len(text)} 字符")
        if len(text) > 500:
            full_content += f"\n来源 {site}:\n{text}\n"
    
    if not full_content:
        print("❌ 所有站点抓取内容均为空，可能是 IP 被封锁。")
        return

    # 3. 提取列表
    news_list = get_hot_news_links(full_content)
    print(f"✅ 提取到 {len(news_list)} 条新闻")

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
        time.sleep(2) # 避免速率限制

    # 5. 保存结果
    if final_result:
        save_json_file(final_result)
        print(json.dumps(final_result, ensure_ascii=False, indent=2))
    else:
        print("⚠️ 最终结果为空，未进行保存覆盖。")

if __name__ == "__main__":
    main()
