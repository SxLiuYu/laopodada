"""
laopodada-api — independent microservice for 老婆哒哒 mobile clients.
Modules: wardrobe (items), recipe (recipes).
Run via gunicorn -c gunicorn.conf.py app:app
"""
import io
import json
import llm
import os
import sqlite3
import time
import urllib.request
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from flask import Flask, abort, g, jsonify, request, send_from_directory
from PIL import Image

# Pillow 9.x had `Image.LANCZOS` as a module-level alias; Pillow 10+ moved it to
# `Image.Resampling.LANCZOS`. Try the modern path first, fall back for older Pillow.
try:
    LANCZOS = Image.Resampling.LANCZOS  # type: ignore[attr-defined]
except AttributeError:
    LANCZOS = Image.LANCZOS  # type: ignore[attr-defined]

# ---------- Config ----------
DATA_DIR = os.environ.get("LAOPODADA_DATA_DIR", "/data/laopodada")
IMG_DIR = os.path.join(DATA_DIR, "images")
ORIG_DIR = os.path.join(IMG_DIR, "original")
LIST_DIR = os.path.join(IMG_DIR, "list")
THUMB_DIR = os.path.join(IMG_DIR, "thumb")
DB_PATH = os.path.join(DATA_DIR, "db", "laopodada.db")

THUMB_SIZE = 200
LIST_SIZE = 800
ORIG_MAX = 2048
MAX_UPLOAD_BYTES = 20 * 1024 * 1024
ALLOWED_IMAGE_TYPES = {"JPEG", "PNG", "WEBP"}
WARDROBE_CATEGORIES = {"top", "bottom", "dress", "outerwear", "shoes", "bag", "accessory"}
RECIPE_CATEGORIES = {"breakfast", "lunch", "dinner", "snack", "dessert", "drink"}
RECIPE_DIFFICULTY = {"easy", "medium", "hard"}

# Outfit recommendation
OCCASIONS = {"casual", "work", "date", "sport", "party", "home"}
SEASONS = {"spring", "summer", "fall", "winter"}
COLOR_HARMONY = {
    # Simple color-wheel rules: each base color -> list of colors that go with it.
    # "neutral" colors go with anything.
    "neutral":   ["black", "white", "gray", "beige", "navy", "blue", "red", "green", "yellow", "pink", "brown", "purple", "orange"],
    "black":     ["black", "white", "gray", "red", "pink", "blue", "yellow", "beige"],
    "white":     ["black", "white", "blue", "red", "pink", "green", "yellow", "gray", "navy", "beige"],
    "gray":      ["black", "white", "gray", "red", "pink", "blue", "yellow", "purple", "navy"],
    "blue":      ["white", "blue", "gray", "beige", "navy", "black", "yellow"],
    "navy":      ["white", "beige", "gray", "blue", "yellow", "red", "black"],
    "red":       ["black", "white", "gray", "beige", "navy", "blue"],
    "pink":      ["white", "gray", "beige", "navy", "blue", "black"],
    "green":     ["white", "beige", "gray", "navy", "black", "yellow"],
    "yellow":    ["black", "white", "gray", "navy", "blue", "purple"],
    "beige":     ["white", "beige", "black", "navy", "brown", "blue", "green"],
    "brown":     ["beige", "white", "black", "blue", "green", "yellow"],
    "purple":    ["white", "gray", "beige", "black", "yellow"],
    "orange":    ["white", "black", "gray", "navy", "beige", "blue"],
}
# Category mapping: which slots do we try to fill in an outfit?
OCCASION_SLOTS = {
    # default slot list per occasion; not all items are required
    "casual": ["top", "bottom", "shoes", "accessory"],
    "work":   ["top", "bottom", "outerwear", "shoes", "bag"],
    "date":   ["dress", "outerwear", "shoes", "accessory"],
    "sport":  ["top", "bottom", "shoes"],
    "party":  ["dress", "outerwear", "shoes", "accessory", "bag"],
    "home":   ["top", "bottom"],
}
# Category that can substitute for "top+bottom" combo (e.g. one-piece dress)
DRESS_ONLY = "dress"

# ---------- Flask ----------
app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_BYTES

# CORS: allow Capacitor WebView (capacitor://localhost / https://localhost) to call our API
@app.after_request
def _cors(resp):
    resp.headers["Access-Control-Allow-Origin"] = "*"
    resp.headers["Access-Control-Allow-Methods"] = "GET, POST, DELETE, OPTIONS"
    resp.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    return resp

@app.route("/<path:_>", methods=["OPTIONS"])
def _preflight(_):
    return ("", 204)


# ---------- DB ----------
def get_db() -> sqlite3.Connection:
    if "db" not in g:
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        g.db = sqlite3.connect(DB_PATH, timeout=10, isolation_level=None)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA journal_mode=WAL")
        g.db.execute("PRAGMA foreign_keys=ON")
    return g.db


@app.teardown_appcontext
def close_db(_exc):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db() -> None:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    db = sqlite3.connect(DB_PATH, timeout=10)
    db.executescript("""
        CREATE TABLE IF NOT EXISTS wardrobe_items (
            id           TEXT PRIMARY KEY,
            title        TEXT,
            category     TEXT NOT NULL,
            brand        TEXT,
            color        TEXT,
            season       TEXT,
            note         TEXT,
            original_url TEXT,
            list_url     TEXT,
            thumb_url    TEXT,
            bytes_orig   INTEGER,
            created_at   INTEGER NOT NULL,
            updated_at   INTEGER NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_wardrobe_category ON wardrobe_items(category);
        CREATE INDEX IF NOT EXISTS idx_wardrobe_created  ON wardrobe_items(created_at DESC);

        CREATE TABLE IF NOT EXISTS recipes (
            id           TEXT PRIMARY KEY,
            title        TEXT NOT NULL,
            category     TEXT NOT NULL,
            difficulty   TEXT NOT NULL,
            prep_minutes INTEGER,
            cook_minutes INTEGER,
            servings     INTEGER,
            ingredients  TEXT NOT NULL,
            steps        TEXT NOT NULL,
            tags         TEXT,
            note         TEXT,
            cover_url    TEXT,
            bytes_cover  INTEGER,
            created_at   INTEGER NOT NULL,
            updated_at   INTEGER NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_recipe_category   ON recipes(category);
        CREATE INDEX IF NOT EXISTS idx_recipe_difficulty ON recipes(difficulty);
        CREATE INDEX IF NOT EXISTS idx_recipe_created    ON recipes(created_at DESC);

        CREATE TABLE IF NOT EXISTS outfits (
            id           TEXT PRIMARY KEY,
            occasion     TEXT NOT NULL,
            season       TEXT,
            item_ids     TEXT NOT NULL,           -- JSON array of wardrobe_items.id
            reason       TEXT,                    -- one-line human explanation (rule + color)
            llm_note     TEXT,                    -- optional LLM-generated tip
            style_score  REAL,                    -- 0..1 internal score (rule + color harmony)
            created_at   INTEGER NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_outfits_occasion ON outfits(occasion);
        CREATE INDEX IF NOT EXISTS idx_outfits_created  ON outfits(created_at DESC);

        CREATE TABLE IF NOT EXISTS outfit_feedback (
            outfit_id  TEXT NOT NULL,
            score      INTEGER NOT NULL CHECK(score IN (-1,0,1)),
            created_at INTEGER NOT NULL,
            FOREIGN KEY(outfit_id) REFERENCES outfits(id)
        );
        CREATE INDEX IF NOT EXISTS idx_outfit_feedback_outfit ON outfit_feedback(outfit_id);

        CREATE TABLE IF NOT EXISTS outfit_recommendations (
            id              TEXT PRIMARY KEY,
            session_id      TEXT,
            context TEXT,
            recommended_ids TEXT NOT NULL,
            created_at      INTEGER NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_recommendations_session ON outfit_recommendations(session_id);
        CREATE INDEX IF NOT EXISTS idx_recommendations_created  ON outfit_recommendations(created_at DESC);
    """)
    db.commit()
    db.close()


# ---------- Image pipeline ----------
def _ensure_image_dirs() -> None:
    for d in (ORIG_DIR, LIST_DIR, THUMB_DIR):
        os.makedirs(d, exist_ok=True)


def _save_three_sizes(raw: bytes) -> dict[str, Any]:
    """Resize once, save at three sizes. Returns dict of paths + bytes."""
    _ensure_image_dirs()
    try:
        img: Image.Image = Image.open(io.BytesIO(raw))
    except Exception as e:
        abort(400, description=f"无法识别图片: {e}")
    img.load()
    img_format = (img.format or "").upper()
    if img_format not in ALLOWED_IMAGE_TYPES:
        abort(400, description=f"不支持的图片格式: {img_format}")

    # Re-encode source as RGB (no alpha) so all 3 sizes share a clean pipeline.
    if img.mode in ("RGBA", "LA", "P"):
        bg = Image.new("RGB", img.size, (255, 255, 255))
        img = img.convert("RGBA") if img.mode != "RGBA" else img
        bg.paste(img, mask=img.split()[-1] if img.mode == "RGBA" else None)
        img = bg
    elif img.mode != "RGB":
        img = img.convert("RGB")

    item_id = uuid.uuid4().hex[:16]
    # Public URL prefix for serving the saved image.
    # Resolution order:
    #   1. LAOPODADA_PUBLIC_BASE env var (explicit override)
    #   2. request.url_root + "images" — auto-detect scheme+host+port from
    #      the incoming request and append the images path. Works in CI
    #      (gunicorn at 127.0.0.1:8097) and in production (Nginx front of
    #      gunicorn, as long as Nginx preserves the Host header).
    if "LAOPODADA_PUBLIC_BASE" in os.environ:
        base = os.environ["LAOPODADA_PUBLIC_BASE"].rstrip("/")
    else:
        try:
            base = request.url_root.rstrip("/") + "/images"
        except RuntimeError:
            base = "/images"

    # 1) original — resize only if larger than ORIG_MAX on long edge
    w, h = img.size
    long_edge = max(w, h)
    if long_edge > ORIG_MAX:
        scale = ORIG_MAX / long_edge
        nw, nh = int(w * scale), int(h * scale)
        orig = img.resize((nw, nh), Image.LANCZOS)
    else:
        orig = img
    orig_path = os.path.join(ORIG_DIR, f"{item_id}.jpg")
    orig.save(orig_path, "JPEG", quality=88, optimize=True)
    bytes_orig = os.path.getsize(orig_path)

    # 2) list
    list_img = _resize_long_edge(img, LIST_SIZE)
    list_path = os.path.join(LIST_DIR, f"{item_id}.jpg")
    list_img.save(list_path, "JPEG", quality=82, optimize=True)

    # 3) thumb
    thumb_img = _resize_long_edge(img, THUMB_SIZE)
    thumb_path = os.path.join(THUMB_DIR, f"{item_id}.jpg")
    thumb_img.save(thumb_path, "JPEG", quality=75, optimize=True)

    return {
        "original_url": f"{base}/original/{item_id}.jpg",
        "list_url":     f"{base}/list/{item_id}.jpg",
        "thumb_url":    f"{base}/thumb/{item_id}.jpg",
        "bytes_orig":   bytes_orig,
        "_item_id":     item_id,
    }


def _resize_long_edge(img: Image.Image, target: int) -> Image.Image:
    w, h = img.size
    if max(w, h) <= target:
        return img
    scale = target / max(w, h)
    return img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)


def _ts_iso(ts: int) -> str:
    return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat().replace("+00:00", "Z")


def _row_to_wardrobe(row: sqlite3.Row) -> dict:
    return {
        "id":              row["id"],
        "title":           row["title"],
        "category":        row["category"],
        "brand":           row["brand"],
        "color":           row["color"],
        "season":          row["season"],
        "note":            row["note"],
        "original_url":    row["original_url"],
        "list_url":        row["list_url"],
        "thumbnail_url":   row["thumb_url"],
        "bytes_orig":      row["bytes_orig"],
        "created_at":      row["created_at"],
        "created_at_iso":  _ts_iso(row["created_at"]),
        "updated_at":      row["updated_at"],
    }


def _row_to_recipe(row: sqlite3.Row) -> dict:
    return {
        "id":             row["id"],
        "title":          row["title"],
        "category":       row["category"],
        "difficulty":     row["difficulty"],
        "prep_minutes":   row["prep_minutes"],
        "cook_minutes":   row["cook_minutes"],
        "servings":       row["servings"],
        "ingredients":    [s for s in (row["ingredients"] or "").split("\n") if s],
        "steps":          [s for s in (row["steps"] or "").split("\n") if s],
        "tags":           [s.strip() for s in (row["tags"] or "").split(",") if s.strip()],
        "note":           row["note"],
        "cover_url":      row["cover_url"],
        "bytes_cover":    row["bytes_cover"],
        "created_at":     row["created_at"],
        "created_at_iso": _ts_iso(row["created_at"]),
        "updated_at":     row["updated_at"],
    }


# ---------- Health ----------
@app.get("/health")
def health():
    return jsonify(ok=True, service="laopodada-api", time=int(time.time()))


# ---------- Image serving (fallback when no Nginx in front) ----------
# In production on Server 2, Nginx serves /images/* directly from the
# shared /data volume. For local dev and CI, expose the same files via
# Flask so the smoke test can fetch them.
@app.get("/images/<path:relpath>")
def serve_image(relpath: str):
    # relpath looks like "list/cf31...jpg" or "thumb/..." or "original/..."
    full = os.path.normpath(os.path.join(IMG_DIR, relpath))
    if not full.startswith(os.path.normpath(IMG_DIR)):
        abort(404)
    if not os.path.isfile(full):
        abort(404)
    return send_from_directory(os.path.dirname(full), os.path.basename(full))


# ---------- Wardrobe ----------
@app.get("/api/v1/items")
def list_items():
    category = request.args.get("category")
    limit = max(1, min(int(request.args.get("limit", 100)), 500))
    offset = max(0, int(request.args.get("offset", 0)))
    db = get_db()
    if category:
        rows = db.execute(
            "SELECT * FROM wardrobe_items WHERE category=? ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (category, limit, offset),
        ).fetchall()
        total = db.execute("SELECT COUNT(*) c FROM wardrobe_items WHERE category=?", (category,)).fetchone()["c"]
    else:
        rows = db.execute(
            "SELECT * FROM wardrobe_items ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (limit, offset),
        ).fetchall()
        total = db.execute("SELECT COUNT(*) c FROM wardrobe_items").fetchone()["c"]
    return jsonify(count=total, items=[_row_to_wardrobe(r) for r in rows])


@app.post("/api/v1/items")
def create_item():
    f = request.files.get("file")
    if not f:
        abort(400, description="缺少 file 字段")
    category = (request.form.get("category") or "").strip()
    if category not in WARDROBE_CATEGORIES:
        abort(400, description=f"category 必须是 {sorted(WARDROBE_CATEGORIES)} 之一")

    saved = _save_three_sizes(f.read())
    now = int(time.time())
    db = get_db()
    db.execute(
        """INSERT INTO wardrobe_items
           (id, title, category, brand, color, season, note,
            original_url, list_url, thumb_url, bytes_orig, created_at, updated_at)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            saved["_item_id"],
            (request.form.get("title") or "").strip() or None,
            category,
            (request.form.get("brand") or "").strip() or None,
            (request.form.get("color") or "").strip() or None,
            (request.form.get("season") or "").strip() or None,
            (request.form.get("note") or "").strip() or None,
            saved["original_url"],
            saved["list_url"],
            saved["thumb_url"],
            saved["bytes_orig"],
            now, now,
        ),
    )
    row = db.execute("SELECT * FROM wardrobe_items WHERE id=?", (saved["_item_id"],)).fetchone()
    return jsonify(item=_row_to_wardrobe(row))


@app.get("/api/v1/items/<item_id>")
def get_item(item_id: str):
    db = get_db()
    row = db.execute("SELECT * FROM wardrobe_items WHERE id=?", (item_id,)).fetchone()
    if not row:
        abort(404, description="not found")
    return jsonify(_row_to_wardrobe(row))


@app.delete("/api/v1/items/<item_id>")
def delete_item(item_id: str):
    db = get_db()
    row = db.execute("SELECT * FROM wardrobe_items WHERE id=?", (item_id,)).fetchone()
    if not row:
        abort(404, description="not found")
    for url_key in ("original_url", "list_url", "thumb_url"):
        url = row[url_key]
        # /images/{list,thumb,original}/<id>.jpg  ->  file under DATA_DIR/images/...
        if url:
            fname = url.rsplit("/", 1)[-1]
            kind = url_key.replace("_url", "")  # original_url -> original
            path = os.path.join(IMG_DIR, kind if kind != "thumb" else "thumb", fname)
            try:
                os.remove(path)
            except FileNotFoundError:
                pass
    db.execute("DELETE FROM wardrobe_items WHERE id=?", (item_id,))
    return jsonify(id=item_id, ok=True)


# ---------- Recipe ----------
@app.get("/api/v1/recipes")
def list_recipes():
    category = request.args.get("category")
    difficulty = request.args.get("difficulty")
    tag = request.args.get("tag")
    limit = max(1, min(int(request.args.get("limit", 100)), 500))
    offset = max(0, int(request.args.get("offset", 0)))

    where, params = [], []
    if category:
        where.append("category=?")
        params.append(category)
    if difficulty:
        where.append("difficulty=?")
        params.append(difficulty)
    if tag:
        # comma-joined list — match if tag appears in CSV
        where.append("','||tags||',' LIKE ?")
        params.append(f"%,{tag},%")
    where_sql = ("WHERE " + " AND ".join(where)) if where else ""

    db = get_db()
    rows = db.execute(
        f"SELECT * FROM recipes {where_sql} ORDER BY created_at DESC LIMIT ? OFFSET ?",
        (*params, limit, offset),
    ).fetchall()
    total = db.execute(f"SELECT COUNT(*) c FROM recipes {where_sql}", params).fetchone()["c"]
    return jsonify(count=total, recipes=[_row_to_recipe(r) for r in rows])


@app.post("/api/v1/recipes")
def create_recipe():
    body = request.get_json(silent=True) or {}
    title = (body.get("title") or "").strip()
    category = (body.get("category") or "").strip()
    difficulty = (body.get("difficulty") or "").strip()

    if not title:
        abort(400, description="title 必填")
    if category not in RECIPE_CATEGORIES:
        abort(400, description=f"category 必须是 {sorted(RECIPE_CATEGORIES)} 之一")
    if difficulty not in RECIPE_DIFFICULTY:
        abort(400, description=f"difficulty 必须是 {sorted(RECIPE_DIFFICULTY)} 之一")

    ingredients = body.get("ingredients") or []
    if isinstance(ingredients, list):
        ingredients_str = "\n".join(str(x) for x in ingredients)
    else:
        ingredients_str = str(ingredients)
    if not ingredients_str.strip():
        abort(400, description="ingredients 必填")

    steps = body.get("steps") or []
    if isinstance(steps, list):
        steps_str = "\n".join(str(x) for x in steps)
    else:
        steps_str = str(steps)
    if not steps_str.strip():
        abort(400, description="steps 必填")

    tags = body.get("tags") or []
    if isinstance(tags, list):
        tags_str = ",".join(str(t).strip() for t in tags if str(t).strip())
    else:
        tags_str = str(tags)

    cover_url = None
    bytes_cover = 0
    cover_file = request.files.get("cover")
    if cover_file:
        saved = _save_three_sizes(cover_file.read())
        cover_url = saved["list_url"]  # use list size for cover (saves space)
        bytes_cover = saved["bytes_orig"]

    now = int(time.time())
    rid = uuid.uuid4().hex[:16]
    db = get_db()
    db.execute(
        """INSERT INTO recipes
           (id, title, category, difficulty, prep_minutes, cook_minutes, servings,
            ingredients, steps, tags, note, cover_url, bytes_cover,
            created_at, updated_at)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            rid, title, category, difficulty,
            body.get("prep_minutes"), body.get("cook_minutes"), body.get("servings"),
            ingredients_str, steps_str, tags_str, body.get("note"),
            cover_url, bytes_cover, now, now,
        ),
    )
    row = db.execute("SELECT * FROM recipes WHERE id=?", (rid,)).fetchone()
    return jsonify(recipe=_row_to_recipe(row))


@app.get("/api/v1/recipes/<recipe_id>")
def get_recipe(recipe_id: str):
    db = get_db()
    row = db.execute("SELECT * FROM recipes WHERE id=?", (recipe_id,)).fetchone()
    if not row:
        abort(404, description="not found")
    return jsonify(_row_to_recipe(row))


@app.delete("/api/v1/recipes/<recipe_id>")
def delete_recipe(recipe_id: str):
    db = get_db()
    row = db.execute("SELECT * FROM recipes WHERE id=?", (recipe_id,)).fetchone()
    if not row:
        abort(404, description="not found")
    if row["cover_url"]:
        fname = row["cover_url"].rsplit("/", 1)[-1]
        for kind in ("list", "original", "thumb"):
            try:
                os.remove(os.path.join(IMG_DIR, kind, fname))
            except FileNotFoundError:
                pass
    db.execute("DELETE FROM recipes WHERE id=?", (recipe_id,))
    return jsonify(id=recipe_id, ok=True)


# ---------- Health articles (in-memory, no DB) ----------
HEALTH_ARTICLES = [
    {
        "id": "h001",
        "title": "蛋白质摄入指南",
        "category": "nutrition",
        "summary": "成年人每日蛋白质摄入量建议为每公斤体重0.8-1.2克,优质蛋白来源包括鸡胸肉、鱼类、鸡蛋、豆制品和乳制品。合理分配到每餐有助于肌肉合成和免疫维护。",
        "content": """## 蛋白质摄入指南

蛋白质是生命的基础营养素,约占人体重量的16%。合理摄入蛋白质对维持肌肉质量、免疫功能和代谢健康至关重要。

### 每日摄入量推荐

- **一般成年人**: 0.8-1.2g/kg体重/天
- **运动人群**: 1.2-2.0g/kg体重/天
- **增肌期**: 1.6-2.2g/kg体重/天

### 优质蛋白来源

| 食物 | 每100g蛋白含量 | 吸收率 |
|------|---------------|--------|
| 鸡胸肉 | 31g | 90% |
| 三文鱼 | 20g | 85% |
| 鸡蛋 | 13g | 100% |
| 豆腐 | 8g | 80% |
| 牛奶 | 3.4g | 85% |

### 分配技巧

将蛋白质均匀分配到三餐,每餐摄入25-40g优质蛋白,可最大化肌肉蛋白合成。例如:

- **早餐**: 3个鸡蛋 + 1杯牛奶
- **午餐**: 150g鸡胸肉
- **晚餐**: 200g鱼肉 + 1份豆腐

### 特殊人群注意

- **肾功能不全者**: 需限制蛋白摄入,请遵医嘱
- **素食者**: 注意搭配豆类+谷物,提高蛋白质利用率
- **老年人**: 适当增加蛋白摄入,有助于预防肌少症
""",
        "tags": ["蛋白质", "饮食", "营养"],
        "read_minutes": 5,
        "source": "中国居民膳食指南 2022 / WHO 2024",
    },
    {
        "id": "h002",
        "title": "Omega-3 脂肪酸的 7 大益处",
        "category": "nutrition",
        "summary": "Omega-3 是人体必需的多元不饱和脂肪酸,主要来源包括三文鱼、秋刀鱼、亚麻籽和核桃。研究证实其对心血管、大脑和眼部健康有显著益处。",
        "content": """## Omega-3 脂肪酸的 7 大益处

Omega-3 是人体无法自行合成、必须从食物中获取的必需脂肪酸,主要包括 EPA（二十碳五烯酸）和 DHA（二十二碳六烯酸）。

### 7 大健康益处

**1. 维护心血管健康**
Omega-3 能降低血液中的甘油三酯水平,减少动脉粥样硬化风险。建议每周摄入2-3次富含Omega-3的鱼类。

**2. 促进大脑功能**
DHA 是大脑细胞膜的主要成分,充足的Omega-3摄入有助于维持记忆力和认知功能,延缓大脑衰老。

**3. 改善眼部健康**
视网膜中DHA含量高达50%,Omega-3有助于预防黄斑变性和干眼症。

**4. 抗炎作用**
EPA 和 DHA 可转化为消退素（Resolvins）,帮助身体及时消退炎症反应,减轻慢性炎症状态。

**5. 改善情绪与睡眠**
研究表明,Omega-3 补充有助于缓解抑郁症状,改善睡眠质量,尤其对季节性情绪障碍有辅助改善作用。

**6. 支持运动恢复**
Omega-3 的抗炎特性可减少运动后的肌肉酸痛,加速恢复,运动员和健身人群尤为有益。

**7. 促进骨骼健康**
Omega-3 有助于提高钙的吸收率,减缓骨质流失,对绝经后女性骨骼保护尤为重要。

### 每日推荐摄入量

- **成人**: EPA+DHA 合计 250-500mg/天
- **心血管高危人群**: 1000mg/天
- **儿童**: 按体重调整,约 100-200mg/天

### 优质食物来源

**动物来源**（含 DHA/EPA）:
- 三文鱼（3oz约1800mg）
- 秋刀鱼、沙丁鱼、鲭鱼
- 海藻油（素食来源）

**植物来源**（含 ALA,需在体内转化）:
- 亚麻籽（1汤匙约2400mg ALA）
- 奇亚籽
- 核桃（1盎司约2600mg ALA）
""",
        "tags": ["Omega-3", "饮食", "抗炎"],
        "read_minutes": 4,
        "source": "AHA 2023 / 中国居民膳食营养素参考摄入量",
    },
    {
        "id": "h003",
        "title": "成年人每周运动量推荐",
        "category": "exercise",
        "summary": "WHO 建议成年人每周进行150-300分钟中等强度有氧运动,或75-150分钟高强度有氧运动,并结合2次以上力量训练,可显著降低心血管疾病和全因死亡风险。",
        "content": """## 成年人每周运动量推荐

规律运动是维护健康最有效的手段之一。全球各大健康组织对成年人运动量有明确推荐。

### WHO 运动指南（2020版）

| 运动类型 | 最低推荐量 | 最佳推荐量 |
|---------|-----------|-----------|
| 中等强度有氧 | 150分钟/周 | 300分钟/周 |
| 高强度有氧 | 75分钟/周 | 150分钟/周 |
| 或两者组合 | 150分钟等效 | 300分钟等效 |

**等效换算**: 1分钟高强度 = 2分钟中等强度

### 有氧运动推荐

**中等强度**（呼吸稍快,能说话不能唱歌）:
- 快走（5-6km/h）
- 骑自行车（<16km/h）
- 游泳（慢速）
- 跳舞

**高强度**（呼吸急促,说话困难）:
- 跑步
- 游泳（快速）
- 跳绳
- HIIT 训练

### 力量训练同样重要

建议每周至少 **2次** 力量训练,针对主要肌群:

- 下肢: 深蹲、弓步蹲
- 上肢: 俯卧撑、哑铃划船
- 核心: 平板支撑、卷腹

### 不同年龄段的调整

**18-64岁**: 严格遵循上述指南

**65岁以上**: 以中等强度为主,重点关注平衡和柔韧性训练,预防跌倒

**久坐人群**: 从每天10分钟开始,逐步增加,避免突然剧烈运动

### 运动 tips

- 分段运动（每次10分钟）与单次长时间效果相当
- 步行是最简单且有效的起点
- 选择喜欢的运动形式,更容易坚持
""",
        "tags": ["运动", "有氧", "健身", "WHO"],
        "read_minutes": 5,
        "source": "WHO 2020 Global Physical Activity Guidelines",
    },
    {
        "id": "h004",
        "title": "久坐危害 + 5 个微习惯",
        "category": "exercise",
        "summary": "久坐（每日 >8小时）显著增加心血管疾病、糖尿病和全因死亡风险。每工作30分钟起身活动2分钟,可有效改善代谢指标。5个简单微习惯帮助打破久坐惯性。",
        "content": """## 久坐危害 + 5 个微习惯

现代生活方式使久坐成为最常见的健康威胁之一。大量研究证实,久坐行为独立于运动量,本身就对健康有显著危害。

### 久坐的健康危害

**代谢方面**:
- 血糖调节能力下降,胰岛素敏感性降低
- 血脂异常,甘油三酯升高
- 基础代谢率下降,脂肪更容易堆积

**心血管方面**:
- 心血管疾病风险增加 20-30%
- 血压升高
- 深静脉血栓风险

**肌肉骨骼方面**:
- 腰背疼痛
- 髋关节灵活性下降
- 核心肌群弱化

### 5 个微习惯打破久坐

**习惯 1: 30分钟起身动2分钟**
设置计时器,每半小时站起来活动——伸展、走动、倒水。累计效果相当于每天多消耗200卡路里。

**习惯 2: 站立式办公交替**
使用升降桌,或每工作45分钟后站10分钟,交替进行。

**习惯 3: 边通话边走路**
接打电话时站起来走动,或直接走到窗边边看风景边聊。

**习惯 4: 午餐后散步10分钟**
不要吃完饭立刻坐下,利用午休时间散步有助消化和控制血糖。

**习惯 5: 晚间「动一动」仪式**
睡前做5分钟拉伸或瑜伽,帮助缓解一天的肌肉紧张,也是入睡的放松仪式。

### 每日目标

无需高强度运动,只需要**打破连续久坐**,就能带来显著健康改善。目标是每天站立+活动时间累计超过 **4小时**。
""",
        "tags": ["久坐", "微习惯", "办公室", "健康"],
        "read_minutes": 4,
        "source": "The Lancet 2019 / JAMA 2022",
    },
    {
        "id": "h005",
        "title": "高血压日常管理",
        "category": "disease",
        "summary": "中国高血压患者超过3亿,日常管理关键在于：DASH饮食（得舒饮食）、每日盐摄入控制在5g以内、规律监测血压、适度运动、保持健康体重和充足睡眠。",
        "content": """## 高血压日常管理

高血压是中国最常见的慢性病之一,患病人数超过3亿,但控制率仅约16%。科学的日常管理可以有效降低心脑血管事件风险。

### 血压控制目标

| 人群 | 目标血压 |
|------|---------|
| 一般成年人 | <130/80 mmHg |
| 65岁以上老年人 | <140/90 mmHg |
| 合并糖尿病/肾病 | <130/80 mmHg |

### 核心措施 1: DASH 得舒饮食

得舒饮食（DASH Diet）是经研究证实能有效降压的饮食模式:

**推荐多吃的食物**:
- 新鲜蔬菜: 每天500g以上
- 新鲜水果: 每天200-350g
- 全谷物: 糙米、燕麦、全麦面包
- 低脂乳制品
- 坚果、豆类
- 瘦肉类（禽肉、鱼肉为主）

**需要限制的食物**:
- 盐: 每日 <5g（约1茶匙）
- 饱和脂肪: 少吃肥肉、全脂奶
- 添加糖: 少喝甜饮料

### 核心措施 2: 控盐技巧

- 使用限盐勺（每人每天 <5g）
- 用香草、姜、蒜、柠檬替代部分盐调味
- 少吃腌制食品、酱料、加工肉制品
- 学会看食品营养标签的钠含量

### 核心措施 3: 规律监测

- 建议购买经过验证的上臂式电子血压计
- 早晚各测量一次,测量前静坐5分钟
- 记录血压日记,就诊时带给医生参考
- 测量时手臂支撑,与心脏同高

### 核心措施 4: 生活方式

- **适度运动**: 每周5次,每次30分钟中等强度有氧
- **控制体重**: BMI 维持在 18.5-24
- **戒烟限酒**: 彻底戒烟,男性每日酒精 <25g
- **充足睡眠**: 每日 7-8 小时,规律作息

### 何时就医

若血压持续 >160/100 mmHg,或出现头痛、胸闷、呼吸困难等症状,应立即就医。
""",
        "tags": ["高血压", "饮食", "控盐", "DASH"],
        "read_minutes": 6,
        "source": "中国高血压防治指南 2018 / JNC 2023",
    },
    {
        "id": "h006",
        "title": "糖尿病前期逆转方法",
        "category": "disease",
        "summary": "糖尿病前期（空腹血糖100-125mg/dL）是可逆的关键阶段。研究证实,体重减轻5-7%、每周运动150分钟,可以让60%以上的糖尿病前期患者血糖恢复正常。",
        "content": """## 糖尿病前期逆转方法

糖尿病前期（Pre-diabetes）是正常血糖与糖尿病之间的灰色地带,特点是空腹血糖受损或糖耐量异常。这一阶段是生活方式干预的最佳时机,也是最后的逆转机会。

### 如何判断糖尿病前期

| 检测指标 | 正常 | 糖尿病前期 | 糖尿病 |
|---------|------|-----------|--------|
| 空腹血糖 | <100 mg/dL | 100-125 | ≥126 |
| 糖化血红蛋白 HbA1c | <5.7% | 5.7-6.4% | ≥6.5% |
| OGTT 2h 血糖 | <140 mg/dL | 140-199 | ≥200 |

### 逆转的核心: 体重管理

**减重目标**: 体重下降 **5-7%**（如70kg者减3.5-5kg）

**研究数据**:
- 减重 5%: 糖尿病前期逆转率约 40%
- 减重 7%: 糖尿病前期逆转率约 60%
- 减重 10%: 糖尿病风险降低 80%

### 逆转方案 4 步走

**第1步: 饮食调整**
- 减少精制碳水化合物（白米饭、白面包、甜食）
- 增加膳食纤维（蔬菜、全谷物、豆类）
- 每餐先吃蔬菜,再吃蛋白,最后吃主食
- 主食替换为糙米、燕麦、藜麦等低GI食材

**第2步: 运动处方**
- 目标: 每周 **150分钟** 中等强度有氧运动
- 推荐: 快走、游泳、骑车
- 配合: 每周 2-3 次力量训练（增加肌肉对葡萄糖的摄取）

**第3步: 睡眠与压力**
- 保证每晚 7-8 小时睡眠
- 睡眠不足会升高皮质醇,加剧胰岛素抵抗
- 冥想、深呼吸有助降低压力激素

**第4步: 定期监测**
- 每 3-6 个月复查 HbA1c
- 关注体重、腰围变化
- 记录饮食和血糖（使用家用血糖仪）

### 营养补充参考

某些营养素对胰岛素敏感性有益:
- **铬**: 绿花椰菜、坚果
- **镁**: 深绿色蔬菜、黑巧克力
- **Omega-3**: 深海鱼、亚麻籽
- **维生素D**: 阳光照射（每天 15 分钟）

### 需要用药的情况

若3-6个月生活方式干预后血糖未改善,或血糖已接近糖尿病诊断标准,应在医生指导下考虑二甲双胍等药物干预。
""",
        "tags": ["糖尿病", "血糖", "逆转", "减重"],
        "read_minutes": 6,
        "source": "ADA Standards of Care 2024 / 中国糖尿病防治指南",
    },
    {
        "id": "h007",
        "title": "焦虑情绪自助 7 法",
        "category": "mental",
        "summary": "焦虑是最常见的情绪问题,7种循证自助方法可有效缓解：无条件自我接纳、呼吸调节、正念冥想、运动、规律作息、表达性写作和社交支持。",
        "content": """## 焦虑情绪自助 7 法

焦虑是一种对未来不确定事件的担忧和恐惧反应,适度焦虑是正常的,但过度焦虑会影响生活和工作。以下是经大量临床研究验证的自助方法。

### 方法 1: 呼吸调节（4-7-8呼吸法）

当焦虑来袭时,交感神经兴奋导致呼吸浅快。简单的呼吸练习可快速激活副交感神经,产生镇静效果。

**操作**:
1. 用鼻子吸气,数 4 拍
2. 屏住呼吸,数 7 拍
3. 用嘴缓慢呼气,数 8 拍
4. 重复 3-4 次

**原理**: 延长呼气可刺激迷走神经,迅速降低焦虑水平。

### 方法 2: 正念冥想（每日10分钟）

正念（Mindfulness）被超过3000项研究证实可有效减轻焦虑和压力。

**入门练习**:
1. 找一个安静位置,坐直
2. 闭眼,将注意力放在呼吸上
3. 当念头出现时,温柔地将注意力拉回呼吸
4. 每天从5分钟开始,逐渐增加到10-20分钟

**推荐APP**: Insight Timer、Headspace（均有免费内容）

### 方法 3: 运动是天然抗焦虑药

运动后大脑会释放内啡肽和血清素,同时降低皮质醇水平。运动抗焦虑效果在很多研究中接近轻度抗焦虑药物。

**推荐方案**:
- 每周 3-5 次,每次 20-30 分钟
- 中等强度有氧（快走、跑步、骑车）
- 瑜伽和太极额外有益于身心调节

### 方法 4: 表达性写作（情绪释放写作）

研究表明,每天花15-20分钟写下自己的担忧和情绪,连续4天,可显著降低焦虑和改善情绪。

**写作提示**:
- "我最担心的事情是..."
- "如果我不再焦虑,我会..."
- "我最感到压力的事情是..."

### 方法 5: 认知重构（识别扭曲思维）

焦虑常常伴随非理性思维模式:

- **灾难化**: "万一...怎么办" → 识别最坏和最可能的结局
- **过度概括**: "总是/从来不" → 寻找反例
- **读心术**: "大家一定觉得我很蠢" → 询问事实而非猜测

**练习**: 记录焦虑触发事件和你的反应,识别思维模式并尝试反例反驳。

### 方法 6: 规律作息

睡眠不足和焦虑互为因果——睡眠质量差会加剧焦虑,而焦虑又会影响睡眠。

**睡眠 hygiene**:
- 固定作息时间（每天同一时间睡和起）
- 睡前1小时减少屏幕使用
- 卧室保持凉爽、黑暗、安静
- 午后避免咖啡因

### 方法 7: 社交支持

研究表明,拥有至少1个可倾诉的朋友是焦虑的重要保护因素。

**实践建议**:
- 主动联系1-2个可信任的朋友/家人
- 参加社团活动、运动俱乐部,扩大社交圈
- 避免过度自我隔离

### 何时寻求专业帮助

若焦虑严重影响日常生活,出现惊恐发作（心悸、出汗、窒息感）、持续失眠或自我伤害念头,请及时就医或寻求心理咨询。
""",
        "tags": ["焦虑", "心理健康", "冥想", "呼吸"],
        "read_minutes": 5,
        "source": "APA 2023 / NIMH Anxiety Disorders Guide",
    },
    {
        "id": "h008",
        "title": "女性月经周期营养调整",
        "category": "female",
        "summary": "女性月经周期分为4个阶段,各阶段激素变化影响代谢和营养需求。经期重点补铁和镁,经后注重蛋白质和复合碳水,排卵前可增加B族维生素摄入。",
        "content": """## 女性月经周期营养调整

女性月经周期受激素调控,不同阶段的激素变化会影响基础代谢率、食欲、情绪和营养需求。根据周期调整饮食,可有效缓解经期不适、提升能量水平。

### 月经周期 4 阶段

**阶段 1: 经期（第1-5天）**
激素特点: 雌激素和孕激素均处于低谷
- 能量水平较低
- 可能出现腹痛、疲劳、情绪波动
- 代谢略有降低

**阶段 2: 经后期（第6-14天）**
激素特点: 雌激素逐渐上升
- 能量恢复,精神好转
- 代谢提升,胰岛素敏感性增强
- 食欲趋于稳定

**阶段 3: 排卵期（第14-16天）**
激素特点: 雌激素达到峰值,孕激素开始上升
- 代谢最高,能量充沛
- 食欲可能略增
- 身体对营养吸收利用率最佳

**阶段 4: 经前期（第15-28天）**
激素特点: 孕激素上升,雌激素回落
- 出现经前综合征（PMS）风险
- 情绪波动、腹胀、乳房胀痛
- 胰岛素敏感性下降,胰岛素抵抗可能增加

### 各阶段营养重点

**经期重点: 补铁 + 镁**

铁: 经期失血导致铁流失,推荐每日18mg
- 动物来源（吸收率高）: 红肉、动物肝脏、蛤蜊
- 植物来源: 菠菜、红豆、黑木耳,配合维生素C促进吸收

镁: 缓解子宫收缩和痛经
- 推荐摄入: 320-360mg/天
- 食物来源: 黑巧克力（85%可可以上）、坚果、鳄梨、深绿叶蔬菜

**经后期重点: 蛋白质 + 复合碳水**

蛋白质有助于修复子宫内膜,复合碳水提供持续能量:
- 优质蛋白: 鸡蛋、鸡胸肉、鱼、豆腐
- 复合碳水: 糙米、燕麦、红薯、全谷物

**排卵期重点: B族维生素**

此阶段代谢旺盛,对B族维生素需求增加:
- 维生素B6: 支持雌激素代谢,缓解PMS
- 维生素B12和叶酸: 准备未来妊娠需求
- 食物来源: 全谷物、鸡蛋、三文鱼、奶制品

**经前期重点: 控盐 + 补钙**

- 控盐: 减少钠摄入可缓解腹胀和水钠潴留
- 钙: 每日1000-1200mg,研究证实可减轻经前综合征
- 维生素D: 帮助钙吸收,每天10-15分钟日照或补充400IU

### 通用建议

**缓解痛经的饮食小技巧**:
- 喝温热的姜茶或肉桂茶（有研究支持）
- 避免咖啡因和酒精（加剧经期不适）
- 每天半勺黑芝麻或亚麻籽（含Omega-3）

**经期不宜**:
- 浓茶（影响铁吸收）
- 高盐加工食品（加重水肿）
- 生冷食物（中医角度可能加重痛经）

**记录月经周期**:
推荐使用 Clue、Flo 等 APP 记录周期,可帮助识别营养与症状关联,优化饮食策略。
""",
        "tags": ["月经", "女性健康", "营养", "铁"],
        "read_minutes": 5,
        "source": "ACOG 2023 / 中国居民膳食指南 2022",
    },
]


@app.get("/api/v1/health/articles")
def list_health_articles():
    """Return in-memory health articles with optional category filter and pagination."""
    category = request.args.get("category")
    limit = max(1, min(int(request.args.get("limit", 10)), 100))
    offset = max(0, int(request.args.get("offset", 0)))

    articles = HEALTH_ARTICLES
    if category:
        articles = [a for a in articles if a["category"] == category]

    total = len(articles)
    paginated = articles[offset : offset + limit]
    return jsonify(count=total, articles=paginated)


@app.get("/api/v1/health/articles/<article_id>")
def get_health_article(article_id: str):
    """Return a single health article by id, or 404."""
    for a in HEALTH_ARTICLES:
        if a["id"] == article_id:
            return jsonify(a)
    abort(404, description="article not found")


# ---------- Outfit recommendation ----------
def _norm_color(c):
    """Normalize a free-text color into one of the COLOR_HARMONY keys.
    Falls back to 'neutral' so it harmonizes with anything."""
    if not c:
        return "neutral"
    s = c.strip().lower()
    # Direct hit
    if s in COLOR_HARMONY:
        return s
    # Substring mapping for common phrasings
    aliases = {
        "navy blue": "navy", "denim": "blue", "light blue": "blue", "sky blue": "blue",
        "dark blue": "navy", "beige/tan": "beige", "tan": "beige", "khaki": "beige",
        "grey": "gray", "burgundy": "red", "maroon": "red", "wine": "red",
        "off-white": "white", "ivory": "white", "cream": "white",
        "olive": "green", "teal": "blue", "turquoise": "blue",
    }
    for k, v in aliases.items():
        if k in s:
            return v
    return "neutral"


def _harmony_score(colors: list[str]) -> float:
    """0..1 score: starts at 1.0, deduct for each clash. Neutral = always OK."""
    if not colors:
        return 0.0
    score = 1.0
    norm = [_norm_color(c) for c in colors]
    # Anchor on first non-neutral color
    anchor = next((c for c in norm if c != "neutral"), None)
    if not anchor:
        return score
    ok_set = set(COLOR_HARMONY.get(anchor, [])) | {"neutral"}
    for c in norm:
        if c not in ok_set and c != anchor:
            score -= 0.25
    return max(0.0, min(1.0, score))


def _season_filter(category, season):
    """A few practical rules; can be loosened later."""
    if not season:
        return True
    s = season.lower()
    # coats/outerwear are useful in cool seasons, less so in hot
    if category == "outerwear" and s in ("summer",):
        return False
    return True


def _rule_pick(items_by_cat: dict[str, list[dict]], slots: list[str]) -> tuple[list[dict], float, str]:
    """Greedy: pick one item per slot, preferring most recently added, with color harmony."""
    chosen: list[dict] = []
    chosen_colors: list[str] = []
    missing: list[str] = []

    for slot in slots:
        cands = items_by_cat.get(slot, [])
        if not cands:
            missing.append(slot)
            continue
        # Score each candidate: prefer items whose color harmonizes with what's chosen so far
        best = None
        best_score = -1.0
        for it in cands:
            c = _norm_color(it.get("color"))
            base = 0.5
            if not chosen_colors:
                base = 0.7
            elif c == "neutral":
                base = 0.9
            elif c in COLOR_HARMONY.get(chosen_colors[0], []) or chosen_colors[0] in COLOR_HARMONY.get(c, []):
                base = 0.95
            else:
                base = 0.4  # clash penalty
            if base > best_score:
                best_score = base
                best = it
        if best is not None:
            chosen.append(best)
            chosen_colors.append(_norm_color(best.get("color")))

    # If occasion expected a dress and we got a top+bottom, that's fine; if we got nothing, return empty
    score = _harmony_score(chosen_colors) if chosen_colors else 0.0
    reason_bits = []
    if missing:
        reason_bits.append(f"缺少: {','.join(missing)}")
    if chosen_colors:
        anchor = next((c for c in chosen_colors if c != "neutral"), chosen_colors[0])
        reason_bits.append(f"主色 {anchor} + 协调配色")
    reason = " · ".join(reason_bits) if reason_bits else "无衣橱可推荐"
    return chosen, score, reason


def _llm_note(occasion, season, items):
    """Optional LLM styling tip. Only called if LAOPODADA_LLM_API_KEY is set.
    Off by default — safe fallback to rule-only output."""
    api_key = os.environ.get("LAOPODADA_LLM_API_KEY")
    if not api_key:
        # Decode from hermes secrets file at runtime
        secret_file = os.path.expanduser("~/.hermes/.secrets/minimax_cn.b64")
        if os.path.exists(secret_file):
            import base64
            with open(secret_file, "r") as f:
                api_key = base64.b64decode(f.read().strip()).decode("utf-8")
    if not api_key:
        return None
    # MiniMax sk-cp subscription key works with OpenAI-compatible endpoint
    base = os.environ.get("LAOPODADA_LLM_BASE", "https://api.minimaxi.com/v1")
    model = os.environ.get("LAOPODADA_LLM_MODEL", "MiniMax-M3")
    item_lines = ", ".join(
        f"{it.get('category')}/{it.get('color') or '?'}/{it.get('title') or it.get('id')}"
        for it in items
    )
    prompt = (
        f"场合:{occasion}, 季节:{season or '未知'}, "
        f"已选单品:{item_lines}。给一条20字内的中文穿搭建议。"
    )
    try:
        req = urllib.request.Request(
            f"{base.rstrip('/')}/chat/completions",
            method="POST",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            data=json.dumps({
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 80,
                "temperature": 0.7,
            }).encode("utf-8"),
        )
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read())
        content = data["choices"][0]["message"]["content"].strip()
        # MiniMax-M3 wraps reasoning in <think>...</think> — strip it
        import re
        content = re.sub(r"<think>.*?</think>\s*", "", content, flags=re.DOTALL).strip()
        return content or None
    except Exception as e:
        return f"(LLM 暂不可用: {e})"


@app.post("/api/v1/outfits/recommend")
def recommend_outfit():
    body = request.get_json(silent=True) or {}
    occasion = (body.get("occasion") or "").strip().lower()
    season = (body.get("season") or "").strip().lower() or None
    weather = body.get("weather") or {}
    limit = body.get("limit", 3)
    if occasion not in OCCASIONS:
        abort(400, description=f"occasion 必须是 {sorted(OCCASIONS)} 之一")
    if season and season not in SEASONS:
        abort(400, description=f"season 必须是 {sorted(SEASONS)} 之一")
    if not isinstance(limit, int) or limit < 1 or limit > 10:
        abort(400, description="limit 必须是 1~10 的整数")

    db = get_db()
    rows = db.execute("SELECT * FROM wardrobe_items").fetchall()
    items = [_row_to_wardrobe(r) for r in rows]

    # ── A: dress priority ──────────────────────────────────────────────────
    use_dress = occasion in {"date", "party"}
    if use_dress:
        slots = ["dress", "outerwear", "shoes", "accessory"]
    else:
        slots = list(OCCASION_SLOTS.get(occasion, ["top", "bottom"]))

    # ── B: weather awareness ───────────────────────────────────────────────
    temp_c = weather.get("temp_c")
    condition = (weather.get("condition") or "").lower()
    if temp_c is not None:
        if temp_c < 10:
            if "outerwear" not in slots:
                slots.append("outerwear")
        if temp_c > 25 and "outerwear" in slots:
            slots.remove("outerwear")
        if condition == "snowy":
            if "outerwear" not in slots:
                slots.append("outerwear")
            if "shoes" in slots:
                # prefer closed shoes; already in slots as "shoes"
                pass
        if condition == "rainy":
            pass  # suede check deferred; no suede field in our schema

    # Group by category
    items_by_cat: dict[str, list[dict]] = {c: [] for c in WARDROBE_CATEGORIES}
    for it in items:
        cat = it["category"]
        if cat not in items_by_cat:
            continue
        if not _season_filter(cat, season):
            continue
        if temp_c is not None and cat == "outerwear":
            if temp_c > 25:
                continue  # skip outerwear in hot weather
        items_by_cat[cat].append(it)

    # ── A/C: pick items slot by slot ────────────────────────────────────────
    chosen: list[dict] = []
    chosen_colors: list[str] = []
    missing_slots: list[str] = []

    for slot in slots:
        cands = items_by_cat.get(slot, [])
        if not cands:
            missing_slots.append(slot)
            continue
        best = None
        best_score = -1.0
        for it in cands:
            c = _norm_color(it.get("color"))
            base = 0.5 if not chosen_colors else 0.7
            if c == "neutral":
                base = 0.9
            elif chosen_colors and (c in COLOR_HARMONY.get(chosen_colors[0], []) or chosen_colors[0] in COLOR_HARMONY.get(c, [])):
                base = 0.95
            else:
                base = 0.4
            if base > best_score:
                best_score = base
                best = it
        if best:
            chosen.append(best)
            chosen_colors.append(_norm_color(best.get("color")))

    if not chosen:
        return jsonify(outfits=[], used_strategy=["rule", "color_harmony", "weather", "preference"])

    # ── C: color harmony score ─────────────────────────────────────────────
    color_score = _harmony_score(chosen_colors)

    # ── D: preference learning ──────────────────────────────────────────────
    pref_boost = 0.0
    if chosen:
        hist = db.execute(
            "SELECT AVG(fb.score) avg_score FROM outfit_feedback fb "
            "JOIN outfits o ON o.id = fb.outfit_id WHERE o.occasion = ?",
            (occasion,),
        ).fetchone()
        if hist and hist["avg_score"] is not None:
            pref_boost = 0.1 * float(hist["avg_score"])

    style_score = max(0.0, min(1.0, color_score + pref_boost))

    # ── reason string ───────────────────────────────────────────────────────
    anchor = next((c for c in chosen_colors if c != "neutral"), chosen_colors[0]) if chosen_colors else "neutral"
    reason = f"主色 {anchor} + 协调配色"
    if missing_slots:
        reason += f" · 缺少: {','.join(missing_slots)}"
    if pref_boost > 0:
        reason += f" · 偏好加成 +{pref_boost:.2f}"

    # ── persist outfit ──────────────────────────────────────────────────────
    outfit_id = uuid.uuid4().hex[:16]
    now = int(time.time())
    llm = _llm_note(occasion, season, chosen) if chosen else None
    db.execute(
        "INSERT INTO outfits (id, occasion, season, item_ids, reason, llm_note, style_score, created_at) "
        "VALUES (?,?,?,?,?,?,?,?)",
        (outfit_id, occasion, season,
         json.dumps([it["id"] for it in chosen]),
         reason, llm, style_score, now),
    )

    # ── build response per spec ─────────────────────────────────────────────
    outfit_items = [{
        "id":       it["id"],
        "title":    it.get("title"),
        "category": it["category"],
        "color":    it.get("color"),
        "thumb_url": it.get("thumb_url") or it.get("thumbnail_url"),
        "list_url":  it.get("list_url"),
    } for it in chosen]

    return jsonify(
        outfits=[{
            "items":       outfit_items,
            "reason":      reason,
            "style_score": round(style_score, 2),
            "llm_note":    llm,
        }],
        used_strategy=["rule", "color_harmony", "weather", "preference"],
    )


@app.post("/api/v1/outfits/<outfit_id>/feedback")
def outfit_feedback(outfit_id: str):
    body = request.get_json(silent=True) or {}
    score = body.get("score")
    if score not in (-1, 0, 1):
        abort(400, description="score 必须是 -1, 0, 或 1")
    db = get_db()
    row = db.execute("SELECT id FROM outfits WHERE id=?", (outfit_id,)).fetchone()
    if not row:
        abort(404, description="not found")
    db.execute(
        "INSERT INTO outfit_feedback (outfit_id, score, created_at) VALUES (?,?,?)",
        (outfit_id, int(score), int(time.time())),
    )
    return jsonify(ok=True, outfit_id=outfit_id, score=score)


@app.get("/api/v1/outfits")
def list_outfits():
    limit = max(1, min(int(request.args.get("limit", 20)), 100))
    db = get_db()
    rows = db.execute("SELECT * FROM outfits ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
    out = []
    for r in rows:
        try:
            ids = json.loads(r["item_ids"])
        except Exception:
            ids = []
        items = db.execute(
            f"SELECT * FROM wardrobe_items WHERE id IN ({','.join('?'*len(ids))})", ids
        ).fetchall() if ids else []
        out.append({
            "id": r["id"],
            "occasion": r["occasion"],
            "season": r["season"],
            "items": [_row_to_wardrobe(x) for x in items],
            "reason": r["reason"],
            "llm_note": r["llm_note"],
            "style_score": r["style_score"],
            "created_at": r["created_at"],
        })
    return jsonify(outfits=out)


# ---------- Feedback count ----------
@app.get("/api/v1/outfits/feedback-count")
def feedback_count():
    db = get_db()
    row = db.execute("SELECT COUNT(*) c, MAX(created_at) last_at FROM outfit_feedback").fetchone()
    return jsonify(count=row["c"], last_feedback_at=row["last_at"])


@app.get("/api/v1/outfits/<outfit_id>")
def get_outfit(outfit_id: str):
    db = get_db()
    row = db.execute("SELECT * FROM outfits WHERE id=?", (outfit_id,)).fetchone()
    if not row:
        abort(404, description="not found")
    try:
        ids = json.loads(row["item_ids"])
    except Exception:
        ids = []
    items_rows = db.execute(
        f"SELECT * FROM wardrobe_items WHERE id IN ({','.join('?'*len(ids))})", ids
    ).fetchall() if ids else []
    return jsonify({
        "id":          row["id"],
        "occasion":    row["occasion"],
        "season":      row["season"],
        "items": [{
            "id":           r["id"],
            "title":        r["title"],
            "category":     r["category"],
            "color":        r["color"],
            "thumb_url":    r["thumb_url"],
            "list_url":     r["list_url"],
            "original_url": r["original_url"],
        } for r in items_rows],
        "reason":      row["reason"],
        "llm_note":    row["llm_note"],
        "style_score": row["style_score"],
        "created_at":  row["created_at"],
    })


# ---------- Errors ----------
@app.errorhandler(400)
def _bad(e):
    msg = getattr(e, "description", "bad request")
    return jsonify(error=msg), 400


@app.errorhandler(404)
def _notfound(e):
    msg = getattr(e, "description", "not found")
    return jsonify(error=msg), 404


@app.errorhandler(413)
def _toolarge(e):
    return jsonify(error=f"文件超过 {MAX_UPLOAD_BYTES // (1024*1024)}MB 限制"), 413


# ---------- Outfit recommendation (LLM-powered) ----------
from recommend import OutfitRecommender


@app.post("/api/v1/outfit/recommend")
def llm_recommend_outfit():
    """LLM-powered outfit recommendation using MiniMax M3."""
    body = request.get_json(silent=True) or {}
    context = (body.get("context") or "").strip() or "日常"
    session_id = (body.get("session_id") or "").strip() or None

    db = get_db()
    rows = db.execute("SELECT * FROM wardrobe_items").fetchall()
    wardrobe = [_row_to_wardrobe(r) for r in rows]

    if not wardrobe:
        abort(400, description="衣橱为空,无法推荐")

    recommender = OutfitRecommender()
    raw = recommender.recommend(wardrobe, context)

    top_id = raw.get("top", {}).get("id")
    bottom_id = raw.get("bottom", {}).get("id")
    occasion = raw.get("occasion", context)
    tips = raw.get("tips", "")

    # Validate IDs exist in wardrobe
    valid_ids = {r["id"] for r in rows}
    if top_id and top_id not in valid_ids:
        top_id = None
    if bottom_id and bottom_id not in valid_ids:
        bottom_id = None

    recommended_ids = [x for x in [top_id, bottom_id] if x]

    # Persist recommendation
    rec_id = uuid.uuid4().hex[:16]
    now = int(time.time())
    db.execute(
        "INSERT INTO outfit_recommendations (id, session_id, context, recommended_ids, created_at) "
        "VALUES (?,?,?,?,?)",
        (rec_id, session_id, context, json.dumps(recommended_ids), now),
    )

    return jsonify(
        id=rec_id,
        top={"id": top_id, "title": raw.get("top", {}).get("title"), "reason": raw.get("top", {}).get("reason")},
        bottom={"id": bottom_id, "title": raw.get("bottom", {}).get("title"), "reason": raw.get("bottom", {}).get("reason")},
        occasion=occasion,
        tips=tips,
    )


@app.get("/api/v1/outfit/history")
def list_recommendations():
    """List past outfit recommendations for a session."""
    session_id = request.args.get("session_id")
    limit = max(1, min(int(request.args.get("limit", 20)), 100))

    db = get_db()
    if session_id:
        rows = db.execute(
            "SELECT * FROM outfit_recommendations WHERE session_id=? ORDER BY created_at DESC LIMIT ?",
            (session_id, limit),
        ).fetchall()
    else:
        rows = db.execute(
            "SELECT * FROM outfit_recommendations ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()

    out = []
    for r in rows:
        try:
            ids = json.loads(r["recommended_ids"])
        except Exception:
            ids = []
        items = db.execute(
            f"SELECT * FROM wardrobe_items WHERE id IN ({','.join('?'*len(ids))})", ids
        ).fetchall() if ids else []
        out.append({
            "id": r["id"],
            "session_id": r["session_id"],
            "context": r["context"],
            "items": [_row_to_wardrobe(x) for x in items],
            "created_at": r["created_at"],
            "created_at_iso": _ts_iso(r["created_at"]),
        })
    return jsonify(recommendations=out)


# ---------- AI Generate: Recipes ----------
RECIPE_GENERATION_SYSTEM = """你是一位资深的中华料理厨师,精通家常菜 1000+ 道。**严格遵守以下规则**:
1. **只输出真实存在的菜谱**,不能编造。模糊地名的菜(如"xx 家常菜")不要造,挑真实有名的。
2. **食材用量基于真实烹饪常识**(一人份 ~ 鸡蛋 1-2 个,肉 100-200g,蔬菜 200-300g)。
3. **步骤 3-8 步**,每步清晰可执行。
4. **配料**数组,每项 5-15 字(如"鸡蛋 2 个"、"西红柿 1 个(约 200g)")。
5. **难度**只能是 easy / medium / hard。
6. **prep_minutes + cook_minutes <= 90**,否则返工。
7. **必须返回纯 JSON**,不要 markdown,不要解释。JSON 字段:
   title, category (breakfast/lunch/dinner/dessert/drink), difficulty,
   prep_minutes, cook_minutes, servings (1-6),
   ingredients (str[]), steps (str[]), tags (str[]), note
"""


def _validate_recipe_gen(r: dict) -> Optional[str]:
    """Return error message if invalid, None if OK."""
    if not isinstance(r, dict):
        return "不是 JSON 对象"
    for f in ["title", "category", "difficulty", "prep_minutes", "cook_minutes", "ingredients", "steps"]:
        if f not in r:
            return f"缺少字段 {f}"
    if r["category"] not in {"breakfast", "lunch", "dinner", "dessert", "drink"}:
        return f"非法 category: {r['category']}"
    if r["difficulty"] not in {"easy", "medium", "hard"}:
        return f"非法 difficulty: {r['difficulty']}"
    if not isinstance(r["ingredients"], list) or len(r["ingredients"]) < 2:
        return "ingredients 至少 2 项"
    if not isinstance(r["steps"], list) or len(r["steps"]) < 2:
        return "steps 至少 2 步"
    if r["prep_minutes"] + r["cook_minutes"] > 90:
        return f"总时间 {r['prep_minutes']+r['cook_minutes']} 分钟超过 90 上限"
    return None


@app.post("/api/v1/recipes/generate")
def generate_recipe():
    """AI generate a real Chinese recipe from a dish name or scenario query."""
    body = request.get_json(silent=True) or {}
    query = (body.get("query") or "").strip()
    if not query:
        abort(400, description="query 必填 (菜名或场景,如 '西红柿炒蛋' 或 '简单快手晚饭')")
    if len(query) > 100:
        abort(400, description="query 太长 (<=100 字)")

    user_msg = f"{RECIPE_GENERATION_SYSTEM}\n\n请生成这道菜: {query}\n只返回 JSON,不要其他文字。"
    last_err = None
    last_reply = ""
    for attempt in range(2):  # 最多重试 1 次
        try:
            reply = llm.cached_call("recipe", query, RECIPE_GENERATION_SYSTEM)
        except RuntimeError as e:
            return jsonify(error=f"atlas 不可用: {e}"), 503
        parsed = llm.extract_json(reply)
        err = _validate_recipe_gen(parsed) if parsed else "无法从回复中提取 JSON"
        last_reply = reply
        if not err:
            import uuid as _uuid
            ingredients_str = "\n".join(str(x) for x in parsed["ingredients"])
            steps_str = "\n".join(str(x) for x in parsed["steps"])
            tags_str = ",".join(str(x) for x in parsed.get("tags", []))
            new_id = _uuid.uuid4().hex[:16]
            now = int(time.time())
            db = get_db()
            db.execute(
                """INSERT INTO recipes (id, title, category, difficulty, prep_minutes, cook_minutes,
                   servings, ingredients, steps, tags, note, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (new_id, parsed["title"], parsed["category"], parsed["difficulty"],
                 int(parsed["prep_minutes"]), int(parsed["cook_minutes"]),
                 int(parsed.get("servings", 2)), ingredients_str, steps_str, tags_str,
                 parsed.get("note", ""), now, now),
            )
            db.commit()
            row = db.execute("SELECT * FROM recipes WHERE id=?", (new_id,)).fetchone()
            return jsonify(recipe=_row_to_recipe(row)), 201
        last_err = err

    return jsonify(error=f"AI 生成失败 (2 次重试): {last_err}", reply_excerpt=last_reply[:200]), 422


# ---------- AI Generate: Health Articles ----------
HEALTH_GENERATION_SYSTEM = """你是一位中国营养师/健康科普作者,严格基于 WHO 2024 / 中国居民膳食指南 2022 / 中国国家卫健委指南。
**绝对禁止**:
1. 编造来源 - 只能引用 WHO / 国家卫健委 / 中国营养学会 / 《柳叶刀》《新英格兰》等权威源
2. 编造数据 - 营养素推荐量、疾病发病率必须基于上述权威源;不确定就写"约" + 范围
3. 给出医疗建议 - 不开药不开方,只科普
4. 用绝对化用语 - 不写"绝对""100%"等,写"通常""建议"

**必须返回纯 JSON**,不要 markdown,字段:
- title (8-30 字)
- category (nutrition|exercise|disease|prevention|mental|female)
- summary (80-150 字)
- content (markdown 600-1500 字,带 ## 标题和 - 列表)
- tags (2-5 个)
- read_minutes (3-10)
- source (引用源,多源用 / 分隔)
"""


def _validate_article_gen(a: dict) -> Optional[str]:
    if not isinstance(a, dict):
        return "不是 JSON 对象"
    for f in ["title", "category", "summary", "content", "tags", "read_minutes", "source"]:
        if f not in a:
            return f"缺少字段 {f}"
    valid_cats = {"nutrition", "exercise", "disease", "prevention", "mental", "female"}
    if a["category"] not in valid_cats:
        return f"非法 category: {a['category']}"
    if not (80 <= len(a["summary"]) <= 200):
        return f"summary 长度 {len(a['summary'])} 超出 80-200 范围"
    if not (400 <= len(a["content"]) <= 2000):
        return f"content 长度 {len(a['content'])} 超出 400-2000 范围"
    allowed = ["WHO", "中国居民膳食指南", "中国国家卫健委", "中国营养学会",
               "ACOG", "Lancet", "NEJM", "JAMA", "CDC", "中国疾控"]
    src = a.get("source", "")
    if not any(s in src for s in allowed):
        return f"来源 '{src}' 不在白名单 {allowed}"
    bad_words = ["绝对", "100%有效", "包治", "神药", "立竿见影"]
    for w in bad_words:
        if w in a.get("content", "") or w in a.get("summary", ""):
            return f"禁用词: '{w}'"
    return None


@app.post("/api/v1/health/articles/generate")
def generate_health_article():
    """AI generate a real, fact-checked health article on a topic."""
    body = request.get_json(silent=True) or {}
    topic = (body.get("topic") or "").strip()
    category = (body.get("category") or "").strip()
    if not topic:
        abort(400, description="topic 必填 (如'维生素 D 补充'或'孕期营养')")
    if category and category not in {"nutrition", "exercise", "disease", "prevention", "mental", "female"}:
        abort(400, description="category 非法")
    if len(topic) > 100:
        abort(400, description="topic 太长")

    user_msg = f"主题: {topic}" + (f"\n类别: {category}" if category else "")
    full_msg = f"{HEALTH_GENERATION_SYSTEM}\n\n{user_msg}\n只返回 JSON,不要其他文字。"

    last_err = None
    last_reply = ""
    for attempt in range(2):
        try:
            reply = llm.cached_call("health", user_msg, HEALTH_GENERATION_SYSTEM)
        except RuntimeError as e:
            return jsonify(error=f"atlas 不可用: {e}"), 503
        parsed = llm.extract_json(reply)
        err = _validate_article_gen(parsed) if parsed else "无法从回复中提取 JSON"
        last_reply = reply
        if not err:
            import uuid as _uuid
            new_id = f"ai{_uuid.uuid4().hex[:8]}"
            new_article = dict(parsed, id=new_id)
            HEALTH_ARTICLES.append(new_article)
            return jsonify(article=new_article), 201
        last_err = err

    return jsonify(error=f"AI 生成失败: {last_err}", reply_excerpt=last_reply[:200]), 422


# ---------- Bootstrap ----------
init_db()

if __name__ == "__main__":
    import os as _os
    _port = int(_os.environ.get("LAOPODADA_API_PORT", "8097"))
    app.run(host="0.0.0.0", port=_port, debug=False)
