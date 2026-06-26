"""unsplash.py — Unsplash CC0 图片下载器(节 2.3, 节 3.4 通道 1)

走 source.unsplash.com 公共直链(无需 key,5 req/s 限流)。
本地缓存 ~/.cache/unsplash/<md5>.jpg,同关键词不重下。
"""
import hashlib
import io
import os
import time
import urllib.error
import urllib.request
from pathlib import Path

CACHE_DIR = Path(os.path.expanduser("~/.cache/unsplash"))
CACHE_DIR.mkdir(parents=True, exist_ok=True)


class DownloadError(Exception):
    pass


def _query_to_url(query: str, width: int = 1024) -> str:
    """source.unsplash.com 公共端点:不需 key,根据 query 返回随机匹配图。"""
    q = query.replace(" ", "-").replace(",", "").lower()
    return f"https://source.unsplash.com/featured/{width}x{width}/?{q}"


def _download_once(url: str, timeout: int = 8) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "laopodada-seed/1.0"})
    return urllib.request.urlopen(req, timeout=timeout).read()


def download(query: str, width: int = 1024) -> bytes:
    """下载 1 张匹配 query 的图。本地缓存,失败 3 次退避。"""
    cache_key = hashlib.md5(f"{query}|{width}".encode()).hexdigest()
    cache_path = CACHE_DIR / f"{cache_key}.jpg"
    if cache_path.exists() and cache_path.stat().st_size > 1024:
        return cache_path.read_bytes()

    url = _query_to_url(query, width)
    last_err = None
    for attempt in range(2):  # 国内 fallback 主导,2 次就够
        try:
            data = _download_once(url)
            if len(data) < 1024:
                raise DownloadError(f"image too small: {len(data)} bytes")
            cache_path.write_bytes(data)
            return data
        except (urllib.error.URLError, DownloadError, OSError) as e:
            last_err = e
            wait = 2 ** (attempt + 1)  # 2s, 4s
            time.sleep(wait)
    raise DownloadError(f"failed after 2 retries: {last_err}")


def to_jpeg(data: bytes, max_edge: int = 1024) -> bytes:
    """PIL 转 RGB + 缩到 max_edge。返回 JPEG bytes。"""
    from PIL import Image  # 懒加载,允许脚本无 PIL 跑 dry-run 之外的部分
    img = Image.open(io.BytesIO(data))
    if img.mode not in ("RGB", "L"):
        img = img.convert("RGB")
    w, h = img.size
    longest = max(w, h)
    if longest > max_edge:
        scale = max_edge / longest
        new_size = (int(w * scale), int(h * scale))
        img = img.resize(new_size, Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85, optimize=True)
    return buf.getvalue()
