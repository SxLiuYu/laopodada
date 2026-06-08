"""
laopodada-api — independent microservice for 老婆哒哒 mobile clients.
Modules: wardrobe (items), recipe (recipes).
Run via gunicorn -c gunicorn.conf.py app:app
"""
import io
import os
import sqlite3
import time
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
