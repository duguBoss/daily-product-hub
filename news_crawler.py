import os
import time
import json
import re
import requests
from openai import OpenAI

# 配置项
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
# 默认选用 OpenRouter 免费列表中性能较好且支持长文本的模型
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
    """使用 jina.ai 读取网页内容(返回 Markdown)"""
    print(f"正在通过 Jina 读取: {url}")
    try:
        response = requests.get(f"https://r.jina.ai/{url}", timeout=30)
        response.raise_for_status()
        return response.text
    except Exception as e:
        print(f"读取失败 {url}: {e}")
        return ""

def clean_json_string(text):
    """清理 AI 返回的内容，确保能被解析为 JSON"""
    match = re.search(r'```(?:json)?\s*(.*?)\s*```', text, re.DOTALL)
    if match:
        text = match.group(1)
    return text.strip()

def process_long_text_with_ai(system_prompt, full_text, final_prompt, chunk_size=4000):
    """
    【核心逻辑：多轮投喂解决截断问题】
    将长文本分块，多轮发送给AI，确保AI完整接收上下文后再进行任务处理
    """
    # 简单的按字符分块
    chunks = [full_text[i:i + chunk_size] for i in range(0, len(full_text), chunk_size)]
    total_chunks = len(chunks)
    
    messages = [{"role": "system", "content": system_prompt}]
    
    for i, chunk in enumerate(chunks):
        if i < total_chunks - 1:
            # 投喂中间内容，只让 AI 回复"收到"
            msg = f"【内容片段 {i+1}/{total_chunks}】\n{chunk}\n\n[指令]：这是部分内容，请不要进行任何分析，只回复“收到”二字。"
            messages.append({"role": "user", "content": msg})
            print(f"  -> 发送片段 {i+1}/{total_chunks}...")
            
            try:
                resp = client.chat.completions.create(model=AI_MODEL, messages=messages)
                ai_reply = resp.choices[0].message.content
                messages.append({"role": "assistant", "content": ai_reply})
            except Exception as e:
                print(f"  -> 片段投喂失败: {e}")
            time.sleep(1) # 避免触发免费API限流
        else:
            # 最后一段内容，加上最终分析指令
            msg = f"【内容片段 {i+1}/{total_chunks}】\n{chunk}\n\n[最终指令]：所有内容已发送完毕。{final_prompt}"
            messages.append({"role": "user", "content": msg})
            print(f"  -> 发送最后片段并请求分析...")
            
            try:
                resp = client.chat.completions.create(model=AI_MODEL, messages=messages)
                return resp.choices[0].message.content
            except Exception as e:
                print(f"  -> 最终分析失败: {e}")
                return "{}"

def get_hot_news_links(all_markdown):
    """从主页内容中提取当天热点科技产品资讯链接"""
    system_prompt = "你是一个科技资讯编辑，负责从海量文本中提取有价值的硬件科技产品新闻。"
    final_prompt = """
    请从以上你收到的所有内容中，提炼出当日最热门的【5个科技产品（各种硬件设备产品相关）资讯】。
    要求：
    1. 必须是硬件设备产品相关的资讯（手机、电脑、芯片、数码等）。
    2. 找出其对应的标题和原文链接。如果是相对路径，请尽量拼接为完整的http链接。
    3. 严格返回 JSON 数组格式，不要有任何多余文字说明。
    格式示例：
    [
      {"title": "iPhone 16 Pro 渲染图曝光", "url": "https://www.xxx.com/xxx.html"},
      ...
    ]
    """
    ai_response = process_long_text_with_ai(system_prompt, all_markdown, final_prompt, chunk_size=8000)
    
    try:
        json_str = clean_json_string(ai_response)
        news_list = json.loads(json_str)
        return news_list[:5] # 确保只返回5条
    except Exception as e:
        print(f"解析新闻列表JSON失败: {e}\nAI返回内容: {ai_response}")
        return []

def get_article_details(markdown_text):
    """提取单篇文章的摘要内容和配图"""
    system_prompt = "你是一个内容摘要提取助手。"
    final_prompt = """
    请阅读这篇完整的文章内容，完成以下任务：
    1. 提炼出这篇资讯的核心详细内容（字数在200-500字之间，保留关键数据和重点）。
    2. 提取文章中具有代表性的配图链接（通常在 Markdown 中以 `![描述](图片链接)` 的形式存在，提取其中的链接即可）。
    3. 严格按照以下 JSON 对象格式返回，不要有任何多余文字：
    {
      "content": "这里是提取的核心内容...",
      "images": ["url1", "url2"]
    }
    """
    ai_response = process_long_text_with_ai(system_prompt, markdown_text, final_prompt, chunk_size=8000)
    
    try:
        json_str = clean_json_string(ai_response)
        return json.loads(json_str)
    except Exception as e:
        print(f"解析文章详情JSON失败: {e}\nAI返回内容: {ai_response}")
        return {"content": "内容提取失败", "images": []}

def main():
    if not OPENROUTER_API_KEY:
        raise ValueError("请设置 OPENROUTER_API_KEY 环境变量！")

    print("=== 第一阶段：抓取主页并提取热点新闻 ===")
    combined_home_markdown = ""
    for site in SOURCES:
        md = fetch_jina_content(site)
        combined_home_markdown += f"\n\n来源网站: {site}\n" + md

    if not combined_home_markdown.strip():
        print("未获取到任何主页内容，程序退出。")
        return

    hot_news = get_hot_news_links(combined_home_markdown)
    print(f"成功提取到 {len(hot_news)} 条热点新闻链接。")

    print("\n=== 第二阶段：进入详情页抓取内容及配图 ===")
    final_results = []
    
    for item in hot_news:
        title = item.get("title", "无标题")
        url = item.get("url", "")
        if not url:
            continue
            
        print(f"\n处理: {title} ({url})")
        article_md = fetch_jina_content(url)
        
        if not article_md:
            continue
            
        details = get_article_details(article_md)
        
        final_results.append({
            "资讯标题": title,
            "内容": details.get("content", ""),
            "配图": details.get("images", [])
        })
        time.sleep(2) # 防并发封控

    print("\n=== 第三阶段：保存结果 ===")
    output_file = "daily_tech_news.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(final_results, f, ensure_ascii=False, indent=4)
    print(f"执行完毕！结果已保存至 {output_file}")
    
    # 打印最终效果
    print(json.dumps(final_results, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
