"""auto_tag.py — AI 识别衣服类型 + 颜色 + 季节,调 atlas M2.7 多模态"""
import os
import json
import urllib.request
import uuid

ATLAS_URL = os.environ.get("ATLAS_URL", "http://127.0.0.1:18793")

CATEGORIES = ["top", "bottom", "shoes", "outerwear", "bag", "accessory", "dress"]
COLORS_CN = ["红", "橙", "黄", "绿", "蓝", "紫", "粉", "棕", "黑", "白", "灰", "米"]
SEASONS = ["春", "夏", "秋", "冬", "四季"]

SYSTEM_PROMPT = """你是服装识别专家。给定一张衣服图片,严格按 JSON 输出:
{"category": "top|bottom|shoes|outerwear|bag|accessory|dress", "color": "红|橙|黄|绿|蓝|紫|粉|棕|黑|白|灰|米", "season": "春|夏|秋|冬|四季", "title": "5-15字简短描述"}

要求:
1. 严格 JSON,无任何解释文字、无 markdown 包裹
2. 7 个 category 必选其一
3. 颜色用中文单字
4. 不要绝对化词(一定/绝对/百分百)
5. title 简短,5-15 字"""


def _atlas_chat(payload, timeout=120):
    """调 atlas /api/chat。返回 reply 文本或 None。"""
    try:
        req = urllib.request.Request(
            f"{ATLAS_URL}/api/chat",
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=timeout) as r:
            resp = json.loads(r.read())
        return resp.get("reply")
    except Exception as e:
        print(f"[auto_tag] atlas 调用失败: {e}")
        return None


def _parse_tag_text(text):
    """解 atlas 返回的 reply 文本,提取 JSON 字段。"""
    if not text:
        return None
    text = text.strip()
    # 解 ```json ... ``` 包裹
    if text.startswith("```"):
        lines = text.split("\n")
        if lines[-1].strip() == "```":
            text = "\n".join(lines[1:-1])
        else:
            text = "\n".join(lines[1:])
    # 找第一个 { 到最后一个 }
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        text = text[start:end+1]
    try:
        return json.loads(text)
    except Exception:
        return None


def _validate(data):
    """校验并规整化识别结果。"""
    cat = (data.get("category") or "").strip().lower()
    if cat not in CATEGORIES:
        cat = "top"
    color = (data.get("color") or "").strip()
    if color not in COLORS_CN:
        color = "黑"
    season = (data.get("season") or "").strip()
    if season not in SEASONS:
        season = "四季"
    title = (data.get("title") or "").strip()[:30]
    if not title:
        title = f"{color}{cat}"
    return {
        "category": cat,
        "color": color,
        "season": season,
        "title": title,
        "confidence": 0.85,
    }


def auto_tag_image(image_url, timeout=120):
    """调 atlas /api/chat 多模态识别衣服。失败返回空 dict。"""
    payload = {
        "message": f"请识别这张衣服图片,严格 JSON 返回 category/color/season/title。图片 URL: {image_url}",
        "system": SYSTEM_PROMPT,
        "model": "MiniMax-M2.7",
        "image_url": image_url,
        "stream": False,
    }
    text = _atlas_chat(payload, timeout=timeout)
    data = _parse_tag_text(text)
    if not data:
        return {}
    return _validate(data)


def auto_tag_bytes(img_bytes, filename="upload.jpg"):
    """上传文件直接走 atlas 多模态需要 file URL,所以先存临时文件,然后传 file:// URL。"""
    suffix = os.path.splitext(filename)[1] or ".jpg"
    tmp_path = os.path.join("/tmp", f"auto_tag_{uuid.uuid4().hex}{suffix}")
    with open(tmp_path, "wb") as f:
        f.write(img_bytes)
    try:
        return auto_tag_image(f"file://{tmp_path}")
    finally:
        try:
            os.remove(tmp_path)
        except OSError:
            pass
