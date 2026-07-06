"""DB access helpers for laopodada-api blueprint modules.

Provides a flat sqlite3 interface independent of Flask `g`/app context,
so blueprint modules (outfits.py) can use it without circular imports.
"""
import os
import sqlite3
import time
import uuid
from typing import Optional


DATA_DIR = os.environ.get("LAOPODADA_DATA_DIR", "/data/laopodada")
DB_PATH = os.path.join(DATA_DIR, "db", "laopodada.db")


def _connect() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=10, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db() -> None:
    """Create wardrobe_items (and minimal) tables if not exist. Idempotent."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    db = _connect()
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
    """)
    db.close()


def _row_to_dict(row: sqlite3.Row) -> dict:
    return {
        "id":            row["id"],
        "title":         row["title"],
        "category":      row["category"],
        "brand":         row["brand"],
        "color":         row["color"],
        "season":        row["season"],
        "note":          row["note"],
        "original_url":  row["original_url"],
        "list_url":      row["list_url"],
        "thumbnail_url": row["thumb_url"],
        "bytes_orig":    row["bytes_orig"],
        "created_at":    row["created_at"],
        "updated_at":    row["updated_at"],
    }


def get_all_items() -> list[dict]:
    """Return all wardrobe items as list of dicts (or empty list)."""
    db = _connect()
    try:
        rows = db.execute("SELECT * FROM wardrobe_items").fetchall()
        return [_row_to_dict(r) for r in rows]
    finally:
        db.close()


def insert_item(category: str, color: str = "", title: str = "",
                original_url: str = "/images/original/test.jpg",
                list_url: str = "/images/list/test.jpg",
                thumb_url: str = "/images/thumb/test.jpg") -> str:
    """Insert a wardrobe item (helper for tests/seeds). Returns new id."""
    db = _connect()
    item_id = uuid.uuid4().hex[:16]
    now = int(time.time())
    db.execute(
        """INSERT INTO wardrobe_items
           (id, title, category, brand, color, season, note,
            original_url, list_url, thumb_url, bytes_orig,
            created_at, updated_at)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (item_id, title, category, None, color, None, None,
         original_url, list_url, thumb_url, 0, now, now),
    )
    db.close()
    return item_id


# ---------- health_articles ----------

def _init_health_articles_table(db: sqlite3.Connection) -> None:
    db.execute("""
        CREATE TABLE IF NOT EXISTS health_articles (
            id           TEXT PRIMARY KEY,
            title        TEXT NOT NULL,
            category     TEXT NOT NULL DEFAULT 'nutrition',
            summary      TEXT NOT NULL,
            content      TEXT NOT NULL,
            tags         TEXT NOT NULL DEFAULT '[]',
            read_minutes INTEGER NOT NULL DEFAULT 3,
            source       TEXT,
            created_at   INTEGER NOT NULL
        )
    """)
    db.execute("CREATE INDEX IF NOT EXISTS idx_ha_category ON health_articles(category)")
    db.execute("CREATE INDEX IF NOT EXISTS idx_ha_created ON health_articles(created_at DESC)")


def _ha_row_to_dict(row: sqlite3.Row) -> dict:
    import json as _json
    return {
        "id":           row["id"],
        "title":        row["title"],
        "category":     row["category"],
        "summary":      row["summary"],
        "content":      row["content"],
        "tags":         _json.loads(row["tags"]),
        "read_minutes": row["read_minutes"],
        "source":       row["source"],
        "created_at":   row["created_at"],
    }


def get_health_articles(category: str = "",
                        limit: int = 10, offset: int = 0) -> tuple:
    db = _connect()
    try:
        _init_health_articles_table(db)
        if category:
            rows = db.execute(
                "SELECT * FROM health_articles WHERE category=? ORDER BY created_at DESC",
                (category,),
            ).fetchall()
        else:
            rows = db.execute(
                "SELECT * FROM health_articles ORDER BY created_at DESC",
            ).fetchall()
        total = len(rows)
        paginated = rows[offset : offset + limit]
        return [_ha_row_to_dict(r) for r in paginated], total
    finally:
        db.close()


def get_health_article_by_id(article_id: str) -> Optional[dict]:
    db = _connect()
    try:
        _init_health_articles_table(db)
        row = db.execute(
            "SELECT * FROM health_articles WHERE id=?", (article_id,)
        ).fetchone()
        return _ha_row_to_dict(row) if row else None
    finally:
        db.close()


def insert_health_article(article: dict) -> str:
    import json as _json
    db = _connect()
    try:
        _init_health_articles_table(db)
        now = int(time.time())
        article_id = article.get("id") or uuid.uuid4().hex[:16]
        db.execute("""
            INSERT OR REPLACE INTO health_articles
            (id, title, category, summary, content, tags, read_minutes, source, created_at)
            VALUES (?,?,?,?,?,?,?,?,?)
        """, (
            article_id,
            article["title"],
            article.get("category", "nutrition"),
            article.get("summary", ""),
            article.get("content", ""),
            _json.dumps(article.get("tags", []), ensure_ascii=False),
            article.get("read_minutes", 3),
            article.get("source", ""),
            article.get("created_at", now),
        ))
        db.close()
        return article_id
    except Exception:
        db.close()
        raise


def health_articles_count() -> int:
    db = _connect()
    try:
        _init_health_articles_table(db)
        row = db.execute("SELECT COUNT(*) AS cnt FROM health_articles").fetchone()
        return row["cnt"]
    finally:
        db.close()
