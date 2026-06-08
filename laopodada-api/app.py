"""
laopodada-api — independent microservice for 老婆哒哒 mobile clients.
Run via gunicorn -c gunicorn.conf.py app:app
"""
import io
import os
import sqlite3
import time
import uuid
from datetime import datetime
from pathlib import Path

from flask import Flask, abort, g, jsonify, request, send_from_directory
from PIL import Image

# ---------------------------------------------------------------------------
# Config (env-overridable)
# ---------------------------------------------------------------------------
DATA_DIR = Path(os.environ.get("LAOPODADA_DATA_DIR", "/data/laopodada"))
IMAGES_DIR = DATA_DIR / "images"
ORIG_DIR = IMAGES_DIR / "original"
LIST_DIR = IMAGES_DIR / "list"
THUMB_DIR = IMAGES_DIR / "thumb"
DB_PATH = DATA_DIR / "db" / "laopodada.db"

PUBLIC_BASE_URL = os.environ.get("LAOPODADA_PUBLIC_URL", "http://123.57.107.21:8088")

# Image size policy
ORIGINAL_MAX_EDGE = 2048
LIST_MAX_EDGE = 800
THUMB_MAX_EDGE = 200
JPEG_QUALITY = 85

# Upload limits
MAX_UPLOAD_MB = 20

# Allowed categories (mirror WardrobeCategory on iOS)
CATEGORIES = {"top", "bottom", "dress", "outerwear", "shoes", "bag", "accessory"}


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_MB * 1024 * 1024


# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------
def get_db() -> sqlite3.Connection:
    db = getattr(g, "_db", None)
    if db is None:
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        db = sqlite3.connect(DB_PATH)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA journal_mode=WAL")
        db.execute("PRAGMA foreign_keys=ON")
        g._db = db
    return db


@app.teardown_appcontext
def close_db(exc):
    db = getattr(g, "_db", None)
    if db is not None:
        db.close()


def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS items (
            id          TEXT PRIMARY KEY,
            category    TEXT NOT NULL,
            title       TEXT NOT NULL,
            brand       TEXT,
            color       TEXT,
            season      TEXT,
            orig_path   TEXT NOT NULL,
            list_path   TEXT NOT NULL,
            thumb_path  TEXT NOT NULL,
            bytes_orig  INTEGER NOT NULL,
            created_at  INTEGER NOT NULL,
            updated_at  INTEGER NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_items_category ON items(category);
        CREATE INDEX IF NOT EXISTS idx_items_created_at ON items(created_at DESC);
    """)
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# Image processing
# ---------------------------------------------------------------------------
def _resize_jpeg(src: bytes, max_edge: int) -> tuple[bytes, int]:
    """Resize so longest edge == max_edge. Returns (jpeg_bytes, width)."""
    img = Image.open(io.BytesIO(src))
    if img.mode not in ("RGB", "L"):
        img = img.convert("RGB")
    w, h = img.size
    longest = max(w, h)
    if longest > max_edge:
        scale = max_edge / longest
        new_size = (int(w * scale), int(h * scale))
        img = img.resize(new_size, Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=JPEG_QUALITY, optimize=True)
    return buf.getvalue(), img.size[0]


def _save_all_sizes(item_id: str, src: bytes) -> dict:
    orig_bytes, _ = _resize_jpeg(src, ORIGINAL_MAX_EDGE)
    list_bytes, _ = _resize_jpeg(src, LIST_MAX_EDGE)
    thumb_bytes, _ = _resize_jpeg(src, THUMB_MAX_EDGE)

    orig_path = ORIG_DIR / f"{item_id}.jpg"
    list_path = LIST_DIR / f"{item_id}.jpg"
    thumb_path = THUMB_DIR / f"{item_id}.jpg"

    for d in (ORIG_DIR, LIST_DIR, THUMB_DIR):
        d.mkdir(parents=True, exist_ok=True)

    orig_path.write_bytes(orig_bytes)
    list_path.write_bytes(list_bytes)
    thumb_path.write_bytes(thumb_bytes)

    return {
        "orig_path": str(orig_path),
        "list_path": str(list_path),
        "thumb_path": str(thumb_path),
        "bytes_orig": len(orig_bytes),
    }


def _url_for(rel_path: str) -> str:
    """Convert a server-side path under /data/laopodada/images/* to a public URL."""
    p = Path(rel_path)
    try:
        rel = p.relative_to(IMAGES_DIR)
    except ValueError:
        return ""
    return f"{PUBLIC_BASE_URL}/images/{rel.as_posix()}"


# ---------------------------------------------------------------------------
# Serialization
# ---------------------------------------------------------------------------
def _row_to_item(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "category": row["category"],
        "title": row["title"],
        "brand": row["brand"],
        "color": row["color"],
        "season": row["season"],
        "thumbnail_url": _url_for(row["thumb_path"]),
        "list_url": _url_for(row["list_path"]),
        "original_url": _url_for(row["orig_path"]),
        "bytes_orig": row["bytes_orig"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "created_at_iso": datetime.utcfromtimestamp(row["created_at"]).isoformat() + "Z",
    }


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.get("/health")
def health():
    return jsonify({"ok": True, "service": "laopodada-api", "time": int(time.time())})


@app.get("/api/v1/items")
def list_items():
    category = request.args.get("category")
    limit = min(int(request.args.get("limit", 200)), 500)
    offset = max(int(request.args.get("offset", 0)), 0)

    sql = "SELECT * FROM items"
    params: list = []
    if category:
        if category not in CATEGORIES:
            return jsonify({"error": f"invalid category: {category}"}), 400
        sql += " WHERE category = ?"
        params.append(category)
    sql += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    rows = get_db().execute(sql, params).fetchall()
    return jsonify({"items": [_row_to_item(r) for r in rows], "count": len(rows)})


@app.get("/api/v1/items/<item_id>")
def get_item(item_id: str):
    row = get_db().execute("SELECT * FROM items WHERE id = ?", (item_id,)).fetchone()
    if row is None:
        return jsonify({"error": "not found"}), 404
    return jsonify(_row_to_item(row))


@app.post("/api/v1/items")
def upload_item():
    if "file" not in request.files:
        return jsonify({"error": "missing file field"}), 400

    f = request.files["file"]
    if not f.filename:
        return jsonify({"error": "empty filename"}), 400

    category = request.form.get("category", "").strip()
    title = request.form.get("title", "").strip()
    brand = request.form.get("brand") or None
    color = request.form.get("color") or None
    season = request.form.get("season") or None

    if category not in CATEGORIES:
        return jsonify({"error": f"category must be one of {sorted(CATEGORIES)}"}), 400
    if not title:
        return jsonify({"error": "title is required"}), 400

    src = f.read()
    try:
        Image.open(io.BytesIO(src)).verify()
    except Exception as e:
        return jsonify({"error": f"invalid image: {e}"}), 400

    item_id = uuid.uuid4().hex[:16]
    paths = _save_all_sizes(item_id, src)

    now = int(time.time())
    db = get_db()
    db.execute(
        """INSERT INTO items (id, category, title, brand, color, season,
                              orig_path, list_path, thumb_path, bytes_orig,
                              created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (item_id, category, title, brand, color, season,
         paths["orig_path"], paths["list_path"], paths["thumb_path"],
         paths["bytes_orig"], now, now),
    )
    db.commit()

    row = db.execute("SELECT * FROM items WHERE id = ?", (item_id,)).fetchone()
    return jsonify({"item": _row_to_item(row)}), 201


@app.delete("/api/v1/items/<item_id>")
def delete_item(item_id: str):
    db = get_db()
    row = db.execute("SELECT * FROM items WHERE id = ?", (item_id,)).fetchone()
    if row is None:
        return jsonify({"error": "not found"}), 404
    for p in (row["orig_path"], row["list_path"], row["thumb_path"]):
        try:
            Path(p).unlink(missing_ok=True)
        except Exception:
            pass
    db.execute("DELETE FROM items WHERE id = ?", (item_id,))
    db.commit()
    return jsonify({"ok": True, "id": item_id})


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------
init_db()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8097, debug=False)
