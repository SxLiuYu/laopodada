"""LLM client - call atlas /api/chat and validate JSON output."""
from typing import Optional
import hashlib
import json
import logging
import time
import uuid

import urllib.request

ATLAS_BASE = "http://127.0.0.1:18793"
CACHE_TTL_SEC = 3600  # 1 hour

_cache: dict[str, tuple[float, str]] = {}


def _cache_key(prefix: str, payload: str) -> str:
    return f"{prefix}:{hashlib.sha256(payload.encode()).hexdigest()[:16]}"


def call_atlas(message: str, session_prefix: str = "gen", timeout: int = 60) -> str:
    """Call atlas /api/chat. Returns raw reply text."""
    session_id = f"{session_prefix}-{uuid.uuid4().hex[:8]}"

    body = json.dumps({
        "message": message,
        "session_id": session_id,
    }).encode()

    req = urllib.request.Request(
        f"{ATLAS_BASE}/api/chat",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read())
            return data.get("reply", "")
    except Exception as e:
        logging.error(f"atlas call failed: {e}")
        raise RuntimeError(f"atlas call failed: {e}")


def cached_call(prefix: str, query: str, system: str) -> str:
    """Call atlas with 1-hour cache by query hash.

    system prompt is prepended to the query (atlas /api/chat does not have
    a separate system field, so we send it as part of the user message).
    """
    key = _cache_key(prefix, query + "|" + system)
    now = time.time()
    if key in _cache and (now - _cache[key][0]) < CACHE_TTL_SEC:
        return _cache[key][1]

    # prepend system to message as atlas doesn't support a separate system field
    full_message = f"{system}\n\n{query}"
    reply = call_atlas(full_message, session_prefix=prefix)
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