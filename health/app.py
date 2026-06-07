#!/usr/bin/env python3
"""健康知识模块 - 偏口鱼博士风格 Flask 应用"""
import os, json, time
from flask import Flask, render_template, request, jsonify
from knowledge_db import (
    KNOWLEDGE_DB, KEY_QUOTES, DIET_FORMULA,
    search, get_by_category, get_all_categories, answer_question
)

app = Flask(__name__, static_folder="static", template_folder="templates")
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# FinnA LLM config (same as notebook-app)
FINNA_KEY = os.environ.get("FINNA_KEY", "app-ULzJbc3OaIN50mZVSU7sAa97")
FINNA_BASE = "https://www.finna.com.cn/v1"
LLM_MODEL = "deepseek-v4-flash"


def call_llm(messages, max_tokens=1024):
    import requests
    for attempt in range(3):
        try:
            resp = requests.post(
                f"{FINNA_BASE}/chat/completions",
                headers={"Authorization": f"Bearer {FINNA_KEY}", "Content-Type": "application/json"},
                json={"model": LLM_MODEL, "messages": messages, "temperature": 0.3,
                      "max_tokens": max_tokens, "stream": False,
                      "extra_body": {"enable_thinking": False}},
                timeout=60
            )
            data = resp.json()
            if "choices" in data:
                return data["choices"][0]["message"]["content"]
        except Exception as e:
            print(f"LLM attempt {attempt+1} failed: {e}")
            time.sleep(2)
    return None


@app.route("/")
def index():
    cats = get_all_categories()
    return render_template("index.html", cats=cats, db=KNOWLEDGE_DB,
                          quotes=KEY_QUOTES, formula=DIET_FORMULA)


@app.route("/api/ask", methods=["POST"])
def ask():
    data = request.get_json()
    query = data.get("query", "").strip()
    if not query:
        return jsonify({"error": "问题不能为空"}), 400

    #1. 先在知识库检索
    result = answer_question(query)

    # 2. 用 LLM 整合回答（带知识库上下文）
    prompt = f"""你是一位循证医学科普助手，用通俗易懂的语言回答健康问题。
基于以下知识库内容回答。如果知识库没有直接答案，给出一般性建议并注明。

## 知识库
{result['answer']}

## 偏口鱼博士金句
{chr(10).join(KEY_QUOTES[:3])}

## 饮食公式
{DIET_FORMULA}

## 用户问题
{query}

回答要求：
- 简洁、有据可查
- 明确说明推荐还是不推荐
- 用「偏口鱼博士观点：」开头引用知识库内容
- 最后给出一句可操作的下一步建议
- 字数控制在200字以内
- 用中文"""

    messages = [{"role": "user", "content": prompt}]
    answer = call_llm(messages)

    return jsonify({
        "answer": answer or result['answer'],
        "sources": result['sources'],
        "tips": result['tips'],
        "formula": DIET_FORMULA
    })


@app.route("/api/category/<cat_name>")
def category(cat_name):
    items = get_by_category(cat_name)
    return jsonify({"items": items, "category": cat_name})


@app.route("/api/random-tip")
def random_tip():
    import random
    tip = random.choice(KEY_QUOTES)
    return jsonify({"tip": tip})


@app.route("/api/search", methods=["POST"])
def api_search():
    data = request.get_json()
    query = data.get("q", "")
    results = search(query, top_k=10)
    return jsonify({"results": results})


@app.route("/health-check")
def health_check():
    cats = get_all_categories()
    return jsonify({"status": "ok", "categories": len(cats), "entries": len(KNOWLEDGE_DB)})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8096, debug=False)