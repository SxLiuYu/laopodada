"""AI outfit recommendation endpoint (v10).

POST /api/v1/outfits/generate — Atlas LLM picks 1 outfit from user's wardrobe.
Response shape: {"outfit": {"items": [{id,category,url,color}], "description": str, "tips": str}}
Error codes: 422 (empty wardrobe or bad LLM JSON), 504 (atlas timeout), 500 (other atlas errors)
"""
import json
import logging
import re
import time

from flask import Blueprint, jsonify, request

import db
import atlas_client


bp = Blueprint("outfits_v10", __name__, url_prefix="/api/v1/outfits")
log = logging.getLogger(__name__)

# 1h in-memory cache
_CACHE: dict[str, tuple[float, dict]] = {}
_CACHE_TTL = 3600


@bp.post("/generate")
def generate_outfit():
    """AI generates one outfit from user's wardrobe items."""
    body = request.get_json(silent=True) or {}
    occasion = (body.get("occasion") or "casual").strip() or "casual"
    weather = body.get("weather")

    # 1. Fetch items from DB
    items = db.get_all_items()
    if not items:
        return jsonify({"error": "衣橱为空,请先添加衣物"}), 422

    # 2. Cache check
    cache_key = f"outfit:{occasion}:{weather}:{len(items)}"
    cached = _CACHE.get(cache_key)
    if cached is not None and (time.time() - cached[0]) < _CACHE_TTL:
        return jsonify(cached[1]), 200

    # 3. Build prompt (cap items at 20 to stay within LLM context)
    items_summary = [
        {"id": it["id"], "category": it["category"], "color": it.get("color", "")}
        for it in items[:20]
    ]
    prompt = (
        f"根据以下衣橱单品,推荐 1 套适合 {occasion} 场合的穿搭。\n"
        f"返回纯 JSON: {{\"items\": [item_id 数组, 2-3 件], "
        f"\"description\": \"搭配描述 50-100 字,中文\", "
        f"\"tips\": \"穿搭小贴士 30-50 字\"}}\n"
        f"衣橱: {json.dumps(items_summary, ensure_ascii=False)}"
    )

    # 4. Call atlas LLM
    try:
        atlas_reply = atlas_client.call(prompt, timeout=90)
    except TimeoutError as e:
        log.error(f"atlas timeout: {e}")
        return jsonify({"error": "AI 思考超时,请重试"}), 504
    except Exception as e:
        log.error(f"atlas error: {e}")
        return jsonify({"error": f"AI 服务异常: {str(e)[:100]}"}), 500

    # 5. Parse JSON from LLM reply
    outfit = _parse_outfit_json(atlas_reply)
    if not outfit or "items" not in outfit or "description" not in outfit:
        return jsonify({"error": "AI 回复格式错误,请换个主题重试"}), 422

    # 6. Enrich with image URLs (id + category + url)
    id_to_item = {it["id"]: it for it in items}
    enriched_items = []
    for item_id in outfit["items"]:
        if item_id in id_to_item:
            it = id_to_item[item_id]
            enriched_items.append({
                "id":       it["id"],
                "category": it["category"],
                "url":      it.get("thumbnail_url") or it.get("original_url"),
                "color":    it.get("color", ""),
            })

    if not enriched_items:
        return jsonify({"error": "AI 推荐的单品不在衣橱中,请重试"}), 422

    response = {
        "outfit": {
            "items":       enriched_items,
            "description": outfit["description"],
            "tips":        outfit.get("tips", ""),
        }
    }

    # 7. Cache
    _CACHE[cache_key] = (time.time(), response)

    return jsonify(response), 200


def _parse_outfit_json(reply: str):
    """Extract first JSON object from LLM reply. Handles ```json ... ``` fence + raw JSON."""
    if not reply:
        return None
    # Code fence first
    m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", reply, re.S)
    if m:
        try:
            return json.loads(m.group(1))
        except json.JSONDecodeError:
            pass
    # Raw JSON: find first { to last }
    m = re.search(r"\{.*\}", reply, re.S)
    if m:
        try:
            return json.loads(m.group(0))
        except json.JSONDecodeError:
            pass
    return None
