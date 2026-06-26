# laopodada 一键 Seed Demo 数据 — 设计规格

**日期:** 2026-06-15
**作者:** Hermes (superpowers brainstorm)
**状态:** 已批准,待实施

## 1. 目标

让 laopodada 移动 App 在产品视角下"完成度 100%":用户打开 APK,衣橱 / 点餐 / 健康 / AI 4 个 tab 都有丰满的真实数据,无需先自己上传或等待 AI 生成。

**当前基线 vs 目标:**

| 类别 | 当前 | 目标 | 新增 |
|---|---|---|---|
| 衣橱 items | 1 | 10 | 9 |
| 菜谱 recipes | 18 | 30 | 12 |
| 健康文章 | 8 | 15 | 7 |
| outfit 示例 | 0 | 5 | 5 |
| **总计** | **27** | **60** | **33** |

## 2. 数据清单(节 1 修订)

### 2.1 衣橱 10 件

| # | category | title | color | season | brand | Unsplash query |
|---|---|---|---|---|---|---|
| 1 | top | 白色棉质 T 恤 | 白 | 四季 | Uniqlo | white cotton tshirt flatlay |
| 2 | top | 黑色针织衫 | 黑 | 秋 | MUJI | black knit sweater |
| 3 | top | 米色亚麻衬衫 | 米 | 夏 | COS | beige linen shirt |
| 4 | bottom | 蓝色直筒牛仔裤 | 蓝 | 四季 | Levi's | blue straight jeans |
| 5 | bottom | 黑色西装裤 | 黑 | 秋 | Zara | black dress pants women |
| 6 | dress | 碎花连衣裙 | 蓝 | 夏 | H&M | floral summer dress |
| 7 | outerwear | 驼色大衣 | 棕 | 冬 | MaxMara | camel coat women |
| 8 | shoes | 白色运动鞋 | 白 | 四季 | Nike | white sneakers |
| 9 | shoes | 黑色高跟鞋 | 黑 | 四季 | Steve Madden | black heels |
| 10 | bag | 棕色手提包 | 棕 | 四季 | Coach | brown leather handbag |

**目的:** 7 category 全覆盖,AI outfit 至少能组合 3 套 casual + 1 套 formal + 1 套 summer。

### 2.2 菜谱 12 道

| 类别 | 难度 | 数量 |
|---|---|---|
| breakfast | easy | 3 |
| lunch | easy | 3 |
| dinner | medium | 4 |
| dinner | hard | 1 |
| snack | easy | 1 |

完整字段(title/category/difficulty/prep_minutes/cook_minutes/servings/ingredients/steps/tags/note)由人手写,不走 LLM。

### 2.3 健康文章 7 篇

| 类别 | 数量 | 主题 |
|---|---|---|
| nutrition | 3 | 早餐重要性 / 膳食纤维 5 大来源 / 控糖饮食原则 |
| exercise | 2 | 久坐拉伸 5 动作 / HIIT 入门 20 分钟 |
| disease | 2 | 糖尿病前期逆转 / 高血压 DASH 饮食 |

内容基于权威源(WHO / 中国居民膳食指南 2022 / 中国卫健委),禁 LLM 编造。

### 2.4 outfit 示例 5 组

| # | occasion | weather | 期望组合 | 验证 |
|---|---|---|---|---|
| 1 | 上班通勤 | — | 衬衫 + 西装裤 + 高跟鞋 + 手提包 | 4 category |
| 2 | 周末休闲 | — | T 恤 + 牛仔裤 + 运动鞋 | 3 category |
| 3 | 正式晚宴 | — | 连衣裙 + 高跟鞋 + 手提包 | 3 category |
| 4 | 秋冬保暖 | cold | 针织衫 + 牛仔裤 + 大衣 + 运动鞋 | 4 category |
| 5 | 夏日出行 | hot | 亚麻衬衫 + 牛仔裤 + 运动鞋 | 3 category |

## 3. 脚本架构(节 2)

### 3.1 目录布局

```
/Users/sxliuyu/repos/laopodada/
├── laopodada-api/
│   ├── seed_recipes.py          # 现有,不动
│   └── scripts/                 # 新建
│       ├── seed_demo.py         # 主入口
│       ├── unsplash.py          # Unsplash CC0 下载
│       ├── uploader.py          # 后端 API 客户端
│       ├── data_wardrobe.py     # 10 件衣
│       ├── data_recipes.py      # 12 道菜
│       ├── data_health.py       # 7 篇文章
│       └── data_outfits.py      # 5 个 outfit
```

### 3.2 主入口 CLI

```bash
./seed_demo.py                           # 默认 seed 123 公网
./seed_demo.py --target local            # 本地
./seed_demo.py --only wardrobe           # 只跑某段
./seed_demo.py --force                   # 跳过幂等
./seed_demo.py --dry-run                 # 下载图不写
```

幂等检查:每段开头 `GET` 远端 count,达到阈值就跳过。`--force` 强制覆盖。

### 3.3 模块设计

- **unsplash.py** (200 行): 调 `source.unsplash.com` 公共端点(无需 key,5 req/s 限流),本地缓存 `~/.cache/unsplash/<hash>.jpg`,失败 3 次退避。
- **uploader.py** (150 行): 4 个方法 `upload_item / create_recipe / create_health_article / generate_outfit`,SSL 跳过(自签证书)。
- **4 个 data_*.py** (各 80-250 行): 模块级常量 list[dict]。

### 3.4 流程

```python
def main():
    args = parse_args()
    client = LaopodadaClient(target)
    unsplash = Unsplash()
    if args.only in ("all", "wardrobe"): seed_wardrobe(...)
    if args.only in ("all", "recipes"):  seed_recipes(...)
    if args.only in ("all", "health"):   seed_health(...)
    if args.only in ("all", "outfits"):  seed_outfits(...)
    print_summary()
```

## 4. 123 上传流程(节 3 修订)

### 4.1 关键发现(实施前发现,影响原方案)

**实施前验证时发现 `health_articles` 不是 db 表,而是 `app.py` 里的内存 list**(`HEALTH_ARTICLES = [...]`)。这意味着:

- 原 A2 方案(SQL 直接写 db)**不成立** — 没有表
- 改走 A1 方案(扩后端 POST endpoint)**反而更干净** — 数据流单一(内存,API CRUD)

**修订:** 健康文章改为走 API,需在 `app.py` 末尾加 1 个 `POST /api/v1/health/articles` 端点(约 20 行)。

### 4.2 网络拓扑

```
Mac 本机                              123 公网
~/repos/laopodada/                    /data/laopodada/
  scripts/seed_demo.py                  db/laopodada.db
       │ curl POST (SSL 跳过自签)        images/original/
       ├──────────────────────────────→ :8088/api/v1/items
       │ curl POST                      images/list/
       ├──────────────────────────────→ :8088/api/v1/recipes       (走完整链路)
       │ curl POST                      images/thumb/
       ├──────────────────────────────→ :8088/api/v1/health/articles (新加)
       │ curl POST
       └──────────────────────────────→ :8088/api/v1/outfits/generate
                                          (nginx → gunicorn 8097 → app.py)
```

**全部走 API**(修订后,删原 A2 方案的 SSH + sqlite3 通道)。

### 4.3 凭证(从 memory 拿)

| 项 | 值 |
|---|---|
| IP | 123.57.107.21 |
| SSH 用户 | root |
| 密码 | YuJinZe12@. |
| 后端 base URL | https://123.57.107.21:8088 |
| 远端 db 路径 | /data/laopodada/db/laopodada.db |
| systemd 服务 | laopodada-api.service |

**脚本不写死密码**,读 env `LAOPODADA_123_PASS`,没设就报错。

### 4.4 后端小改(1 文件,~20 行)

`laopodada-api/app.py` 末尾(1733 行后)加:

```python
@app.post("/api/v1/health/articles")
def create_health_article():
    """Seed-only endpoint to append a health article to the in-memory list."""
    body = request.get_json(silent=True) or {}
    for f in ["title", "category", "content"]:
        if not body.get(f):
            return jsonify({"error": f"missing {f}"}), 400
    article = {
        "id": uuid.uuid4().hex[:12],
        "title": body["title"],
        "category": body["category"],
        "content": body["content"],
        "summary": body.get("summary", body["content"][:80] + "..."),
        "read_minutes": int(body.get("read_minutes", 5)),
        "source": body.get("source", "WHO/中国居民膳食指南 2022"),
        "created_at": int(time.time()),
    }
    HEALTH_ARTICLES.append(article)
    return jsonify(article), 201
```

**部署:** `rsync app.py` 到 123 → `systemctl restart laopodada-api` → `curl POST` 验。

**风险评估:** 极低 — 新增 endpoint,不动现有 list 结构,不删数据。

## 5. 验证金字塔(节 4)

### 5.1 L1 单元自检(seed 内部)

每段写完立刻验:

```python
# wardrobe
assert items_count >= 10 and category_count >= 5
for it in items[:3]: assert HEAD(thumbnail_url) == 200

# recipes
assert recipes_count >= 30 and {breakfast, lunch, dinner}.issubset(categories)

# health
assert articles_count >= 15 and {nutrition, exercise, disease}.issubset(categories)

# outfits
assert outfits_count >= 5
for o in outfits: assert len({i.category for i in o.items}) >= 2
```

### 5.2 L2 公网端到端(终端 curl 4 条)

```bash
# 4 个 count
echo "衣橱: $(curl ... | jq .count)"    # 期望 ≥10
echo "菜谱: $(curl ... | jq .count)"    # 期望 ≥30
echo "健康: $(curl ... | jq .count)"    # 期望 ≥15
echo "outfit: $(curl ... | jq .count)"  # 期望 ≥5

# 公网图可访(随机 5 张)
# AI outfit 多 category
# 健康文章字段完整
```

### 5.3 L3 真机/模拟器视觉

情况 A(Android 模拟器在跑):CI 重 build v11 APK → adb install → 截图 4 tab → 肉眼看 10/30/15/5 全显。

情况 B(模拟器没跑):给用户 APK URL 自取,降级到 L1+L2。

情况 C(iOS 真机):走 AltStore 拖 .ipa。

## 6. 完工报告

seed 跑完 + 3 层验证全过,写 `docs/STATUS.md` 总结:
- 数据现状(60 条)
- 部署(baseURL / systemd)
- 验证(L1/L2/L3)
- 已知限制(内存 list 重启丢)
- 下一步(衣橱上传真机测,outfit 反馈接入)

## 7. 风险 + 缓解

| 风险 | 缓解 |
|---|---|
| Unsplash 限流 | source.unsplash.com 公共端点 + 本地缓存 |
| 图片 API 400 (category 白名单) | data_wardrobe 7 category 跟 CATEGORIES 一致 |
| 123 服务挂 | seed 前 curl /health |
| outfit LLM 选不准 | category 校验,3 类以下 warn 不重试 |
| gunicorn 缓存旧代码 | restart 后 sleep 3 再调 API |

## 8. 决策记录

| 决策 | 选择 | 理由 |
|---|---|---|
| 优化方向 | 产品视角(C) | 用户授权"完成度 100%" |
| 子项目 | 一键 seed 脚本 | 直接补数据 |
| 图片源 | Unsplash CC0 | 零成本高质量 |
| seed 目标 | 123 公网 | APK 用户看到公网数据 |
| 健康文章入口 | A1 扩后端 API | 修订:原 A2 SQL 不成立(无表) |
| 失败策略 | 单条失败 log 继续 | 不阻塞其它 |
| 重入 | 幂等 + --force | 安全 |
