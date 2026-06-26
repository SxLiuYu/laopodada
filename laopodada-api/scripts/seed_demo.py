#!/usr/bin/env python3
"""seed_demo.py — 一键 seed 60 条 demo 数据(节 2.2 主入口)

用法:
  ./seed_demo.py                           # 默认 seed 123 公网
  ./seed_demo.py --target local            # 本地
  ./seed_demo.py --only wardrobe           # 只跑某段
  ./seed_demo.py --force                   # 跳过幂等
  ./seed_demo.py --dry-run                 # 下载图不写
  ./seed_demo.py --skip-unsplash           # 跳过图(只写数据,图用占位)

凭证(必须设 env):
  export LAOPODADA_123_PASS='YuJinZe12@.'

幂等检查:每段开头 GET count,达到阈值就跳过。--force 强制覆盖。
"""
import argparse
import os
import sys
import time
from pathlib import Path

# 让脚本能从 scripts/ 目录 import 兄弟模块
sys.path.insert(0, str(Path(__file__).parent))

import unsplash
import uploader
from data_wardrobe import WARDROBE
from data_recipes import RECIPES
from data_health import HEALTH_ARTICLES
from data_outfits import OUTFITS


TARGETS = {
    "123": "https://123.57.107.21:8088",
    "local": "http://127.0.0.1:8097",
}

THRESHOLDS = {
    "items": 10,
    "recipes": 30,
    "health": 15,
    "outfits": 5,
}


def _get_password(target):
    if target == "123":
        pw = os.environ.get("LAOPODADA_123_PASS")
        if not pw:
            sys.exit("需要 LAOPODADA_123_PASS 环境变量\ne.g. export LAOPODADA_123_PASS='...'\n或用 --target local")
    return os.environ.get("LAOPODADA_123_PASS", "")


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--target", choices=list(TARGETS), default="123")
    p.add_argument("--only", choices=["all", "wardrobe", "recipes", "health", "outfits"], default="all")
    p.add_argument("--force", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--skip-unsplash", action="store_true", help="跳过图下载,只写数据")
    return p.parse_args()


# ---------- 4 段 ----------
def seed_wardrobe(client, args):
    log = lambda m: print(f"[wardrobe] {m}")
    log("start")
    if not args.force:
        n = client.get_items().get("count", 0)
        if n >= THRESHOLDS["items"]:
            log(f"已有 {n} 件 ≥ {THRESHOLDS['items']},跳过")
            return
    for item in WARDROBE:
        if args.dry_run:
            log(f"DRY: would upload {item['id_hint']}")
            continue
        try:
            if args.skip_unsplash:
                # 跳过图,生成 1x1 灰
                import io
                from PIL import Image
                img = Image.new("RGB", (200, 200), (200, 200, 200))
                buf = io.BytesIO()
                img.save(buf, format="JPEG")
                jpg = buf.getvalue()
            else:
                # 默认 PIL 卡片(国内稳 + 0 网络),Unsplash 国外端点国内 503
                # 如需真实图:在 _make_card_jpeg 位置换 unsplash.download
                jpg = _make_card_jpeg(item)
            resp = client.upload_item(
                jpg, item["category"], item["title"],
                item["brand"], item["color"], item["season"],
            )
            log(f"  ✓ {item['id_hint']:20s} id={resp.get('item', {}).get('id', '?')[:12]}")
        except Exception as e:
            log(f"  ✗ {item['id_hint']:20s} ERR: {e}")
    log("done")


# ---------- 占位图:多色衣橱卡片 ----------
CATEGORY_COLORS = {
    "top":       (135, 176, 215),  # 浅蓝
    "bottom":    (198, 173, 128),  # 卡其
    "dress":     (230, 175, 200),  # 粉
    "outerwear": (158, 117, 87),   # 棕
    "shoes":     (170, 170, 170),  # 灰
    "bag":       (195, 165, 130),  # 驼
}


def _make_card_jpeg(item):
    """生成 800x800 多色衣橱卡:品类色背景 + 标题 + 品牌。"""
    import io
    from PIL import Image, ImageDraw, ImageFont
    bg = CATEGORY_COLORS.get(item["category"], (200, 200, 200))
    img = Image.new("RGB", (800, 800), bg)
    draw = ImageDraw.Draw(img)

    # 顶部浅色条
    draw.rectangle([0, 0, 800, 80], fill=(255, 255, 255, 200))

    # 找系统中文字体,失败用 default
    font_title = None
    font_brand = None
    for path in [
        "/System/Library/Fonts/PingFang.ttc",
        "/System/Library/Fonts/STHeiti Medium.ttc",
        "/System/Library/Fonts/Hiragino Sans GB.ttc",
        "/Library/Fonts/Arial Unicode.ttf",
    ]:
        if os.path.exists(path):
            try:
                font_title = ImageFont.truetype(path, 56)
                font_brand = ImageFont.truetype(path, 36)
                break
            except Exception:
                continue
    if font_title is None:
        font_title = ImageFont.load_default()
        font_brand = ImageFont.load_default()

    # 标题(中间)
    title = item["title"]
    bbox = draw.textbbox((0, 0), title, font=font_title)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text(((800 - tw) / 2, 320), title, fill=(50, 50, 50), font=font_title)

    # 品牌(下面)
    brand = item.get("brand", "")
    if brand:
        bbox2 = draw.textbbox((0, 0), brand, font=font_brand)
        bw = bbox2[2] - bbox2[0]
        draw.text(((800 - bw) / 2, 420), brand, fill=(90, 90, 90), font=font_brand)

    # 顶部品类 + 颜色 chip
    cat = item.get("category", "")
    color = item.get("color", "")
    header = f"  {cat} · {color}  "
    bbox3 = draw.textbbox((0, 0), header, font=font_brand)
    hw = bbox3[2] - bbox3[0]
    draw.text(((800 - hw) / 2, 24), header, fill=(60, 60, 60), font=font_brand)

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    return buf.getvalue()


def seed_recipes(client, args):
    log = lambda m: print(f"[recipes]  {m}")
    log("start")
    if not args.force:
        n = client.get_recipes().get("count", 0)
        if n >= THRESHOLDS["recipes"]:
            log(f"已有 {n} 道 ≥ {THRESHOLDS['recipes']},跳过")
            return
    for r in RECIPES:
        if args.dry_run:
            log(f"DRY: would create {r['title']}")
            continue
        try:
            resp = client.create_recipe(r)
            log(f"  ✓ {r['title'][:20]:20s} id={resp.get('recipe', {}).get('id', '?')[:12]}")
        except Exception as e:
            log(f"  ✗ {r['title'][:20]:20s} ERR: {e}")
    log("done")


def seed_health(client, args):
    log = lambda m: print(f"[health]   {m}")
    log("start")
    if not args.force:
        n = client.get_health_articles().get("count", 0)
        if n >= THRESHOLDS["health"]:
            log(f"已有 {n} 篇 ≥ {THRESHOLDS['health']},跳过")
            return
    for a in HEALTH_ARTICLES:
        if args.dry_run:
            log(f"DRY: would create {a['title']}")
            continue
        try:
            resp = client.create_health_article(a)
            log(f"  ✓ {a['title'][:30]:30s} id={resp.get('id', '?')[:12]}")
        except Exception as e:
            log(f"  ✗ {a['title'][:30]:30s} ERR: {e}")
    log("done")


def seed_outfits(client, args):
    log = lambda m: print(f"[outfits]  {m}")
    log("start")
    if not args.force:
        n = client.get_outfits().get("count", 0)
        if n >= THRESHOLDS["outfits"]:
            log(f"已有 {n} 组 ≥ {THRESHOLDS['outfits']},跳过")
            return
    for o in OUTFITS:
        if args.dry_run:
            log(f"DRY: would generate {o['label_cn']} ({o['occasion']})")
            continue
        try:
            resp = client.generate_outfit(
                o["occasion"], season=o.get("season"), weather=o.get("weather")
            )
            # /recommend 返 {"outfits":[{"items":[...],...}]}
            # /generate   返 {"outfit":{"items":[...],...}}
            outfits = resp.get("outfits")
            if outfits is None and "outfit" in resp:
                outfits = [resp["outfit"]]
            items = (outfits or [{}])[0].get("items", [])
            cats = sorted({i.get("category", "?") for i in items})
            log(f"  ✓ {o['label_cn']:8s} ({o['occasion']:7s}/{o.get('season', '-'):6s}) "
                f"{len(items)}件 [{'/'.join(cats)}]")
        except Exception as e:
            log(f"  ✗ {o['label_cn']:8s} ({o['occasion']}) ERR: {e}")
    log("done")


def print_summary(client):
    print("\n" + "=" * 50)
    print("  L1 自检 — 4 段数据 count")
    print("=" * 50)
    for label, getter, threshold in [
        ("衣橱",    client.get_items,            THRESHOLDS["items"]),
        ("菜谱",    client.get_recipes,          THRESHOLDS["recipes"]),
        ("健康",    client.get_health_articles,  THRESHOLDS["health"]),
        ("outfit",  client.get_outfits,          THRESHOLDS["outfits"]),
    ]:
        try:
            n = getter().get("count", 0)
            ok = "✅" if n >= threshold else "⚠️ "
            print(f"  {ok} {label:8s} {n:3d} (期望 ≥ {threshold})")
        except Exception as e:
            print(f"  ✗  {label:8s} ERR: {e}")


def main():
    args = parse_args()
    base = TARGETS[args.target]
    _get_password(args.target)
    print(f"=== seed_demo ===")
    print(f"target:  {args.target} ({base})")
    print(f"only:    {args.only}")
    print(f"force:   {args.force}")
    print(f"dry-run: {args.dry_run}")
    print(f"skip-unsplash: {args.skip_unsplash}")
    print()

    client = uploader.LaopodadaClient(base)
    # 先测后端活着
    try:
        h = client.health()
        print(f"health: {h.get('ok')}, time={h.get('time')}")
    except Exception as e:
        sys.exit(f"后端不可达: {e}\n确认 {base} 在跑")
    print()

    t0 = time.time()
    if args.only in ("all", "wardrobe"):
        seed_wardrobe(client, args)
    if args.only in ("all", "recipes"):
        seed_recipes(client, args)
    if args.only in ("all", "health"):
        seed_health(client, args)
    if args.only in ("all", "outfits"):
        seed_outfits(client, args)

    if not args.dry_run:
        print_summary(client)

    print(f"\nelapsed: {time.time() - t0:.1f}s")


if __name__ == "__main__":
    main()
