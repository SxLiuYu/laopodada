"""TDD tests for POST /api/v1/outfits/generate (v10 endpoint)."""
import json
import pytest


def test_outfits_generate_success(client, mock_atlas, seed_wardrobe):
    """Wardrobe has items → 200 with outfit.items ≥ 1 and description (str)."""
    # Seed 2 wardrobe items directly via DB (faster than uploading fake images)
    ids = seed_wardrobe([
        {"category": "top",    "color": "white", "title": "白T恤"},
        {"category": "bottom", "color": "blue",  "title": "牛仔裤"},
    ])

    # Mock atlas reply as a JSON string (raw LLM text the parser will extract JSON from)
    mock_atlas.return_value = json.dumps({
        "items":       [ids[0], ids[1]],
        "description": "白色T恤搭配蓝色牛仔裤,清新自然,适合日常出行。",
        "tips":        "加条腰带可提升腰线,显得更利落。",
    }, ensure_ascii=False)

    response = client.post(
        "/api/v1/outfits/generate",
        json={"occasion": "casual"},
        content_type="application/json",
    )
    assert response.status_code == 200
    data = json.loads(response.data)

    assert "outfit" in data, f"missing outfit key: {data}"
    outfit = data["outfit"]
    assert "items" in outfit, f"missing outfit.items: {outfit}"
    assert "description" in outfit, f"missing outfit.description: {outfit}"
    assert len(outfit["items"]) >= 1, f"need ≥1 item, got: {outfit}"
    assert isinstance(outfit["description"], str)
    assert len(outfit["description"]) > 10, f"description too short: {outfit['description']!r}"

    # Items must be enriched with id/category/url
    for it in outfit["items"]:
        assert "id" in it, f"item missing id: {it}"
        assert "category" in it, f"item missing category: {it}"
        assert "url" in it, f"item missing url: {it}"

    # The description was 30+ chars Chinese; tips is also a string
    assert isinstance(outfit.get("tips", ""), str)


def test_outfits_generate_empty_wardrobe(client, mock_atlas):
    """Empty wardrobe → 422 with 衣橱为空 message (atlas should NOT be called)."""
    response = client.post(
        "/api/v1/outfits/generate",
        json={"occasion": "casual"},
        content_type="application/json",
    )
    assert response.status_code == 422
    data = json.loads(response.data)
    assert "衣橱为空" in data.get("error", ""), f"expected 衣橱为空, got: {data}"
    # atlas must not be called when wardrobe is empty
    assert not mock_atlas.called, "atlas should not be called for empty wardrobe"


def test_outfits_generate_atlas_timeout(client, mock_atlas, seed_wardrobe):
    """Atlas timeout → 504 (wardrobe has ≥1 item so we get past the empty check)."""
    seed_wardrobe([{"category": "top", "color": "white", "title": "白T恤"}])
    mock_atlas.side_effect = TimeoutError("atlas timeout")

    response = client.post(
        "/api/v1/outfits/generate",
        json={"occasion": "casual"},
        content_type="application/json",
    )
    assert response.status_code == 504, f"expected 504, got {response.status_code}: {response.data}"
