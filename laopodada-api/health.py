"""Health articles module - v10 with database persistence.

POST /api/v1/health/articles/generate — AI generates health article, saves to DB
GET  /api/v1/health/articles — List articles with pagination
GET  /api/v1/health/articles/<id> — Get single article

Health categories: nutrition, exercise, disease, mental, female, prevention
"""
import json
import logging
import time
import uuid

from flask import Blueprint, jsonify, request

import db
import atlas_client


bp = Blueprint("health_v10", __name__, url_prefix="/api/v1/health")
log = logging.getLogger(__name__)

# Valid categories for health articles
HEALTH_CATEGORIES = {"nutrition", "exercise", "disease", "mental", "female", "prevention"}

# Source whitelist for AI-generated content (must contain one of these)
SOURCE_WHITELIST = [
    "WHO", "中国居民膳食指南", "中国国家卫健委", "中国营养学会",
    "ACOG", "Lancet", "NEJM", "JAMA", "CDC", "中国疾控"
]

# Forbidden words that indicate low-quality or misleading content
FORBIDDEN_WORDS = ["绝对", "100%有效", "包治", "神药", "立竿见影"]

# System prompt for health article generation
HEALTH_GENERATION_SYSTEM = """你是一个专业的健康科普作家。根据用户输入的话题，写一篇300-800字的健康科普文章。

要求：
1. 只输出真实、有科学依据的内容
2. 必须引用权威来源（WHO、中国居民膳食指南、中国国家卫健委、中国营养学会、ACOG、Lancet、NEJM、JAMA、CDC、中国疾控之一）
3. 不要编造具体数据，如需引用请注明"研究表明"
4. 语言通俗易懂，适合普通读者
5. 内容要积极正面，提供可行的健康建议
6. 绝对禁止使用绝对化用语（绝对、100%有效、包治、神药、立竿见影等）

返回JSON格式：
{
    "title": "文章标题",
    "category": "分类(nutrition/exercise/disease/mental/female/prevention之一)",
    "summary": "80-150字摘要",
    "content": "Markdown格式正文，300-800字",
    "tags": ["标签1", "标签2"],
    "source": "权威来源名称",
    "read_minutes": 预估阅读分钟数(数字)
}"""


def _validate_article_gen(article: dict) -> str | None:
    """Validate generated article content. Returns error message or None if valid."""
    if not article:
        return "解析失败：内容为空"
    if not article.get("title"):
        return "缺少标题"
    if not article.get("content"):
        return "缺少正文"
    if not article.get("source"):
        return "缺少来源"
    # Check source is in whitelist
    source = article["source"]
    if not any(w in source for w in SOURCE_WHITELIST):
        return f"来源不权威：{source}，必须包含 {SOURCE_WHITELIST} 之一"
    # Check no forbidden words
    content_lower = (article.get("content") or "") + (article.get("summary") or "")
    for word in FORBIDDEN_WORDS:
        if word in content_lower:
            return f"内容含禁用词：{word}"
    # Check reasonable length
    content = article.get("content", "")
    if len(content) < 100:
        return "正文太短（<100字）"
    if len(content) > 10000:
        return "正文太长（>10000字）"
    return None


@bp.post("/articles/generate")
def generate_article():
    """AI generates a health article and saves to database."""
    body = request.get_json(silent=True) or {}
    topic = (body.get("topic") or "").strip()
    if not topic:
        return jsonify({"error": "topic 必填"}), 400
    if len(topic) > 100:
        return jsonify({"error": "topic 太长 (<=100字)"}), 400

    category = body.get("category", "")
    if category and category not in HEALTH_CATEGORIES:
        return jsonify({"error": f"category 必须是: {', '.join(HEALTH_CATEGORIES)}"}), 400

    # Build prompt
    prompt = f"请撰写一篇关于「{topic}」的健康科普文章。"
    if category:
        prompt += f"（分类：{category}）"

    last_err = None
    last_reply = ""
    for attempt in range(2):  # Max 1 retry
        try:
            reply = atlas_client.call(prompt, timeout=90)
        except TimeoutError as e:
            log.error(f"atlas timeout for health article: {e}")
            return jsonify({"error": "AI 思考超时,请重试"}), 504
        except Exception as e:
            log.error(f"atlas error for health article: {e}")
            return jsonify({"error": f"AI 服务异常: {str(e)[:100]}"}), 500

        last_reply = reply

        # Extract JSON from reply
        article = _extract_json(reply)
        if not article:
            last_err = "无法从回复中提取 JSON"
            continue

        # Override category if specified
        if category:
            article["category"] = category

        # Validate
        err = _validate_article_gen(article)
        if err:
            last_err = err
            log.warning(f"[health] validate failed (attempt {attempt+1}): {err}")
            continue

        # Save to database
        article_id = db.insert_health_article({
            "id": uuid.uuid4().hex[:16],
            "title": article.get("title", topic),
            "category": article.get("category", "nutrition"),
            "summary": article.get("summary", ""),
            "content": article.get("content", ""),
            "tags": article.get("tags", []),
            "read_minutes": int(article.get("read_minutes", 3)),
            "source": article.get("source", ""),
            "created_at": int(time.time()),
        })

        log.info(f"[health] article generated: {article_id}")
        return jsonify({
            "article": {
                "id": article_id,
                "title": article.get("title"),
                "category": article.get("category"),
                "summary": article.get("summary"),
                "content": article.get("content"),
                "tags": article.get("tags", []),
                "read_minutes": article.get("read_minutes"),
                "source": article.get("source"),
                "created_at": int(time.time()),
            }
        }), 201

    return jsonify({
        "error": f"AI 生成失败 (2次重试): {last_err}",
        "reply_excerpt": last_reply[:200]
    }), 422


@bp.get("/articles")
def list_articles():
    """List health articles with pagination."""
    category = request.args.get("category", "").strip()
    limit = min(int(request.args.get("limit", 20)), 100)
    offset = int(request.args.get("offset", 0))

    if category and category not in HEALTH_CATEGORIES:
        return jsonify({"error": f"category 必须是: {', '.join(HEALTH_CATEGORIES)}"}), 400

    try:
        articles, total = db.get_health_articles(category=category, limit=limit, offset=offset)
        return jsonify({
            "count": total,
            "articles": articles,
            "limit": limit,
            "offset": offset,
        })
    except Exception as e:
        log.error(f"[health] list failed: {e}")
        return jsonify({"error": str(e)}), 500


@bp.get("/articles/<article_id>")
def get_article(article_id: str):
    """Get a single health article by ID."""
    try:
        article = db.get_health_article_by_id(article_id)
        if not article:
            return jsonify({"error": "文章不存在"}), 404
        return jsonify({"article": article})
    except Exception as e:
        log.error(f"[health] get failed: {e}")
        return jsonify({"error": str(e)}), 500


def _extract_json(reply: str) -> dict | None:
    """Extract first valid JSON object from LLM reply."""
    import re
    # 1. Try markdown ```json ... ``` fence
    fence_re = r"```json\s*(\{[\s\S]*?\})\s*```"
    m = re.search(fence_re, reply)
    if m:
        try:
            return json.loads(m.group(1))
        except json.JSONDecodeError:
            pass

    # 2. Try each { ... } block, balance-aware
    s = 0
    while True:
        s = reply.find("{", s)
        if s < 0:
            return None
        depth = 0
        in_str = False
        escape = False
        for i in range(s, len(reply)):
            c = reply[i]
            if escape:
                escape = False
                continue
            if c == "\\":
                escape = True
                continue
            if c == '"':
                in_str = not in_str
                continue
            if in_str:
                continue
            if c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(reply[s:i + 1])
                    except json.JSONDecodeError:
                        break
        s += 1
    return None

