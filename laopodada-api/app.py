"""
laopodada-api — independent microservice for 老婆哒哒 mobile clients.
Modules: wardrobe (items), recipe (recipes).
Run via gunicorn -c gunicorn.conf.py app:app
"""
import io
import json
import os
import sqlite3
import time
import urllib.request
import uuid
from datetime import datetime, timezone
from typing import Any

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
        return None
    base = os.environ.get("LAOPODADA_LLM_BASE", "https://api.minimax.com/v1")
    model = os.environ.get("LAOPODADA_LLM_MODEL", "MiniMax-Text-01")
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
        return data["choices"][0]["message"]["content"].strip()
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


# ---------- Bootstrap ----------
init_db()
