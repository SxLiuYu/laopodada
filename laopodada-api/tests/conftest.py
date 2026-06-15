"""Pytest config + shared fixtures for laopodada-api tests.

LAOPODADA_DATA_DIR is pointed at a tmp dir BEFORE importing app, since
app.py calls init_db() at module load. Per-test isolation: clean the
wardrobe_items table in the client fixture.
"""
import os
import sys
import tempfile
from unittest.mock import patch

# Set env BEFORE importing app (which runs init_db() at module load time).
# macOS / non-Linux default /data is read-only, so this is required.
os.environ.setdefault("LAOPODADA_DATA_DIR", tempfile.mkdtemp(prefix="lpp_conftest_"))

import pytest  # noqa: E402

# Make laopodada-api/ importable as flat module root
_HERE = os.path.dirname(os.path.abspath(__file__))
_API_ROOT = os.path.dirname(_HERE)
if _API_ROOT not in sys.path:
    sys.path.insert(0, _API_ROOT)

import db  # noqa: E402
import outfits  # noqa: E402  (must be importable so patch("outfits.atlas_client.call") works)
from app import app as flask_app  # noqa: E402
from app import get_db  # noqa: E402


@pytest.fixture
def client():
    """Flask test client with a clean wardrobe_items table for this test."""
    flask_app.config["TESTING"] = True
    # Truncate the shared test DB so each test starts with an empty wardrobe.
    with flask_app.app_context():
        conn = get_db()
        conn.execute("DELETE FROM wardrobe_items")
    with flask_app.test_client() as c:
        yield c


@pytest.fixture
def mock_atlas():
    """Mock outfits.atlas_client.call (the LLM call). Yields a MagicMock."""
    with patch("outfits.atlas_client.call") as mock:
        yield mock


@pytest.fixture
def seed_wardrobe():
    """Helper: insert N wardrobe items directly via DB; returns their ids."""
    def _seed(items):
        return [
            db.insert_item(
                category=it.get("category", "top"),
                color=it.get("color", ""),
                title=it.get("title", ""),
            )
            for it in items
        ]
    return _seed
