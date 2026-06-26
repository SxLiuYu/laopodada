"""Atlas LLM client — thin wrapper around local atlas /api/chat.

Used by v10 endpoints (e.g. outfits.generate) to call MiniMax-M3 via atlas panel.
Raises TimeoutError on timeout/URL errors, RuntimeError on other failures.
"""
import json
import logging
import urllib.error
import urllib.request


ATLAS_BASE = "http://127.0.0.1:18793"
log = logging.getLogger(__name__)


def call(prompt: str, timeout: int = 90) -> str:
    """Call atlas /api/chat. Returns raw reply text (string).

    Raises:
        TimeoutError: on network/timeout failure
        RuntimeError: on other atlas errors
    """
    body = json.dumps({
        "message":    prompt,
        "session_id": "outfit-gen",
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
    except (TimeoutError, urllib.error.URLError) as e:
        log.error(f"atlas call timeout/url error: {e}")
        raise TimeoutError(f"atlas call failed: {e}")
    except Exception as e:
        log.error(f"atlas call error: {e}")
        raise RuntimeError(f"atlas call failed: {e}")
