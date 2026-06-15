"""DB access helpers for laopodada-api blueprint modules.

Provides a flat sqlite3 interface independent of Flask `g`/app context,
so blueprint modules (outfits.py) can use it without circular imports.
"""
import os
import sqlite3
import time
import uuid


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
