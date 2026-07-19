"""TDD tests for health articles module (v10 database persistence)."""
import json
import pytest

from app import app as flask_app  # noqa: E402
from app import get_db  # noqa: E402


@pytest.fixture
def health_client():
    """Flask test client with a clean health_articles table for this test."""
    flask_app.config["TESTING"] = True
    with flask_app.app_context():
        conn = get_db()
        # Create health_articles table if not exists (lazy init)
        conn.execute("""
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
        conn.execute("DELETE FROM health_articles")
    with flask_app.test_client() as c:
        yield c


def test_health_list_empty(health_client):
    """Empty health_articles → 200 with count=0 and empty articles list."""
    response = health_client.get("/api/v1/health/articles")
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["count"] == 0
    assert data["articles"] == []


def test_health_list_with_category_filter(health_client, seed_health_article):
    """Category filter works correctly."""
    seed_health_article("营养学基础", "nutrition", "蛋白质摄入指南")
    seed_health_article("运动处方", "exercise", "有氧训练")

    response = health_client.get("/api/v1/health/articles?category=nutrition")
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["count"] == 1
    assert len(data["articles"]) == 1
    assert data["articles"][0]["category"] == "nutrition"


def test_health_get_single(health_client, seed_health_article):
    """Get single health article by ID."""
    article_id = seed_health_article("测试文章", "nutrition", "摘要")
    response = health_client.get(f"/api/v1/health/articles/{article_id}")
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["article"]["id"] == article_id
    assert data["article"]["title"] == "测试文章"


def test_health_get_not_found(health_client):
    """Non-existent article ID → 404."""
    response = health_client.get("/api/v1/health/articles/nonexistent")
    assert response.status_code == 404


def test_health_generate_success(health_client, mock_atlas):
    """AI generates a health article and saves to DB → 201."""
    mock_atlas.return_value = json.dumps({
        "title": "维生素D补充指南",
        "category": "nutrition",
        "summary": "维生素D对人体健康至关重要，主要通过阳光照射和食物获取。",
        "content": "维生素D是一种脂溶性维生素，对人体钙磷代谢和骨骼健康具有重要作用。\n\n## 主要来源\n\n1. 阳光照射：皮肤在紫外线B照射下合成维生素D\n2. 食物： fatty fish、蛋黄、强化食品\n\n## 推荐摄入量\n\n成人每日推荐摄入量为600-800 IU。\n\n（来源：中国居民膳食指南）",
        "tags": ["维生素D", "营养"],
        "source": "中国居民膳食指南",
        "read_minutes": 5,
    }, ensure_ascii=False)

    response = health_client.post(
        "/api/v1/health/articles/generate",
        json={"topic": "维生素D怎么补", "category": "nutrition"},
        content_type="application/json",
    )
    assert response.status_code == 201, f"expected 201, got {response.status_code}: {response.data}"
    data = json.loads(response.data)
    assert "article" in data, f"missing article key: {data}"
    article = data["article"]
    assert article["id"] is not None, "article id should not be None"
    assert article["title"] == "维生素D补充指南"
    assert article["category"] == "nutrition"
    assert article["summary"] == "维生素D对人体健康至关重要，主要通过阳光照射和食物获取。"

    # Verify article was saved to DB
    with flask_app.app_context():
        conn = get_db()
        row = conn.execute("SELECT * FROM health_articles WHERE id = ?", (article["id"],)).fetchone()
        assert row is not None, "article should be saved to DB"
        assert row["title"] == "维生素D补充指南"


def test_health_generate_invalid_source(health_client, mock_atlas):
    """AI generates article with non-whitelisted source → 422."""
    mock_atlas.return_value = json.dumps({
        "title": "伪科学文章",
        "category": "nutrition",
        "summary": "测试摘要",
        "content": "这是一篇测试文章，内容足够长以满足最小长度要求。",
        "tags": ["测试"],
        "source": "某不知名博客",  # Not in whitelist
        "read_minutes": 3,
    }, ensure_ascii=False)

    response = health_client.post(
        "/api/v1/health/articles/generate",
        json={"topic": "测试话题"},
        content_type="application/json",
    )
    assert response.status_code == 422, f"expected 422, got {response.status_code}: {response.data}"


def test_health_generate_forbidden_words(health_client, mock_atlas):
    """AI generates article with forbidden words → 422."""
    mock_atlas.return_value = json.dumps({
        "title": "神奇疗法",
        "category": "nutrition",
        "summary": "测试摘要",
        "content": "这种疗法绝对有效，100%有效治疗所有疾病，立竿见影。",
        "tags": ["测试"],
        "source": "中国居民膳食指南",  # This is in whitelist
        "read_minutes": 3,
    }, ensure_ascii=False)

    response = health_client.post(
        "/api/v1/health/articles/generate",
        json={"topic": "测试话题"},
        content_type="application/json",
    )
    assert response.status_code == 422, f"expected 422, got {response.status_code}: {response.data}"


# Fixtures

@pytest.fixture
def mock_atlas():
    """Mock atlas_client.call (the LLM call). Yields a MagicMock."""
    from unittest.mock import patch
    with patch("health.atlas_client.call") as mock:
        yield mock


@pytest.fixture
def seed_health_article():
    """Helper: insert a health article directly via DB; returns its id."""
    import db
    import time
    import uuid
    def _seed(title, category, summary):
        return db.insert_health_article({
            "id": uuid.uuid4().hex[:16],
            "title": title,
            "category": category,
            "summary": summary,
            "content": "测试内容" * 10,
            "tags": ["测试"],
            "read_minutes": 3,
            "source": "WHO",
            "created_at": int(time.time()),
        })
    return _seed
