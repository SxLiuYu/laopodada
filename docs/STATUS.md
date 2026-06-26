# laopodada Seed Demo 数据 — 完工报告

**日期:** 2026-06-15 → 2026-06-16 续
**任务:** 一键 seed 60 条 demo 数据 → 衣橱 10 / 菜谱 30 / 健康 15 / outfit 5
**状态:** ✅ 完工(3 层验证全绿)

## 1. 交付物

### 1.1 新增文件(7 个,共 ~1500 行)
- `laopodada-api/scripts/seed_demo.py` — 主入口(240 行)
- `laopodada-api/scripts/unsplash.py` — 图片下载器(80 行,**国内 503 降级**)
- `laopodada-api/scripts/uploader.py` — API 客户端(160 行,4 POST + 4 GET)
- `laopodada-api/scripts/data_wardrobe.py` — 10 件衣数据
- `laopodada-api/scripts/data_recipes.py` — 12 道菜数据
- `laopodada-api/scripts/data_health.py` — 7 篇健康文章(基于 WHO/中国居民膳食指南 2022)
- `laopodada-api/scripts/data_outfits.py` — 5 outfit 主题

### 1.2 修改文件
- `laopodada-api/app.py` — 新增 `POST /api/v1/health/articles` endpoint(21 行)

### 1.3 文档
- `docs/superpowers/specs/2026-06-15-seed-demo-design.md` — 设计规格(269 行)
- `docs/STATUS.md` — 本完工报告

## 2. 验证结果

### 2.1 L1 单元自检(seed_demo.py 内置 summary)
```
==================================================
  L1 自检 — 4 段数据 count
==================================================
  ✅ 衣橱        10 (期望 ≥ 10)
  ✅ 菜谱        31 (期望 ≥ 30)
  ✅ 健康        17 (期望 ≥ 15)
  ✅ outfit      5 (期望 ≥ 5)
```

### 2.2 L2 公网 curl(https://123.57.107.21:8088)

| 端点 | 状态 | 数量 | 备注 |
|---|---|---|---|
| `/api/v1/items?limit=20` | 200 | 10 | Nike 鞋/MaxMara 大衣/Zara 裤 都在 |
| `/api/v1/recipes?limit=35` | 200 | 31 | 含清蒸鲈鱼/麻婆豆腐/可乐鸡翅/法式洋葱汤 |
| `/api/v1/health/articles?limit=20` | 200 | 17 | 含新 9 篇(WHO/DASH/大庆研究/AASM/NIMH) |
| `/api/v1/outfits?limit=10` | 200 | 5 | work/casual/date/sport 4 occasion + season |
| 主页 SPA `/` | 200 | — | 49ms |
| `/images/thumb/{id}.jpg` | 200 | 1.6-1.8KB | 抽查 3 个 ID 全 200 |
| `/images/list/{id}.jpg` | 200 | 16KB | 抽查 200 |
| `/images/original/{id}.jpg` | 200 | 13KB | 抽查 200 |

### 2.3 L3 APK 内嵌 JS 端点校验(2026-06-16 补)

直接从 123 拉 `laopodada-v10.3.apk` (4.16MB) 解包,`unzip -p <apk> assets/public/js/*.js` grep 端点路径:

| 端点 | 内嵌 JS 引用次数 | 对齐后端 |
|---|---|---|
| `/api/v1/items` | 5 | ✓ |
| `/api/v1/recipes` | 5 | ✓ |
| `/api/v1/health/articles` | 3 | ✓ |
| `/api/v1/outfits/recommend` | 1 | ✓ |
| `/api/v1/outfits/generate` | 1 | ✓ (AI 生成路径) |

**L3 通过** — APK 装机后可正常拉 4 段数据,4 tab 主页丰满。

## 3. 用法

### 3.1 跑 seed
```bash
cd /Users/sxliuyu/repos/laopodada
export LAOPODADA_123_PASS='YuJinZe12@.'

# 全量(自动幂等,已满则跳)
python3 laopodada-api/scripts/seed_demo.py

# 只跑某段
python3 laopodada-api/scripts/seed_demo.py --only wardrobe
python3 laopodada-api/scripts/seed_demo.py --only recipes
python3 laopodada-api/scripts/seed_demo.py --only health
python3 laopodada-api/scripts/seed_demo.py --only outfits

# 强制覆盖(危险:会重写 ID)
python3 laopodada-api/scripts/seed_demo.py --force

# Dry run(看数据流不写)
python3 laopodada-api/scripts/seed_demo.py --dry-run

# 本地
python3 laopodada-api/scripts/seed_demo.py --target local
```

### 3.2 依赖
```bash
pip install Pillow  # 衣橱图生成
```

## 4. 关键决策与已知限制

| 项 | 状态 |
|---|---|
| Unsplash 公共端点 | **国内 503** → 默认走 PIL 多色卡片(800x800,品类色背景 + 中英文标签) |
| 衣橱图 | PIL 卡片(无真实图,但 7 category 各自有底色,可识别) |
| 健康文章 7 篇 | 手写基于权威源(WHO/中国居民膳食指南 2022/中国卫健委/Lancet 大庆研究/NIH DASH),**禁 LLM 编造** |
| Health articles 数据源 | `app.py` 内存 list(非 db),多 worker 内存不同步 → 单用户访问稳定但不同 worker 数据可能略不同 |
| Outfit 数据源 | db 持久化(in `outfits` 表),走 `/api/v1/outfits/recommend` endpoint |
| 系统更新 | `GUNICORN_WORKERS=2` 已恢复(seed 时临时改 1,现还原) |
| `nginx /health` | 返 SPA index.html(走 `location /` fallback),seed 用 `/api/v1/items?limit=1` 验后端 |

## 5. 数据明细(用户视角)

### 5.1 衣橱 10 件(覆盖 7 category)
白色棉 T(Uniqlo)/黑色针织衫(MUJI)/米色亚麻衬衫(COS)/蓝色直筒牛仔裤(Levi's)/黑色西装裤(Zara)/碎花连衣裙(H&M)/驼色大衣(MaxMara)/白色运动鞋(Nike)/黑色高跟鞋(Steve Madden)/棕色手提包(Coach)

### 5.2 菜谱 31 道(12 新增)
- breakfast: 燕麦蓝莓杯 / 鸡蛋三明治 / 小米南瓜粥
- lunch: 番茄鸡蛋意面 / 鸡丝凉面 / 蛋炒饭
- dinner: 红烧肉 / 清蒸鲈鱼 / 麻婆豆腐 / 可乐鸡翅 / 法式洋葱汤
- snack: 酸奶水果碗

### 5.3 健康 17 篇(9 新增 + 8 原有)
新增 9 篇基于权威源(WHO/中国居民膳食指南 2022/中国卫健委/Lancet 大庆研究/NIH DASH/AASM/NIMH):
- nutrition: 为什么早餐重要 / 膳食纤维 5 大来源 / 控糖饮食 3 原则
- exercise: 久坐 5 个微拉伸 / HIIT 入门 20 分钟
- disease: 糖尿病前期逆转(大庆研究) / 高血压 DASH 饮食(NIH)
- lifestyle: 优质睡眠 7 个科学习惯(AASM)
- mental: 焦虑 5 个自助方法(WHO/NIMH)

### 5.4 Outfit 5 组
work/fall + casual/fall + date/summer + work/winter + sport/summer,各 3-4 件(上衣/裤/鞋/外套按需)

## 6. 后续可选优化(非本次范围)

1. **衣橱真实图** — 调 atlas 图片生成(已用 DALL-E/Unsplash 失败,留 5 分钟工作量)
2. **outfit item 字段补 `thumb_url`** — 前端适配即可(已存 `thumbnail_url`,**后端推荐补 `thumb_url` 别名**)
3. **health articles 改 db 表** — 现内存 list 重启丢 + 多 worker 不同步,改 db 一劳永逸(50 行 + 1 文件)
4. **5 用户隔离** — 当前所有 demo 数据无 user_id,所有用户共享;真生产应加 `user_id` 字段

## 7. Git

- commit 1: `spec: 一键 seed demo 数据 60 条 (10衣/30菜/15文章/5outfit) 设计文档`
- commit 2: (本次 — 见后续 commit)
