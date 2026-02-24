import os
import time
import json
import re
import requests
from urllib.parse import urljoin
from openai import OpenAI

OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
AI_MODEL = "google/gemini-2.5-flash:free" 
SOURCES = [
    "https://www.ithome.com",
    "https://www.mydrivers.com"
]

# 兜底文件保存函数
def save_json_file(data, filename="daily_tech_news.json"):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def fetch_jina_content(url):
    """使用 jina.ai 读取网页内容，增加浏览器伪装"""
    print(f"  -> 正在抓取: {url}")
    headers = {
        "X-Return-Format": "markdown",
        # 增加 User-Agent 伪装，防止被目标网站拦截
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    }
    try:
        response = requests.get(f"https://r.jina.ai/{url}", headers=headers, timeout=60)
        response.raise_for_status()
        return response.text
    except Exception as e:
        print(f"  -> [抓取失败] {url}: {e}")
        return ""

def clean_json_string(text):
    """提取 JSON 字符串"""
    if not text: return ""
    text = text.strip()
    match = re.search(r'```(?:json)?\s*(.*?)\s*```', text, re.DOTALL | re.IGNORECASE)
    if match: text = match.group(1).strip()
    
    start_array, start_object = text.find('['), text.find('{')
    if start_array != -1 and (start_object == -1 or start_array < start_object):
        end_array = text.rfind(']')
        if end_array != -1: return text[start_array:end_array+1]
    if start_object != -1 and (start_array == -1 or start_object < start_array):
        end_object = text.rfind('}')
        if end_object != -1: return text[start_object:end_object+1]
    return text

def process_long_text_with_ai(client, system_prompt, full_text, final_prompt, chunk_size=6000):
    if not full_text.strip(): return ""
    chunks = [full_text[i:i + chunk_size] for i in range(0, len(full_text), chunk_size)]
    total_chunks = len(chunks)
    messages = [{"role": "system", "content": system_prompt}]
    
    for i, chunk in enumerate(chunks):
        if i < total_chunks - 1:
            msg = f"【片段 {i+1}/{total_chunks}】\n{chunk}\n\n[指令]：这是部分内容，只需回复“收到”，不要做任何总结。"
            messages.append({"role": "user", "content": msg})
            try:
                client.chat.completions.create(model=AI_MODEL, messages=messages)
                messages.append({"role": "assistant", "content": "收到"}) 
            except Exception as e:
                print(f"  -> [AI片段投喂报错]: {e}")
            time.sleep(1)
        else:
            msg = f"【片段 {i+1}/{total_chunks}】\n{chunk}\n\n[最终指令]：所有内容完毕！\n{final_prompt}"
            messages.append({"role": "user", "content": msg})
            try:
                resp = client.chat.completions.create(model=AI_MODEL, messages=messages)
                return resp.choices[0].message.content
            except Exception as e:
                print(f"  -> [AI最终分析报错]: {e}")
                return ""
    return ""

def get_hot_news_links(client, all_markdown):
    system_prompt = "你是一个科技资讯编辑，负责提取有价值的硬件科技新闻。不要输出除了 JSON 之外的字符。"
    final_prompt = """
    请从之前的所有内容中，提取当日最热门的【5个科技硬件产品（如手机、电脑、芯片等）资讯】。
    严格返回 JSON 数组格式！
    格式：[{"title": "新闻标题", "url": "对应的原文链接(如果是相对路径请尽量完整)"}]
    """
    print("\n提交AI进行热点提取...")
    ai_response = process_long_text_with_ai(client, system_prompt, all_markdown, final_prompt, chunk_size=8000)
    
    try:
        json_str = clean_json_string(ai_response)
        news_list = json.loads(json_str)
        valid_news = []
        for item in news_list:
            url = item.get("url", "")
            title = item.get("title", "无标题")
            if "..." in url or not url: continue
            if url.startswith("/"):
                base = "https://www.mydrivers.com" if "mydrivers" in all_markdown else "https://www.ithome.com"
                url = urljoin(base, url)
            if url.startswith("http"):
                valid_news.append({"title": title, "url": url})
        return valid_news[:5]
    except Exception as e:
        print(f"[错误] 新闻列表JSON解析失败: {e}\nAI返回内容:\n{ai_response}")
        return []

def get_article_details(client, markdown_text):
    system_prompt = "你是一个内容提取助手，严格输出 JSON 格式。"
    final_prompt = """
    提取核心详细内容和配图链接。严格返回 JSON 格式：
    {"content": "这里是提取的核心内容(200字以上)...", "images": ["图片url1", "图片url2"]}
    """
    ai_response = process_long_text_with_ai(client, system_prompt, markdown_text, final_prompt, chunk_size=8000)
    try:
        json_str = clean_json_string(ai_response)
        return json.loads(json_str)
    except Exception as e:
        print(f"[错误] 详情解析失败: {e}")
        return {"content": "内容提取失败", "images": []}

def main():
    # 兜底机制：脚本一开始就先生成一个空的 JSON 文件，确保后续 GitHub Actions 传文件时不报错
    save_json_file([])

    if not OPENROUTER_API_KEY:
        print("【致命错误】缺少 OPENROUTER_API_KEY 环境变量！请检查 GitHub Secrets 配置。")
        return

    client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=OPENROUTER_API_KEY)

    print("=== 1. 抓取主页数据 ===")
    combined_home_markdown = ""
    for site in SOURCES:
        md = fetch_jina_content(site)
        if md: combined_home_markdown += f"\n\n来源网站: {site}\n" + md

    if not combined_home_markdown.strip():
        print("【失败结束】所有网站主页均抓取失败或为空，程序退出。")
        return

    print("=== 2. AI 提取热点新闻 ===")
    hot_news = get_hot_news_links(client, combined_home_markdown)
    if not hot_news:
        print("【失败结束】AI未能提取到任何有效新闻格式，程序退出。")
        return
        
    print(f"成功获取 {len(hot_news)} 条新闻。")

    print("\n=== 3. 进入详情页分析 ===")
    final_results = []
    for item in hot_news:
        print(f"\n-> 处理: {item['title']}")
        article_md = fetch_jina_content(item['url'])
        if not article_md:
            print("   (页面获取为空，跳过)")
            continue
            
        details = get_article_details(client, article_md)
        final_results.append({
            "资讯标题": item["title"],
            "链接": item["url"],
            "内容": details.get("content", ""),
            "配图": details.get("images", [])
        })
        time.sleep(2)

    print("\n=== 4. 生成最终数据文件 ===")
    save_json_file(final_results)
    print(f"执行成功！共 {len(final_results)} 条记录已保存。")

if __name__ == "__main__":
    main()
