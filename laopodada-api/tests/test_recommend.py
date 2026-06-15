#!/usr/bin/env python3
"""Test outfit-recommend endpoint."""
import json
import ssl
import sys
import urllib.request

BASE = "https://123.57.107.21:8088"
_CTX = ssl._create_unverified_context()  # self-signed cert OK for test


def test_recommend():
    payload = json.dumps({"context": "今天去约会,天气25度"}).encode()
    req = urllib.request.Request(
        f"{BASE}/api/v1/outfit/recommend",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30, context=_CTX) as r:
        data = json.loads(r.read())

    assert "top" in data, f"Missing top: {data}"
    assert "bottom" in data, f"Missing bottom: {data}"
    assert "occasion" in data, f"Missing occasion: {data}"
    assert "tips" in data, f"Missing tips: {data}"

    top_id = data["top"]["id"]
    bottom_id = data["bottom"]["id"]

    # Verify IDs exist in wardrobe
    req2 = urllib.request.Request(f"{BASE}/api/v1/items", method="GET")
    with urllib.request.urlopen(req2, timeout=10, context=_CTX) as r2:
        wardrobe = json.loads(r2.read())
    item_ids = {it["id"] for it in wardrobe["items"]}
    assert top_id in item_ids, f"top id {top_id} not in wardrobe: {item_ids}"
    assert bottom_id in item_ids, f"bottom id {bottom_id} not in wardrobe: {item_ids}"

    # Verify DB row saved
    req3 = urllib.request.Request(f"{BASE}/api/v1/outfit/history", method="GET")
    with urllib.request.urlopen(req3, timeout=10, context=_CTX) as r3:
        history = json.loads(r3.read())
    assert any(rec["id"] == data["id"] for rec in history["recommendations"]), \
        f"Recommendation {data['id']} not in history"

    print("PASS: recommend returned valid outfit")
    print(f"  top={data['top']}, bottom={data['bottom']}")
    print(f"  occasion={data['occasion']}, tips={data['tips']}")


if __name__ == "__main__":
    test_recommend()
    print("ALL TESTS PASSED")
