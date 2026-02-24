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

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
)

def fetch_jina_content(url):
    """使用 jina.ai 读取网页内容"""
    print(f"  -> 正在抓取: {url}")
    headers = {"X-Return-Format": "markdown"} # 明确要求返回 markdown
    try:
        response = requests.get(f"https://r.jina.ai/{url}", headers=headers, timeout=60)
        response.raise_for_status()
        return response.text
    except Exception as e:
        print(f"  -> [错误] 抓取失败 {url}: {e}")
        return ""

def clean_json_string(text):
    """加强版 JSON 清理函数：过滤所有多余文字"""
    if not text:
        return ""
    text = text.strip()
    
    # 尝试匹配 Markdown 里的 JSON 块
    match = re.search(r'```(?:json)?\s*(.*?)\s*```', text, re.DOTALL | re.IGNORECASE)
    if match:
        text = match.group(1).strip()
    
    # 强制截取第一层 [] 或 {}
    start_array = text.find('[')
    start_object = text.find('{')
    
    if start_array != -1 and (start_object == -1 or start_array < start_object):
        end_array = text.rfind(']')
        if end_array != -1:
            return text[start_array:end_array+1]
            
    if start_object != -1 and (start_array == -1 or start_object < start_array):
        end_object = text.rfind('}')
        if end_object != -1:
            return text[start_object:end_object+1]
            
    return text

def process_long_text_with_ai(system_prompt, full_text, final_prompt, chunk_size=6000):
    """多轮投喂解决截断问题"""
    if not full_text.strip():
        return ""

    chunks = [full_text[i:i + chunk_size] for i in range(0, len(full_text), chunk_size)]
    total_chunks = len(chunks)
    messages = [{"role": "system", "content": system_prompt}]
    
    for i, chunk in enumerate(chunks):
        if i < total_chunks - 1:
            msg = f"【内容片段 {i+1}/{total_chunks}】\n{chunk}\n\n[指令]：这是部分内容，只需回复“收到”，不要做任何总结或提取。"
            messages.append({"role": "user", "content": msg})
            try:
                resp = client.chat.completions.create(model=AI_MODEL, messages=messages)
                ai_reply = resp.choices[0].message.content
                messages.append({"role": "assistant", "content": "收到"}) # 强制替换回复节省上下文
            except Exception as e:
                print(f"  -> [错误] 片段投喂失败: {e}")
            time.sleep(1)
        else:
            msg = f"【内容片段 {i+1}/{total_chunks}】\n{chunk}\n\n[最终指令]：所有内容发送完毕！\n{final_prompt}"
            messages.append({"role": "user", "content": msg})
            try:
                resp = client.chat.completions.create(model=AI_MODEL, messages=messages)
                return resp.choices[0].message.content
            except Exception as e:
                print(f"  -> [错误] 最终分析失败: {e}")
                return ""
    return ""

def get_hot_news_links(all_markdown):
    """提取热点链接并修复相对路径"""
    system_prompt = "你是一个科技资讯编辑，负责提取有价值的硬件科技产品新闻。不要输出任何除了 JSON 之外的字符。"
    final_prompt = """
    请从之前的所有内容中，提取当日最热门的【5个科技产品（如手机、电脑、数码硬件等）资讯】。
    严格返回 JSON 数组格式！不要返回任何额外解释！
    格式：
    [
      {"title": "新闻标题", "url": "对应的原文链接(如果是相对路径请尽量完整)"}
    ]
    """
    
    print("\n提交AI进行热点提取...")
    ai_response = process_long_text_with_ai(system_prompt, all_markdown, final_prompt, chunk_size=8000)
    
    try:
        json_str = clean_json_string(ai_response)
        news_list = json.loads(json_str)
        
        # 补全相对路径链接
        valid_news = []
        for item in news_list:
            url = item.get("url", "")
            title = item.get("title", "无标题")
            
            # 过滤掉无法访问的假链接
            if "..." in url or not url:
                continue
                
            # 处理相对路径问题 (自动补全域名)
            if url.startswith("/"):
                # 简单推断一下来源站点
                base = "https://www.mydrivers.com" if "mydrivers" in all_markdown else "https://www.ithome.com"
                url = urljoin(base, url)
            
            if url.startswith("http"):
                valid_news.append({"title": title, "url": url})
                
        return valid_news[:5]
    except Exception as e:
        print(f"[错误] 提取新闻列表JSON解析失败: {e}")
        print(f"AI 原始返回内容:\n{ai_response}")
        return []

def get_article_details(markdown_text):
    """提取详情与图片"""
    system_prompt = "你是一个内容提取助手，严格输出 JSON 格式。"
    final_prompt = """
    提取核心详细内容和配图链接。
    严格返回 JSON 格式：
    {
      "content": "这里是提取的资讯核心内容（200字以上）...",
      "images": ["图片url1", "图片url2"]
    }
    """
    ai_response = process_long_text_with_ai(system_prompt, markdown_text, final_prompt, chunk_size=8000)
    
    try:
        json_str = clean_json_string(ai_response)
        return json.loads(json_str)
    except Exception as e:
        print(f"[错误] 详情页JSON解析失败: {e}")
        return {"content": "内容提取失败", "images": []}

def main():
    if not OPENROUTER_API_KEY:
        raise ValueError("缺少 OPENROUTER_API_KEY 环境变量！")

    print("=== 1. 抓取主页数据 ===")
    combined_home_markdown = ""
    for site in SOURCES:
        md = fetch_jina_content(site)
        if md:
            combined_home_markdown += f"\n\n来源网站: {site}\n" + md

    if not combined_home_markdown.strip():
        print("所有网站主页均抓取失败，退出程序。")
        return

    print("=== 2. AI 提取热点新闻 ===")
    hot_news = get_hot_news_links(combined_home_markdown)
    if not hot_news:
        print("未提取到任何新闻，请检查上方日志看是否 AI 报错。")
        return
        
    print(f"成功获取 {len(hot_news)} 条新闻：")
    for n in hot_news:
         print(f" - {n['title']} [{n['url']}]")

    print("\n=== 3. 进入详情页分析内容 ===")
    final_results = []
    
    for item in hot_news:
        print(f"\n-> 处理: {item['title']}")
        article_md = fetch_jina_content(item['url'])
        
        if not article_md:
            print("   (页面获取为空，跳过)")
            continue
            
        details = get_article_details(article_md)
        
        final_results.append({
            "资讯标题": item["title"],
            "链接": item["url"],
            "内容": details.get("content", ""),
            "配图": details.get("images", [])
        })
        time.sleep(2)

    print("\n=== 4. 生成最终数据文件 ===")
    output_file = "daily_tech_news.json"
    
    # 就算结果不完整也保存，避免文件丢失
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(final_results, f, ensure_ascii=False, indent=4)
        
    print(f"保存成功！共 {len(final_results)} 条记录写入 {output_file}")
    print(json.dumps(final_results, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
