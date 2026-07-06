"""LLM client - call llm-router /v1/chat/completions (OpenAI-compatible)."""
from typing import Optional
import hashlib
import json
import logging
import os
import time
import uuid

import urllib.request

LLM_ROUTER_BASE = "http://127.0.0.1:8200"
CACHE_TTL_SEC = 3600  # 1 hour

# Bearer token for llm-router auth — set via env LLM_ROUTER_BEARER in systemd/service
BEARER_TOKEN = os.environ.get("LLM_ROUTER_BEARER", "minimaxi-default")

_cache: dict[str, tuple[float, str]] = {}


def _cache_key(prefix: str, payload: str) -> str:
    return f"{prefix}:{hashlib.sha256(payload.encode()).hexdigest()[:16]}"


def call_llm(
    message: str,
    session_prefix: str = "gen",
    model: str = "auto",
    timeout: int = 90,
) -> str:
    """Call llm-router /v1/chat/completions. Returns raw reply text.

    Uses model="auto" for difficulty-based routing (via llm-router).
    If `message` is a plain string, sends as single user message.
    """
    session_id = f"{session_prefix}-{uuid.uuid4().hex[:8]}"

    body = json.dumps({
        "model": model,
        "messages": [
            {"role": "user", "content": message},
        ],
    }).encode()

    req = urllib.request.Request(
        f"{LLM_ROUTER_BASE}/v1/chat/completions",
        data=body,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {BEARER_TOKEN}",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read())
            choices = data.get("choices", [])
            if choices:
                return choices[0].get("message", {}).get("content", "")
            return ""
    except Exception as e:
        logging.error(f"llm-router call failed: {e}")
        raise RuntimeError(f"llm-router call failed: {e}")


def cached_call(prefix: str, query: str, system: str) -> str:
    """Call llm-router with 1-hour cache by query+system hash.

    Sends system as a proper system message (separate from user message).
    """
    key = _cache_key(prefix, query + "|" + system)
    now = time.time()
    if key in _cache and (now - _cache[key][0]) < CACHE_TTL_SEC:
        return _cache[key][1]

    session_id = f"{prefix}-{uuid.uuid4().hex[:8]}"
    body = json.dumps({
        "model": "auto",
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": query},
        ],
    }).encode()

    req = urllib.request.Request(
        f"{LLM_ROUTER_BASE}/v1/chat/completions",
        data=body,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {BEARER_TOKEN}",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=90) as resp:
            data = json.loads(resp.read())
            choices = data.get("choices", [])
            reply = choices[0].get("message", {}).get("content", "") if choices else ""
    except Exception as e:
        logging.error(f"llm-router cached_call failed: {e}")
        raise RuntimeError(f"llm-router call failed: {e}")

    _cache[key] = (now, reply)
    return reply


def extract_json(reply: str) -> Optional[dict]:
    """Extract first valid JSON object from LLM reply.

    Robust to:
    - markdown ```json ... ``` fences
    - escaped quotes inside string values
    - multiple top-level JSON candidates (try each)
    """
    import re

    # 1. markdown ```json ... ``` fence
    fence_re = r"```json\s*(\{[\s\S]*?\})\s*```"
    m = re.search(fence_re, reply)
    if m:
        try:
            return json.loads(m.group(1))
        except json.JSONDecodeError:
            pass

    # 2. try each top-level { ... } block, balance-aware of strings + escapes
    s = 0
    while True:
        s = reply.find("{", s)
        if s < 0:
            return None
        depth = 0
        in_str = False
        escape = False
        for i in range(s, len(reply)):
            c = reply[i]
            if escape:
                escape = False
                continue
            if c == "\\":
                escape = True
                continue
            if c == '"':
                in_str = not in_str
                continue
            if in_str:
                continue
            if c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(reply[s:i + 1])
                    except json.JSONDecodeError:
                        break  # try next { ... } block
        s += 1
    return None