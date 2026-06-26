# 老婆哒哒 (laopodada) 产品/技术规格说明书

## 产品定位

**一句话**:面向个人用户的私人助理 App,聚焦衣橱管理 + 点餐决策 + 健康科普 + AI 闲聊四大场景。

**目标用户**:单用户(老婆)自用,以女性视角设计,中文交互。

**解决的问题**:日常"今天穿什么""吃啥好""这个健康说法对吗"+"问点小问题"的碎片决策,通过拍照/文字/AI 集中归口。

**技术栈**:
- **客户端**: Capacitor 8.4.0 跨端壳,Android (compileSdk 36) + iOS 双原生工程,前端 vanilla JS + CSS,无构建步骤 (`www/` 即源码)
- **后端**: Flask 3 + gunicorn (`gthread`, 2 workers × 4 threads),Python 3,SQLite (WAL 模式),Pillow 10+ 处理图片
- **LLM**: minimaxi M3,经 atlas panel.py (`:18793`) 中转,代码层走 `llm.cached_call()` / `recommend.OutfitRecommender`
- **存储**: `/data/laopodada/{images/{original,list,thumb}, db/laopodada.db}`
- **部署**: 阿里云 ECS `123.57.107.21`,nginx 8088/8091/8443 反代,gunicorn `:8097` (laopodada-api)
- **HTTPS**: 自签证书,首次访问需手动信任

**Capacitor 配置**: `capacitor.config.json:1-10` — `appId=com.laopodada.app`, `webDir=www`, `androidScheme=http`, `cleartext=true`, `iosScheme=capacitor`.

## 5 大板块

### 1. 衣橱 (wardrobe)

**功能列表**:
- 拍照/相册上传单件衣物,带类别 / 标题 / 颜色 / 季节 4 个元数据字段
- 按分类筛选列表 (8 类: all/top/bottom/dress/outerwear/shoes/bag/accessory)
- 单件详情 modal (大图 + 元数据 + 删除按钮)
- 删除 (DB 行 + 3 个尺寸图片文件)

**关键交互流程**: 上传 sheet → `<input type=file capture=environment>` 拍照/选图 → FileReader 预览 → FormData POST → 后端收 `file + category + title/color/season` → Pillow 三档缩放 (`_save_three_sizes`, `laopodada-api/app.py:197-263`) → INSERT SQLite → 返回 item URL。

**API 端点**:
- `POST /api/v1/items` (multipart) `laopodada-api/app.py:361-394` — 必填 `file` + `category`,可选 `title/brand/color/season/note`
- `GET /api/v1/items?category=&limit=&offset=` `app.py:340-358` — 返回 `{count, items[]}`, 默认 limit 100, 上限 500
- `GET /api/v1/items/<id>` `app.py:397-403` — 单件详情
- `DELETE /api/v1/items/<id>` `app.py:406-424` — 删 DB 行 + 三档图片文件

**返回 schema** (衣橱单件): `{id, title, category, brand, color, season, note, original_url, list_url, thumbnail_url, bytes_orig, created_at, created_at_iso, updated_at}`。注意前端读取字段名是 `thumbnail_url` (`wardrobe.js:166`) 而非 `thumb_url` — `_row_to_wardrobe` (`app.py:289`) 做了 alias。

**前端关键函数**:
- `renderWardrobePage()` `www/js/wardrobe.js:6-29` — 渲染 filter chips + 拍照按钮 + grid
- `openUploadSheet()` `wardrobe.js:32-87` — bottom sheet 表单
- `submitUpload()` `wardrobe.js:110-153` — FormData 提交 + 错误处理
- `loadWardrobe()` `wardrobe.js:155-180` — 列表加载
- `showItemDetail()` / `confirmDeleteItem()` `wardrobe.js:190-224`

**已知 bug / 限制**:
- 衣橱拍照上传曾被删,本次 commit `488e281` 恢复(v9)
- `capture="environment"` 在 iOS Safari 上被部分忽略,fallback 到选图

### 2. 点餐 (recipe)

**功能列表**:
- 菜谱列表 + 分类筛选 (breakfast/lunch/dinner/snack/dessert/drink) + 难度筛选 (easy/medium/hard) + 模糊搜索 (title)
- "+ 新建" 手工录入 (title/category/difficulty/prep/cook/ingredients 换行分隔/steps 换行分隔/tags 逗号分隔)
- AI 一键生成菜谱 (LLM 60-90 秒,生成结果直接插入列表头部 + 高亮紫色边框)
- 详情 modal (cover + 元数据 + 食材/步骤列表)
- 删除

**关键交互流程**: AI 生成 → `generateRecipe(query)` → 后端 `llm.cached_call('recipe', ...)` → 校验字段 (`_validate_recipe_gen`, `app.py:1585-1602`) → 校验失败重试 1 次 (最多 2 次, `app.py:1618`) → 失败返 422 → 校验通过 INSERT recipes 表 → 201 + 新菜谱对象 → 前端 `prependRecipeToList` `recipe.js:145-166` 插到列表头。

**API 端点**:
- `GET /api/v1/recipes?category=&difficulty=&tag=&limit=&offset=` `app.py:428-455` — 标签匹配走 `LIKE '%,tag,%'` 子串
- `POST /api/v1/recipes` `app.py:458-519` — JSON body,可选 `cover` multipart 走 3 档缩放
- `GET /api/v1/recipes/<id>` `app.py:522-528`
- `DELETE /api/v1/recipes/<id>` `app.py:531-545` — 删 cover 3 档
- `POST /api/v1/recipes/generate` `app.py:1605-1648` — body `{query}`,LLM 生成,自动落库

**返回 schema** (单菜谱): `{id, title, category, difficulty, prep_minutes, cook_minutes, servings, ingredients[], steps[], tags[], note, cover_url, bytes_cover, created_at, created_at_iso, updated_at}`。ingredients/steps 在 DB 存 `\n` 分隔字符串,`app.py:306-307` 拆数组返回。

**前端关键函数**:
- `renderRecipePage()` `www/js/recipe.js:22-101` — 4 段 UI (头部 + AI 生成栏 + cat/diff chips + 搜索 + grid)
- `generateRecipe()` 走 `api.js:174-185`
- `showRecipeDetail()` / `confirmDeleteRecipe()` / `showRecipeCreateForm()` / `submitRecipe()` `recipe.js:183-319`
- 种子数据 `laopodada-api/seed_recipes.py:31-350` 提供 12 道家常菜 (idempotent, 12 行短路退出)

### 3. 健康 (health articles)

**功能列表**:
- 健康科普文章列表 (8 篇硬编码 in-memory)
- 分类筛选 (nutrition/exercise/disease/mental/female — `prevention` 只在 AI 生成 select 中)
- 搜索 (title + summary 模糊匹配)
- AI 一键生成文章 (LLM 60-90 秒,落进 `HEALTH_ARTICLES` 列表内存)
- 已读状态 localStorage (`health_read_ids`)
- 离线降级: 失败时回退 `healthCache` (localStorage `health_articles`)

**关键交互流程**: AI 生成 → 强校验白名单来源 + 长度 + 禁用词 (`_validate_article_gen`, `app.py:1670-1692`) → 来源必须含 WHO/中国居民膳食指南/中国国家卫健委/中国营养学会/ACOG/Lancet/NEJM/JAMA/CDC/中国疾控 之一 → 通过则 append 到 `HEALTH_ARTICLES` 内存 list 并返 201 → 前端 `prependArticleToList` `health.js:177-192`。

**API 端点**:
- `GET /api/v1/health/articles?category=&limit=&offset=` `app.py:1061-1074` — 默认 limit 10, 上限 100
- `GET /api/v1/health/articles/<id>` `app.py:1077-1083`
- `POST /api/v1/health/articles/generate` `app.py:1695-1729` — body `{topic, category?}`, LLM 生成, **不入 DB** 仅 append 内存 list (重启丢失)

**8 篇硬编码文章** (`HEALTH_ARTICLES`, `app.py:549-1058`): 蛋白质摄入指南 / Omega-3 7 大益处 / WHO 运动量 / 久坐 5 微习惯 / 高血压 / 糖尿病前期 / 焦虑 7 法 / 月经周期营养 — 每篇 400-1500 字 markdown 含来源白名单。

**前端关键函数**:
- `renderHealthPage()` / `renderHealthCatBar()` / `loadHealthArticles()` `www/js/health.js:14-115`
- `renderHealthList()` `health.js:117-138` — client-side 模糊搜索
- `openHealthArticle()` `health.js:146-168` — modal + 已读计数

**已知 bug / 限制**:
- 健康生成文章存内存不落库 — 重启容器后丢失 (只增不减语义)
- LLM 偶尔不返 JSON 时 `extract_json` 仍可能失败,root cause 在 LLM,extract 鲁棒化部分修复 (`llm.py:64-114`)
- prevention 分类只存在于 AI 生成下拉,前端列表不显示

### 4. AI 咨询 (chat)

**功能列表**:
- 与 MiniMax M3 中文对话
- 4 个快捷入口 (天气/早餐/笑话/穿搭) + 清空
- 历史记录 (后端按 `session_id` 持久化)
- localStorage 缓存 `chat_session_id` (`web-<ts>-<rand>`) + `chat_count` 计数

**关键交互流程**: 发送消息 → `chatWithAI(msg, sessionId)` → POST `/api/chat` → 后端 atlas `/api/chat` → 返回 `{response}` → 前端兜底读取 `data.response || data.reply || data.content || data.message` (`api.js:160`)。注意: **chat 路径不走 laopodada-api**,直走 nginx 8088 反代 atlas 18793。

**API 端点** (atlas,不在 app.py):
- `POST /api/chat` (atlas 18793) — body `{message, session_id}`,返 `{response, session_id}`
- `GET /api/chat/history?session_id=&limit=` — 返 `{history/messages: [{role, content}]}`

**前端关键函数**:
- `renderChatPage()` / `sendChat()` / `sendQuickChat()` / `clearChat()` `www/js/chat.js:9-100`
- 计数 `chat.js:73-75` 写 localStorage 给 profile 页用

**已知 bug / 限制**:
- 直连 atlas 18793 公网被挡,v8 commit `92a6af0` 改走 window.API_BASE(nginx 8088 反代)
- reply/response 字段名错,v8 同样修复 (`api.js:160` 兜底 4 种字段)

### 5. 我的 (profile)

**功能列表**:
- 4 个统计卡片: 衣橱单品数 / 菜谱数 / 健康已读 / AI 对话次数
- 最近推荐历史 (基于 `outfits` 表)

**关键交互流程**: `loadProfileStats()` (`profile.js:36-82`) 并发 3 个请求 `listItems / listRecipes / listOutfits` → 衣橱数取 `data.count`、菜谱数取 `data.count || data.total` → 健康已读读 `localStorage.health_read_ids.length` → AI 对话次数读 `localStorage.chat_count` → 渲染 outfits 历史列表带日期/场合/style_score。

**API 端点**:
- `GET /api/v1/items?limit=1` 取 count
- `GET /api/v1/recipes?limit=1` 取 count
- `GET /api/v1/outfits?limit=20` `app.py:1393-1417` — 历史

**已知 bug / 限制**:
- 健康已读数和 AI 对话次数纯前端 localStorage, 卸载 App 丢失
- profile 无用户登录,实际单用户使用

## AI 生成系统

**LLM 客户端架构**:
- `laopodada-api/llm.py:11` 定义 `ATLAS_BASE = "http://127.0.0.1:18793"` (同机 panel.py 中转)
- `call_atlas(message, session_prefix)` `llm.py:21-43` — POST `/api/chat`, 60s timeout, 拿 `data.reply`
- `cached_call(prefix, query, system)` `llm.py:46-61` — 把 system 拼到 message 前(因为 atlas 无独立 system 字段),按 `sha256(query|system)` 做 1 小时 in-memory 缓存 (`CACHE_TTL_SEC = 3600`)
- `extract_json(reply)` `llm.py:64-114` — 鲁棒解析: ①优先匹配 ` ```json {…} ``` ` markdown fence; ②逐个扫描顶层 `{…}` 块,识别字符串内 escape + 大括号配对; ③任一 `json.loads` 成功立即返回

**3 个 endpoint 对比**:

| Endpoint | 输入 | 校验重试 | 落库 | 触发页面 |
|---|---|---|---|---|
| `POST /api/v1/recipes/generate` `app.py:1605-1648` | `{query}` | 2 次 | ✅ recipes 表 | 点餐页 `recipe.js:58-98` |
| `POST /api/v1/health/articles/generate` `app.py:1695-1729` | `{topic, category?}` | 2 次 | ❌ 仅内存 list | 健康页 `health.js:42-81` |
| `POST /api/v1/outfit/recommend` `app.py:1483-1529` | `{context, session_id?}` | 3 次 + fallback | ✅ outfit_recommendations 表 | (recommend.js 直连) |

**Prompt 模板要点**:
- 菜谱系统 (`app.py:1571-1582`): 严格"只输出真实菜谱"、食材用量常识、3-8 步、`prep+cook ≤ 90` 分钟、纯 JSON 无 markdown
- 健康系统 (`app.py:1652-1667`): 禁编造来源/数据/医疗建议、禁绝对化用语、JSON 字段含 80-150 字 summary + 400-1500 字 markdown content + 来源白名单
- 穿搭 (`recommend.py:121-135`): 给衣橱 items JSON + 场景,要求 `{top, bottom, occasion, tips}`,strict retry 加 "以 { 开头以 } 结尾"

**来源白名单 + 数值校验**: 仅健康文章生成 `app.py:1683-1691` 强制 — 必须在 `["WHO","中国居民膳食指南","中国国家卫健委","中国营养学会","ACOG","Lancet","NEJM","JAMA","CDC","中国疾控"]` 内,且禁用词 `["绝对","100%有效","包治","神药","立竿见影"]`。

**1h 缓存**: `llm.py:14` `_cache: dict[str, tuple[float, str]]` in-memory,重启失效;key = `f"{prefix}:{sha256(query|system)[:16]}"`。

**chat 路径特别说明**: `chat.js:160` 走 `window.API_BASE + /api/chat`,**不经 laopodada-api**,直连 nginx 8088 反代的 atlas 18793。

## 数据模型 schema

SQLite WAL 模式 (`app.py:101`),6 张表 (初始化于 `init_db()`, `app.py:113-188`):

**wardrobe_items** — 衣橱单件
- `id` TEXT PK (uuid hex[:16])
- `title`, `brand`, `color`, `season`, `note` TEXT NULL
- `category` TEXT NOT NULL (enum: top/bottom/dress/outerwear/shoes/bag/accessory)
- `original_url`, `list_url`, `thumb_url` TEXT
- `bytes_orig` INTEGER
- `created_at`, `updated_at` INTEGER (unix ts)
- 索引: `idx_wardrobe_category(category)`, `idx_wardrobe_created(created_at DESC)`

**recipes** — 菜谱
- `id` TEXT PK
- `title` NOT NULL, `category` NOT NULL (breakfast/lunch/dinner/snack/dessert/drink), `difficulty` NOT NULL (easy/medium/hard)
- `prep_minutes`, `cook_minutes`, `servings` INTEGER
- `ingredients`, `steps` TEXT NOT NULL (`\n` 分隔)
- `tags` TEXT (`,` 分隔), `note`, `cover_url` NULL, `bytes_cover`
- `created_at`, `updated_at` INTEGER
- 索引: `idx_recipe_category`, `idx_recipe_difficulty`, `idx_recipe_created DESC`

**outfits** — 规则引擎推荐结果 (历史)
- `id`, `occasion` NOT NULL, `season`, `item_ids` TEXT (JSON array), `reason`, `llm_note`, `style_score` REAL (0..1), `created_at`
- 索引: `idx_outfits_occasion`, `idx_outfits_created DESC`

**outfit_feedback** — 反馈
- `outfit_id` TEXT FK→outfits.id, `score` INTEGER CHECK IN (-1,0,1), `created_at`
- 索引: `idx_outfit_feedback_outfit`
- 用于 `_rule_pick` 偏好加成 (`app.py:1325-1332`, `pref_boost = 0.1 * AVG(score)`)

**outfit_recommendations** — LLM 推荐结果
- `id`, `session_id`, `context`, `recommended_ids` JSON, `created_at`
- 索引: `idx_recommendations_session`, `idx_recommendations_created DESC`

**health articles** — **不存 DB**,仅 in-memory `HEALTH_ARTICLES` list (`app.py:549-1058`),AI 生成的也只 append 到 list。

## API 总表

`laopodada-api/app.py` 共 **22 个 endpoint** (含 1 个 OPTIONS 兜底 = 23 个 route 装饰器)。base URL: `https://123.57.107.21:8088` (生产), `http://192.168.1.10:8097` / `http://10.0.2.2:8097` (本地 iOS sim / Android emu)。

| # | Method | Path | 文件:行 | 入参 | 出参 | 错误 |
|---|---|---|---|---|---|---|
| 1 | OPTIONS | `/<path:_>` | app.py:90-92 | — | 204 | — |
| 2 | GET | `/health` | app.py:319-321 | — | `{ok, service, time}` | — |
| 3 | GET | `/images/<path>` | app.py:328-336 | relpath | image bytes | 404 |
| 4 | GET | `/api/v1/items` | app.py:340-358 | `?category=&limit=&offset=` | `{count, items[]}` | — |
| 5 | POST | `/api/v1/items` | app.py:361-394 | multipart `file, category*` | `{item}` | 400/413 |
| 6 | GET | `/api/v1/items/<id>` | app.py:397-403 | — | `{item}` | 404 |
| 7 | DELETE | `/api/v1/items/<id>` | app.py:406-424 | — | `{id, ok}` | 404 |
| 8 | GET | `/api/v1/recipes` | app.py:428-455 | `?category=&difficulty=&tag=&limit=&offset=` | `{count, recipes[]}` | — |
| 9 | POST | `/api/v1/recipes` | app.py:458-519 | JSON body, 可选 cover | `{recipe}` | 400 |
| 10 | GET | `/api/v1/recipes/<id>` | app.py:522-528 | — | `{recipe}` | 404 |
| 11 | DELETE | `/api/v1/recipes/<id>` | app.py:531-545 | — | `{id, ok}` | 404 |
| 12 | GET | `/api/v1/health/articles` | app.py:1061-1074 | `?category=&limit=&offset=` | `{count, articles[]}` | — |
| 13 | GET | `/api/v1/health/articles/<id>` | app.py:1077-1083 | — | `{article}` | 404 |
| 14 | POST | `/api/v1/outfits/recommend` | app.py:1232-1373 | `{occasion*, season, weather, limit}` | `{outfits[], used_strategy[]}` | 400 |
| 15 | POST | `/api/v1/outfits/<id>/feedback` | app.py:1376-1390 | `{score∈{-1,0,1}}` | `{ok, outfit_id, score}` | 400/404 |
| 16 | GET | `/api/v1/outfits` | app.py:1393-1417 | `?limit=` | `{outfits[]}` | — |
| 17 | GET | `/api/v1/outfits/feedback-count` | app.py:1421-1425 | — | `{count, last_feedback_at}` | — |
| 18 | GET | `/api/v1/outfits/<id>` | app.py:1428-1458 | — | `{outfit}` | 404 |
| 19 | POST | `/api/v1/outfit/recommend` | app.py:1483-1529 | `{context, session_id?}` | `{id, top, bottom, occasion, tips}` | 400/503 |
| 20 | GET | `/api/v1/outfit/history` | app.py:1532-1567 | `?session_id=&limit=` | `{recommendations[]}` | — |
| 21 | POST | `/api/v1/recipes/generate` | app.py:1605-1648 | `{query}` | `{recipe}` | 400/422/503 |
| 22 | POST | `/api/v1/health/articles/generate` | app.py:1695-1729 | `{topic, category?}` | `{article}` | 400/422/503 |

**全局错误码**: `400 bad request` (`app.py:1462-1465`), `404 not found` (`app.py:1468-1471`), `413 toolarge` 超 20MB (`app.py:1474-1476`), `422 LLM 生成失败` (菜谱/健康), `503 atlas 不可用`。

**CORS**: `Access-Control-Allow-Origin: *` (`app.py:82-88`),允许 `GET/POST/DELETE/OPTIONS`。

**频率限制**: **无** (单用户自用)。

## 部署架构

**123 云服务器**: `123.57.107.21` (阿里云 ECS)

**端口分配**:
- `8097` — gunicorn laopodada-api (`gunicorn.conf.py:11`),本地直连用
- `18793` — atlas panel.py LLM 中转 (同机,127.0.0.1)
- `8088` — nginx 反代入口 (HTTPS 自签,公网)
- `8091` — nginx APK 公开下载 (公网 HTTP)
- `8443` — nginx 备用 HTTPS

**systemd 单元**:
- `laopodada-api.service` (`laopodada-api/systemd/laopodada-api.service:1-17`) — `WorkingDirectory=/opt/laopodada-api`, `Environment=LAOPODADA_DATA_DIR=/data/laopodada`, `LAOPODADA_PUBLIC_URL=http://123.57.107.21:8088`, `ExecStart=gunicorn -c gunicorn.conf.py app:app`, `Restart=always`, 日志 `>>/opt/laopodada-api/app.log`

**nginx 反代拓扑**:
```
公网 client
  │
  ├─ :8088 (HTTPS 自签) ──┬─ /laopodada/api/* ──► gunicorn :8097 (laopodada-api)
  │                       ├─ /api/chat ──► atlas :18793 (panel.py)
  │                       └─ /images/*   ──► /data/laopodada/images/
  │
  ├─ :8091 (HTTP) ─── /APK/*.apk ──► /data/apks/ 公开 APK 下载
  │
  └─ :8443 ─── 备用
```

**阿里云安全组端口限制**: 仅 `8088/8091/8443/8092/8093` 开放公网;8097/18793 仅 127.0.0.1。

**systemd 单元列表 (当前实际)**: 仅 `laopodada-api.service` (`laopodada-api/systemd/`)。atlas 由独立 systemd 管理(未在本仓)。

## CI/CD

**两个 workflow** (`.github/workflows/`):

**build-android.yml** (`build-android.yml:1-167`):
- 触发: push main 改 `www/**`, `android/**`, `package.json`, `package-lock.json`, `capacitor.config.json`, workflow 文件本身;或 `workflow_dispatch` 手动
- Runner: `ubuntu-22.04`, timeout 30 min
- 步骤: Checkout → Node 22 → JDK 21 (`temurin`) → Android SDK (`platform-tools platforms;android-36 build-tools;36.0.0`) → `npm install --include=dev` (删 lockfile 强制重生成,官方 registry) → 验证 cap binary → `cap sync android` → `./gradlew assembleDebug` (主) + `assembleRelease` (continue-on-error) → 验证 APK 输出 (列 4 处路径 + commit DEBUG-LOG.md 到 `ci-debug-logs` 分支) → upload `laopodada-debug-apk` (7 天) + `laopodada-release-apk` (7 天) + `gradle-debug-log` (1 天)

**build-ios.yml** (`build-ios.yml:1-66`):
- 触发: push main 改 `www/**`, `ios/**`, `package.json`, `package-lock.json`, `capacitor.config.json`, workflow 文件本身;或 `workflow_dispatch` 手动
- Runner: `macos-14`, timeout 30 min
- 步骤: Checkout → Node 22 → Xcode 15.4 → `npm install` (官方 registry) → `cap sync ios` → `xcodebuild -sdk iphonesimulator` (CODE_SIGNING 关闭) → zip `.app` → upload `ios-build` (7 天)

**已知坑**:
- build-android 锁文件必须删,否则锁住 npmmirror hash (`build-android.yml:46`)
- npm 装完要验证 cap 二进制 (有时 .bin/cap 缺失)
- `if-no-files-found: error` → `warn` 改,避免 find 失败炸 build
- `ci-debug-logs` 分支 orphan + force push 写 CI-DEBUG.md

## APK 渠道

**本地 debug build**: `cd android && ./gradlew assembleDebug` → `android/app/build/outputs/apk/debug/app-debug.apk` (4.4 MB, 2026-06-10 14:43 生成于 `local.properties`)。
**CI build + download**: push main → GitHub Actions artifact `laopodada-debug-apk` (7 天保留)。
**123 nginx 8091 公开 URL**: `http://123.57.107.21:8091/APK/...`。
**Android Manifest** (`android/app/src/main/AndroidManifest.xml:1-43`): 单 `MainActivity extends BridgeActivity`,INTERNET 权限,`usesCleartextTraffic=true` + `networkSecurityConfig` (`network_security_config.xml:1-16`) 允许 10.0.2.2/localhost/192.168.1.10/123.57.107.21 明文 + 自签 HTTPS。

**Capacitor 迁移自 Cordova**: 历史 commit `36ba9e2 Capacitor 替换 Cordova 完工 + CORS 修复 + iOS sim 跑通 4 件衣服`,`build-android.yml:2` 标题已标 "(Capacitor)"。

## 已知 bug 清单

**已修复 (按 commit 时间)**:
- **衣橱拍照上传曾丢失**: CC 之前误删,`488e281` 恢复(`wardrobe.js:32-87` sheet + `submitUpload`)
- **AI 聊天直连 atlas 18793 公网被挡**: `92a6af0` 改走 `window.API_BASE` (8088 反代)
- **AI 聊天 reply/response 字段名错**: `92a6af0` 加兜底 (`api.js:160` 读 `data.response || data.reply || data.content || data.message`)
- **主页 404 因 laopodada-api 是 API 不是 web server**: `36ba9e2` 加 CORS + 改 nginx 入口到 laopodada-ios/www 子目录
- **CI 锁文件 + npmmirror hash 问题**: `37211c9` 起反复调试 (`build-android.yml:46` 删 lockfile + 官方 registry)
- **YAML 1.1 'on' 解析为 true**: `0bc1c89` 给 `on` 加引号

**未修 / 已知限制**:
- **AI 健康生成 422 当 LLM 不按 prompt 返 JSON**: `extract_json` (`llm.py:64-114`) 鲁棒化部分修, root cause 在 LLM 偶尔不返纯 JSON, recommend.py `e1b6858` 也加固过
- **nginx 8088 `/images/` location 被 regex 抢**: 上次会话 v9 修
- **nginx `try_files $` 转义 bug**: v9 修
- **阿里云安全组端口限制**: 仅 8088/8091/8443/8092/8093 通公网,8097/18793 仅内网
- **健康文章不落 DB**: AI 生成的 append 到内存 list,重启容器丢失
- **localStorage 数据**: chat_session_id / chat_count / health_read_ids 卸载 App 丢失
- **CORS 允许 `*`**: 单用户自用,生产环境不暴露敏感 endpoint
- **无频率限制**: 单用户无所谓,公网部署理论可被滥用
- **穿搭推荐 fallback 不准确**: `recommend.py:152-159` 当 LLM 全失败时返回前 2 件,可能不是 best match

## 未实现 / 规划中

**代码 placeholder** (反推):
- `www/recommend.html` + `www/js/recommend.js` + `www/recommend.css` 存在完整穿搭推荐页面,但 **index.html 没有 nav 入口** — 用户只能手动访问 `recommend.html`,**主流程无 tab**
- `app.py:1185` `_llm_note` 内嵌的 outfit 规则引擎有 LLM 提示兜底,但代码注释写 "Off by default" — 默认走纯规则
- 5 tab 中没有 "穿搭推荐" 入口 — v7 5-tab 完成后这条独立页面半废
- iOS 端用 SwiftUI (`laopodada-ios/` 子项目),未与 Capacitor 整合 — README 提到但当前未在主仓活跃开发
- 用户登录/多用户: `app.py` 无 user 表,profile 用本地 localStorage 统计
- 推送通知 / 提醒: 未集成 Capacitor Push plugin
- 离线缓存: 仅 health.js 用 localStorage,其他页面无 Service Worker

## 关键文件路径速查表

**前端 (Capacitor webDir=www)**:
- `www/index.html` — 5-tab 主壳 (衣橱/点餐/健康/AI/我的)
- `www/js/config.js` — API base URL (`https://123.57.107.21:8088`)
- `www/js/api.js` — fetch wrapper + 16 个 endpoint 客户端函数 (含 XHR fallback 修 SOP)
- `www/js/wardrobe.js` — 衣橱页 (拍照 + 列表 + 详情 + 删除)
- `www/js/recipe.js` — 点餐页 (列表 + AI 生成 + 手工新建 + 详情)
- `www/js/health.js` — 健康页 (列表 + AI 生成 + 详情 + localStorage 缓存)
- `www/js/chat.js` — AI 聊天 (atlas 经 nginx 8088 反代)
- `www/js/profile.js` — 我的页 (4 统计 + 推荐历史)
- `www/js/app.js` — 入口 (`switchTab` + `toast`)
- `www/js/camera.js` — 旧版独立拍照页 (主流程已被 wardrobe 合并,代码还在)
- `www/js/recommend.js` + `www/recommend.html` + `www/recommend.css` — 独立穿搭推荐页 (无 tab 入口)
- `www/css/app.css` — 5-tab 主题样式 (400 行,粉橙渐变 + 卡片 + chip)

**后端 (laopodada-api/)**:
- `laopodada-api/app.py` — Flask 主入口 (1738 行,22 endpoint,业务规则全在这)
- `laopodada-api/llm.py` — atlas 中转客户端 + 1h 缓存 + JSON 提取
- `laopodada-api/recommend.py` — LLM 穿搭推荐 (独立 API key 解码逻辑)
- `laopodada-api/seed_recipes.py` — 12 道菜谱种子 (idempotent)
- `laopodada-api/gunicorn.conf.py` — 2 workers × 4 threads gthread
- `laopodada-api/systemd/laopodada-api.service` — systemd 单元
- `laopodada-api/tests/test_recommend.py` — 端到端推荐 API 烟测
- `laopodada-api/data/db/laopodada.db` — SQLite DB (含 WAL)

**工程根**:
- `package.json` — Capacitor 8.4 + cordova 12 依赖
- `capacitor.config.json` — appId / webDir / scheme
- `android/` + `ios/` — 原生工程
- `cordova/` — 旧 Cordova 工程 (半废)
- `laopodada-ios/` — SwiftUI iOS 子项目 (半废)
- `.github/workflows/build-android.yml` — CI APK
- `.github/workflows/build-ios.yml` — CI iOS sim
- `BUILD_STEPS.md` — 本地 APK 编译步骤
- `GITHUB_ACTIONS_BUILD.md` — CI 架构说明
- `README.md` — 顶层概览 + 部署拓扑图

---

最后更新:由 老婆哒哒 仓库代码全量扫描自动生成
