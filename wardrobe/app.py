"""
电子衣橱 - Web 端应用 (AI 增强版)
- 规则候选生成 → FashionCLIP 视觉评分 → Qwen3 LLM 精排 + 推荐理由
- 模型懒加载；缺失时自动降级到纯规则模式
"""

import json
import logging
import os
import sys
import uuid
from datetime import datetime
from pathlib import Path

import numpy as np
import requests
from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request, send_from_directory

# 加载 .env（可选）
load_dotenv()

# 抑制 transformers / mlx 大量 INFO 日志
logging.basicConfig(level=logging.WARNING, format="%(asctime)s [%(name)s] %(message)s")
log = logging.getLogger("wardrobe")
log.setLevel(logging.INFO)

app = Flask(__name__)

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
UPLOAD_DIR = BASE_DIR / "static" / "uploads"
WARDROBE_FILE = DATA_DIR / "wardrobe.json"

DATA_DIR.mkdir(exist_ok=True)
UPLOAD_DIR.mkdir(exist_ok=True)

# ==================== AI 模块（懒加载） ====================

_embedder = None
_reasoner = None


def get_embedder():
    global _embedder
    if _embedder is None:
        from ai.fashion_embedder import FashionEmbedder
        _embedder = FashionEmbedder(data_dir=str(DATA_DIR))
        try:
            if _embedder.model_exists():
                _embedder.load()
                log.info("FashionCLIP 已就绪 (%d 件衣物有 embedding)", len(_embedder._id_to_idx))
        except Exception as e:
            log.warning("FashionCLIP 加载失败: %s (将跳过视觉打分)", e)
    return _embedder


def get_reasoner():
    global _reasoner
    if _reasoner is None:
        from ai.llm_rerank import OutfitReasoner
        _reasoner = OutfitReasoner()
        if _reasoner.is_available():
            try:
                _reasoner.load()
                if _reasoner.is_ready():
                    log.info("LLM 模型就绪 (backend=%s)", _reasoner.backend())
                else:
                    log.warning("LLM 未就绪: %s", _reasoner.disabled_reason())
            except Exception as e:
                log.warning("LLM 加载失败: %s (将退化为纯规则推荐)", e)
        else:
            log.info("LLM 模型目录不存在或为空, 跳过加载")
    return _reasoner


# ==================== 规则知识库 ====================

COLOR_PAIRS_GOOD = {
    "白色": ["黑色", "灰色", "蓝色", "卡其色", "粉色", "红色", "绿色", "棕色", "米色"],
    "黑色": ["白色", "灰色", "红色", "金色", "银色", "米色", "蓝色"],
    "灰色": ["白色", "黑色", "粉色", "蓝色", "紫色", "绿色"],
    "蓝色": ["白色", "灰色", "卡其色", "黑色", "米色", "棕色"],
    "卡其色": ["白色", "蓝色", "黑色", "棕色", "绿色", "米色"],
    "米色": ["白色", "黑色", "棕色", "蓝色", "灰色", "绿色"],
    "棕色": ["白色", "米色", "卡其色", "蓝色", "绿色"],
    "红色": ["黑色", "白色", "灰色", "蓝色"],
    "粉色": ["白色", "灰色", "黑色", "蓝色", "紫色"],
    "绿色": ["白色", "黑色", "卡其色", "米色", "棕色", "灰色"],
    "紫色": ["白色", "灰色", "黑色", "粉色"],
    "黄色": ["白色", "黑色", "灰色", "蓝色"],
    "橙色": ["白色", "黑色", "灰色", "蓝色"],
}

OCCASION_STYLES = {
    "正式": ["正式"],
    "商务": ["正式"],
    "面试": ["正式"],
    "会议": ["正式"],
    "休闲": ["休闲", "日常"],
    "日常": ["休闲", "日常", "约会"],
    "逛街": ["休闲", "日常"],
    "约会": ["约会", "休闲"],
    "聚会": ["约会", "休闲"],
    "运动": ["运动"],
    "户外": ["运动", "休闲"],
    "健身": ["运动"],
}


# ==================== 数据层 ====================

def load_wardrobe() -> list[dict]:
    if WARDROBE_FILE.exists():
        with open(WARDROBE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def save_wardrobe(items: list[dict]) -> None:
    with open(WARDROBE_FILE, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)


def get_warmth_from_temp(temp: float) -> list[str]:
    if temp < 5:
        return ["厚"]
    if temp < 15:
        return ["厚", "适中"]
    if temp < 23:
        return ["适中", "薄"]
    return ["薄"]


def color_match_score(c1: str, c2: str) -> int:
    if c1 == c2:
        return 1
    if c1 in COLOR_PAIRS_GOOD and c2 in COLOR_PAIRS_GOOD[c1]:
        return 3
    if c2 in COLOR_PAIRS_GOOD and c1 in COLOR_PAIRS_GOOD[c2]:
        return 3
    return 0


# ==================== 天气 ====================

def get_weather(city: str) -> dict:
    try:
        url = f"https://wttr.in/{city}?format=j1"
        resp = requests.get(url, timeout=8, headers={"User-Agent": "WardrobeApp/2.0"})
        data = resp.json()
        cur = data.get("current_condition", [{}])[0]
        temp = int(cur.get("temp_C", 20))
        desc = cur.get("weatherDesc", [{}])[0].get("value", "晴")
        desc_l = desc.lower()
        wt = "晴"
        for kw, label in [("rain", "雨"), ("drizzle", "雨"), ("shower", "雨"),
                          ("snow", "雪"), ("cloud", "阴"), ("overcast", "阴"),
                          ("mist", "雾"), ("fog", "雾"), ("霾", "雾")]:
            if kw in desc_l:
                wt = label
                break
        return {
            "city": city,
            "temp": temp,
            "feels_like": cur.get("FeelsLikeC", str(temp)),
            "desc": desc,
            "weather_type": wt,
            "humidity": cur.get("humidity", "50"),
            "wind": cur.get("windspeedKmph", "0"),
            "suggested_warmth": get_warmth_from_temp(temp),
        }
    except Exception as e:
        log.warning("天气接口失败: %s", e)
        return {
            "city": city, "temp": 20, "feels_like": "20", "desc": "未知",
            "weather_type": "晴", "humidity": "50", "wind": "0",
            "suggested_warmth": ["适中"], "error": str(e),
        }


# ==================== 候选生成 ====================

def _classify(wardrobe: list[dict], allowed_styles: list[str], warmth: list[str]) -> dict:
    """按风格+温度过滤后分类。"""
    cats: dict[str, list[dict]] = {k: [] for k in
        ["上衣", "下装", "连衣裙", "外套", "鞋子", "饰品"]}
    for it in wardrobe:
        if it.get("style", "日常") not in allowed_styles:
            continue
        if it.get("warmth", "适中") not in warmth:
            continue
        cat = it.get("category", "")
        if cat in cats:
            cats[cat].append(it)
    return cats


def _score_combo(items: list[dict]) -> float:
    """给一套搭配算规则分。颜色+3 / 同色+1 / 风格统一+3。"""
    score = 0
    colors = [it.get("color", "") for it in items]
    for i in range(len(colors)):
        for j in range(i + 1, len(colors)):
            score += color_match_score(colors[i], colors[j])
    styles = [it.get("style", "") for it in items]
    if len(set(styles)) == 1 and styles[0]:
        score += 3
    return float(score)


def _stable_id(items: list[dict]) -> str:
    return "|".join(sorted(it["id"] for it in items))


def generate_candidates(wardrobe: list[dict], occasion: str, weather_type: str,
                        cap: int = 24) -> list[dict]:
    """
    返回候选搭配列表 (>= cap 时按规则分排序截断)。
    每条: {id, items, rule_score}
    """
    allowed = OCCASION_STYLES.get(occasion, ["休闲", "日常"])
    warmth = get_warmth_from_temp(20)  # 实际温度在 /recommend 中再过滤

    # 注意: 温度过滤放到 generate_candidates 之外做
    pools = _classify(wardrobe, allowed, warmth)
    tops, bottoms, dresses, outers, shoes, accs = (pools[k] for k in
        ["上衣", "下装", "连衣裙", "外套", "鞋子", "饰品"])

    cands: dict[str, dict] = {}

    # 连衣裙路线
    for d in dresses[:8]:
        for s in shoes[:8]:
            base = [d, s]
            base_score = _score_combo(base)
            cands[_stable_id(base)] = {"items": base, "rule_score": base_score}
            for o in outers[:4]:
                c = [d, o, s]
                cands[_stable_id(c)] = {"items": c,
                                        "rule_score": _score_combo(c)}
            for a in accs[:3]:
                c = [d, s, a]
                cands[_stable_id(c)] = {"items": c,
                                        "rule_score": _score_combo(c)}

    # 上下装路线
    for t in tops[:8]:
        for b in bottoms[:8]:
            for s in shoes[:6]:
                base = [t, b, s]
                cands[_stable_id(base)] = {"items": base,
                                           "rule_score": _score_combo(base)}
                for o in outers[:3]:
                    c = [t, b, s, o]
                    cands[_stable_id(c)] = {"items": c,
                                            "rule_score": _score_combo(c)}
                for a in accs[:3]:
                    c = [t, b, s, a]
                    cands[_stable_id(c)] = {"items": c,
                                            "rule_score": _score_combo(c)}

    # 按规则分排序
    ranked = sorted(cands.values(), key=lambda c: c["rule_score"], reverse=True)
    # 分配稳定 id
    for i, c in enumerate(ranked):
        c["id"] = f"c{i:03d}"
    return ranked[:cap]


# ==================== AI 精排 ====================

# 视觉分权重（在总分中的相对重要度）
VISUAL_WEIGHT = 2.0


def ai_score_candidates(candidates: list[dict]) -> list[dict]:
    """
    给候选打视觉分，融合到 combined_score。
    无 embedding 或模型未加载时，visual_score=0。
    """
    emb = get_embedder()
    has_emb = emb is not None and emb.is_ready()

    for c in candidates:
        if has_emb:
            v, _ = emb.outfit_compatibility(c["items"])
            c["visual_score"] = float(v)
        else:
            c["visual_score"] = 0.0
        c["combined_score"] = c["rule_score"] + VISUAL_WEIGHT * c["visual_score"]

    candidates.sort(key=lambda x: x["combined_score"], reverse=True)
    return candidates


def ai_rerank(weather: dict, occasion: str, candidates: list[dict]) -> dict:
    """返回 {order: [cand_id...], reasons: {cand_id: str}, used_ai: bool}"""
    reasoner = get_reasoner()
    if reasoner is None or not reasoner.is_available():
        return {
            "order": [c["id"] for c in candidates],
            "reasons": {c["id"]: "基于规则与视觉兼容性排序" for c in candidates},
            "used_ai": False,
        }
    try:
        result = reasoner.rerank(weather, occasion, candidates)
        result["used_ai"] = True
        return result
    except Exception as e:
        log.exception("LLM 精排失败: %s", e)
        return {
            "order": [c["id"] for c in candidates],
            "reasons": {c["id"]: f"AI 精排失败: {type(e).__name__}" for c in candidates},
            "used_ai": False,
        }


# ==================== 路由 ====================

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/wardrobe", methods=["GET"])
def api_get_wardrobe():
    return jsonify(load_wardrobe())


@app.route("/api/wardrobe", methods=["POST"])
def api_add_item():
    name = request.form.get("name", "").strip()
    if not name:
        return jsonify({"error": "名称不能为空"}), 400
    category = request.form.get("category", "上衣")
    color = request.form.get("color", "白色")
    style = request.form.get("style", "休闲")
    warmth = request.form.get("warmth", "适中")
    season = request.form.get("season", "春夏")

    image_file = request.files.get("image")
    image_relpath = ""
    image_abs = ""
    if image_file and image_file.filename:
        ext = Path(image_file.filename).suffix or ".jpg"
        fname = f"{uuid.uuid4().hex}{ext}"
        image_abs = str(UPLOAD_DIR / fname)
        image_file.save(image_abs)
        image_relpath = f"/static/uploads/{fname}"

    item = {
        "id": uuid.uuid4().hex[:12],
        "name": name, "category": category, "color": color,
        "style": style, "warmth": warmth, "season": season,
        "image": image_relpath, "created_at": datetime.now().isoformat(),
    }

    items = load_wardrobe()
    items.append(item)
    save_wardrobe(items)

    # 异步（实为轻量同步）算 embedding
    if image_abs:
        try:
            emb = get_embedder()
            if emb is not None and emb.is_ready():
                emb.upsert(item["id"], image_abs)
                log.info("embedding cached: %s", item["id"])
        except Exception as e:
            log.warning("embedding 计算失败: %s", e)

    return jsonify(item)


@app.route("/api/wardrobe/<item_id>", methods=["DELETE"])
def api_delete_item(item_id):
    items = load_wardrobe()
    items = [it for it in items if it["id"] != item_id]
    save_wardrobe(items)
    try:
        emb = get_embedder()
        if emb is not None and emb.is_ready():
            emb.remove(item_id)
    except Exception as e:
        log.warning("删除 embedding 失败: %s", e)
    return jsonify({"ok": True})


@app.route("/api/weather")
def api_weather():
    city = request.args.get("city", "北京")
    return jsonify(get_weather(city))


@app.route("/api/ai/status")
def api_ai_status():
    """前端可轮询此端点展示 AI 状态。"""
    from ai.device import get_available_memory_mb

    emb = get_embedder()
    reasoner = get_reasoner()

    return jsonify({
        "fashion_clip": {
            "model_exists": emb is not None and emb.model_exists(),
            "ready": emb is not None and emb.is_ready(),
            "remote": emb.is_remote() if emb else False,
            "cached_items": len(emb._id_to_idx) if emb else 0,
            "disabled_reason": emb.disabled_reason() if emb else None,
        },
        "llm": {
            "model_exists": reasoner is not None and reasoner.is_available(),
            "ready": reasoner is not None and reasoner.is_ready(),
            "backend": reasoner.backend() if reasoner else "none",
            "remote": reasoner.is_remote() if reasoner else False,
            "remote_url": reasoner.remote_url if reasoner else "",
            "disabled_reason": reasoner.disabled_reason() if reasoner else None,
        },
        "system": {
            "available_memory_mb": get_available_memory_mb(),
            "platform": os.uname().sysname if hasattr(os, "uname") else sys.platform,
        },
    })


@app.route("/api/recommend", methods=["GET", "POST"])
def api_recommend():
    if request.method == "POST":
        body = request.get_json(silent=True) or {}
        city = body.get("city") or request.args.get("city", "北京")
        occasion = body.get("occasion") or request.args.get("occasion", "日常")
    else:
        city = request.args.get("city", "北京")
        occasion = request.args.get("occasion", "日常")

    wardrobe = load_wardrobe()
    weather = get_weather(city)
    temp = weather["temp"]
    suggested_warmth = get_warmth_from_temp(temp)

    # 1) 规则生成候选（用实际温度过滤后再扩到 12 套）
    raw_candidates = generate_candidates(wardrobe, occasion, weather["weather_type"], cap=40)
    # 温度过滤
    filtered = [c for c in raw_candidates
                if all(it.get("warmth", "适中") in suggested_warmth for it in c["items"])]
    if len(filtered) < 6:
        filtered = raw_candidates  # 不够就放宽
    candidates = filtered[:12]

    if not candidates:
        return jsonify({
            "weather": weather, "occasion": occasion,
            "outfits": [], "total_items": len(wardrobe),
            "ai": {"used_visual": False, "used_llm": False},
        })

    # 2) 视觉打分 + 融合排序
    candidates = ai_score_candidates(candidates)
    top_for_llm = candidates[:6]

    # 3) LLM 精排
    rerank = ai_rerank(weather, occasion, top_for_llm)
    by_id = {c["id"]: c for c in top_for_llm}

    # 4) 组装最终结果
    outfits = []
    for rank, cid in enumerate(rerank["order"], 1):
        c = by_id.get(cid)
        if not c:
            continue
        items = c["items"]
        outfits.append({
            "rank": rank,
            "items": items,
            "score": round(c["combined_score"], 2),
            "rule_score": round(c["rule_score"], 2),
            "visual_score": round(c.get("visual_score", 0), 3),
            "reason": rerank["reasons"].get(cid, ""),
            "description": " + ".join(it["name"] for it in items),
        })

    return jsonify({
        "weather": weather,
        "occasion": occasion,
        "outfits": outfits,
        "total_items": len(wardrobe),
        "ai": {
            "used_visual": any(c.get("visual_score", 0) > 0 for c in top_for_llm),
            "used_llm": rerank.get("used_ai", False),
            "llm_backend": get_reasoner().backend() if get_reasoner() else "none",
        },
    })


# 显式暴露 static 目录（默认 Flask 已支持，保持兼容）
@app.route("/static/<path:filename>")
def static_files(filename):
    return send_from_directory("static", filename)


if __name__ == "__main__":
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "5050"))
    debug = os.environ.get("DEBUG", "0") == "1"
    log.info("启动 Flask: http://%s:%d (debug=%s)", host, port, debug)
    app.run(host=host, port=port, debug=debug, threaded=True)
