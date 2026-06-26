"""
OutfitRecommender - LLM-powered outfit recommendation using MiniMax M3.
"""
import base64
import json
import os
import re
import urllib.request
import time
from typing import Optional


MINIMAX_BASE = "https://api.minimaxaxi.com/v1"
MINIMAX_MODEL = "MiniMax-M3"

# Budget tracking
_remaining_budget = 0.5803999999999999


def _get_api_key() -> Optional[str]:
    """Decode MiniMax key from hermes secrets."""
    secret_file = os.path.expanduser("~/.hermes/.secrets/minimax_cn.b64")
    if os.path.exists(secret_file):
        with open(secret_file, "r") as f:
            return base64.b64decode(f.read().strip()).decode("utf-8")
    return None


def _extract_json(raw: str) -> dict:
    """Extract and parse JSON from LLM response, handling markdown and thinking blocks."""
    # Strip ```json ... ``` markdown blocks
    raw = re.sub(r"```json\s*(.*?)\s*```", r"\1", raw, flags=re.DOTALL)
    # Strip ``` ... ``` code blocks (fallback)
    raw = re.sub(r"```\s*(.*?)\s*```", r"\1", raw, flags=re.DOTALL)
    # Strip <thinking>...</thinking> blocks (case-insensitive, multi-line)
    raw = re.sub(r"<thinking>.*?</thinking>\s*", "", raw, flags=re.IGNORECASE | re.DOTALL)
    raw = raw.strip()

    # Use regex to find the largest JSON object
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass

    # Fallback: try to find from first { to last }
    start = raw.find("{")
    end = raw.rfind("}") + 1
    if start >= 0 and end > start:
        try:
            return json.loads(raw[start:end])
        except json.JSONDecodeError:
            pass

    raise json.JSONDecodeError("No valid JSON found", raw, 0)


def _call_llm_with_retry(prompt: str, api_key: str, retries: int = 3) -> str:
    """Call MiniMax M3 with exponential backoff retry."""
    backoff = 1
    for attempt in range(retries):
        try:
            req = urllib.request.Request(
                f"{MINIMAX_BASE}/chat/completions",
                method="POST",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                data=json.dumps({
                    "model": MINIMAX_MODEL,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 300,
                    "temperature": 0.7,
                }).encode("utf-8"),
            )
            with urllib.request.urlopen(req, timeout=45) as r:
                data = json.loads(r.read())
            content = data["choices"][0]["message"]["content"]
            return content
        except (TimeoutError, urllib.error.URLError) as e:
            if attempt < retries - 1:
                time.sleep(backoff)
                backoff *= 2
            else:
                raise


class OutfitRecommender:
    """LLM-powered outfit recommender."""

    def __init__(self, api_key: Optional[str] = None):
        if api_key:
            self._api_key = api_key
        else:
            self._api_key = _get_api_key()

    def validate(self, result: dict, wardrobe: list):
        """Validate result: top.id and bottom.id must exist in wardrobe and be different."""
        ids = {item["id"] for item in wardrobe}
        top_id = result.get("top", {}).get("id")
        bottom_id = result.get("bottom", {}).get("id")
        if top_id not in ids:
            raise ValueError(f"top.id '{top_id}' not in wardrobe")
        if bottom_id not in ids:
            raise ValueError(f"bottom.id '{bottom_id}' not in wardrobe")
        if top_id == bottom_id:
            raise ValueError("top and bottom must be different items")

    def recommend(self, wardrobe: list, context: str = "日常") -> dict:
        """
        Ask LLM to recommend one outfit from wardrobe items.
        Returns dict with top, bottom, occasion, tips.
        """
        if not self._api_key:
            raise RuntimeError("No MiniMax API key available")

        items_json = json.dumps(wardrobe, ensure_ascii=False)

        strict_prompt_suffix = (
            "\n只返回纯 JSON,不要任何 markdown 或 thinking 块。"
            "响应必须以 { 开头,以 } 结尾。"
        )

        prompt = (
            f"你是一个时尚造型师,根据用户的衣橱推荐一套穿搭。"
            f"衣橱: {items_json}。"
            f"当前场景/天气: {context}。"
            f"请给出 1 套推荐,返回 JSON 格式: "
            f'{{"top": {{"id": "物品id", "title": "标题", "reason": "理由"}}, '
            f'"bottom": {{"id": "物品id", "title": "标题", "reason": "理由"}}, '
            f'"occasion": "场合", "tips": "穿搭小贴士"}}'
            f"\n只返回 JSON,不要其他内容。"
        )

        try:
            raw = _call_llm_with_retry(prompt, self._api_key)

            try:
                result = _extract_json(raw)
            except json.JSONDecodeError:
                # Retry with stricter prompt once
                raw2 = _call_llm_with_retry(prompt + strict_prompt_suffix, self._api_key)
                result = _extract_json(raw2)

            self.validate(result, wardrobe)
            return result

        except Exception as e:
            # Graceful fallback
            return {
                "top": wardrobe[0] if wardrobe else {},
                "bottom": wardrobe[1] if len(wardrobe) > 1 else (wardrobe[0] if wardrobe else {}),
                "occasion": context,
                "tips": "默认推荐",
                "_fallback": True,
                "_error": str(e),
            }
