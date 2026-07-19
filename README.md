# 老婆哒哒 (laopodada)

> 老婆的私人助理套件 — 衣橱 + 食谱 + 健康知识 + AI 对话 + 记账。原生双端 + 独立后端微服务。

## 子项目

| 目录 | 用途 | 技术栈 | 端口 |
|---|---|---|---|
| [`laopodada-api/`](./laopodada-api/) | 后端 API + 图片存储 | Flask + gunicorn + Pillow + SQLite | 8097 → 8088 |
| `www/` | 前端页面 | Vanilla JS + CSS，无构建步骤 | — |
| `android/` | Android 工程 | Capacitor 8.4 跨端壳 | — |

## 技术栈

### 前端 (www/)
- **框架**: Vanilla JavaScript + CSS，无构建步骤
- **状态管理**: 统一状态管理模块 `state.js`
- **UI 组件**: 公共组件库 `components.js`
- **样式**: CSS Variables + Design Tokens，支持动画和骨架屏
- **API**: fetch wrapper + XHR fallback (Capacitor 环境)

### 后端 (laopodada-api/)
- **框架**: Flask 3 + gunicorn (2 workers × 4 threads)
- **数据库**: SQLite (WAL 模式)
- **图片处理**: Pillow 10+ (3 档 WebP 缩放)
- **LLM**: MiniMax M3 经 atlas panel 中转
- **Blueprint 模块化**: 
  - `outfits.py` — 穿搭推荐
  - `health.py` — 健康文章 (数据库持久化)
- **测试**: pytest + Flask test client

### 移动端
- **跨端框架**: Capacitor 8.4.0
- **Android**: compileSdk 36, JDK 21
- **iOS**: Xcode 15.4 (模拟器构建)

## 部署拓扑

```
┌──────────────────┐        ┌──────────────────────┐
│  iOS / Android   │  HTTPS │  Nginx :8088         │
│      app         │ ─────► │   /laopodada/api/* ──► gunicorn :8097 (laopodada-api)
└──────────────────┘        │   /api/chat     ──► atlas :18793 (panel.py)
                            │   /images/*     ──► /data/laopodada/images/
                            └──────────┬───────────┘
                                       │ proxy_pass
                            ┌──────────▼───────────┐
                            │  gunicorn :8097      │
                            │  Flask laopodada-api │
                            └──────────┬───────────┘
                                       │
                            ┌──────────▼───────────┐
                            │  /data/laopodada/    │
                            │  ├─ images/          │
                            │  │  ├─ original/     │
                            │  │  ├─ list/         │
                            │  │  └─ thumb/        │
                            │  └─ db/laopodada.db  │
                            └──────────────────────┘
```

## 路线图

| 模块 | 状态 |
|---|---|
| **衣橱 (Wardrobe)** | ✅ MVP — 上传/列表/详情/编辑/删除 + 3 层 WebP 缩放 + AI 识别 |
| **食谱 (Recipe)** | ✅ 完整 — 列表/分类筛选/AI 生成/手工录入/详情 |
| **健康知识 (Health)** | ✅ v2 — 列表/分类筛选/AI 生成/已读标记/数据库持久化 |
| **AI 对话 (Chat)** | ✅ 完整 — MiniMax M3 对话/历史记录/快捷入口 |
| **穿搭推荐 (Outfit)** | ✅ v10 — 规则引擎 + LLM 智能推荐/反馈/历史 |
| **记账 (Bookkeeping)** | ✅ 完整 — 支出记录/月度统计/分类管理 |
| **个人中心 (Profile)** | ✅ 完整 — 数据统计/设置/导出/关于 |
| **Android 客户端** | ✅ Capacitor 8.4 + CI 自动构建 |
| **iOS 客户端** | ✅ SwiftUI 子项目 |

## 核心功能

### 1. 衣橱管理
- 📷 拍照/相册上传，AI 自动识别衣物信息
- 🏷️ 分类筛选（8 类：上装/下装/连衣裙/外套/鞋/包/配饰）
- ✏️ 编辑/删除衣物，3 档 WebP 自动缩放
- 🔍 搜索功能（名称/颜色/品牌）

### 2. 点餐决策
- 📋 12 道家常菜种子数据
- 🍳 分类筛选（早餐/午餐/晚餐/零食/甜点/饮品）
- 🤖 AI 一键生成菜谱（LLM 60-90 秒）
- 📝 手工录入菜谱
- 🖼️ 封面图上传

### 3. 健康知识
- 📚 8 篇硬编码健康文章
- 🥗 分类筛选（营养/运动/慢病/心理/女性/预防）
- 🤖 AI 生成健康科普文章（数据库持久化）
- ✅ 已读标记（localStorage）
- 📖 Markdown 渲染支持

### 4. AI 对话
- 💬 MiniMax M3 中文对话
- ⚡ 4 个快捷入口（天气/早餐/笑话/穿搭）
- 📜 历史记录（按 session_id 持久化）
- 🔄 消息重试功能

### 5. 穿搭推荐
- 🎯 规则引擎 + LLM 智能推荐
- 👔 支持多种场合（休闲/上班/约会/运动/派对/居家）
- 📊 风格评分系统（0-1）
- 👍 反馈机制（喜欢/不喜欢）
- 📈 偏好学习（基于反馈调整推荐）

### 6. 记账功能
- 💰 10 种支出分类
- 📊 月度支出统计
- 📈 分类占比分析
- ➕ 快速记账

### 7. 个人中心
- 📊 4 大统计卡片（衣橱/菜谱/记账/支出）
- 🗑️ 清除缓存
- 📤 数据导出（JSON）
- ℹ️ 关于信息

## 前端架构优化

### 模块化结构
```
www/
  js/
    config.js       — API base URL 配置
    utils.js        — 公共工具函数（escapeHtml, toast, modal, bottom-sheet）
    state.js        — 统一状态管理（Proxy 响应式）
    components.js   — 公共 UI 组件库
    api.js          — fetch wrapper + 所有 API 端点
    skeleton.js     — 骨架屏工具函数
    pull-refresh.js — 下拉刷新（Capacitor 原生支持）
    wardrobe.js     — 衣橱页
    recipe.js       — 菜谱页
    health.js       — 健康页（v2 数据库持久化）
    chat.js         — AI 对话页
    bookkeeping.js  — 记账页
    profile.js      — 我的页
    ai-fab.js       — AI 浮动按钮组件
    main-page.js    — 主页
    app.js          — App 入口（路由管理 + 全局错误捕获）
```

### 状态管理
- **统一状态对象**: `state.js` 提供全局状态管理
- **页面状态持久化**: Tab 切换时保留筛选条件和滚动位置
- **临时数据管理**: `temp` 对象管理上传文件、编辑中等临时状态

### UI 组件库
- **Modal/Bottom Sheet**: 统一的弹窗组件，支持点击遮罩关闭
- **Filter Bar**: 可复用的过滤标签栏
- **Skeleton**: 骨架屏加载动画
- **Empty State**: 统一的空状态展示
- **Stat Card**: 统计卡片组件
- **Article/Outfit/Recipe Card**: 各类卡片组件

### 设计系统
- **CSS Variables**: 完整的 Design Tokens（颜色、间距、字体、阴影、圆角）
- **动画系统**: 页面切换、卡片点击、Toast 提示等动画
- **响应式设计**: 4px 基准网格，移动端优先
- **字体优化**: PingFang SC / Hiragino Sans GB / Microsoft YaHei

## 后端架构优化

### Blueprint 模块化
```
laopodada-api/
  app.py              — Flask 主入口（注册所有 Blueprint）
  outfits.py          — 穿搭推荐 Blueprint
  health.py           — 健康文章 Blueprint（数据库持久化）
  llm.py              — LLM 客户端（atlas 中转 + 1h 缓存）
  atlas_client.py     — Atlas LLM 客户端
  db.py               — 数据库访问层（健康文章 CRUD）
  auto_tag.py         — AI 图片识别
  recommend.py        — 穿搭推荐规则引擎
  gunicorn.conf.py    — Gunicorn 配置
```

### 健康文章持久化
- **数据库表**: `health_articles`（id, title, category, summary, content, tags, read_minutes, source, created_at）
- **API 端点**:
  - `GET /api/v1/health/articles` — 列表（支持分类筛选和分页）
  - `GET /api/v1/health/articles/<id>` — 单篇文章
  - `POST /api/v1/health/articles/generate` — AI 生成并持久化
- **内容校验**: 来源白名单 + 禁用词过滤 + 长度校验（100-10000 字）

### 缓存优化
- **LLM 缓存**: 1 小时 in-memory 缓存（按 query+system hash）
- **前端缓存**: localStorage 缓存（健康文章、聊天记录等）
- **图片缓存**: Capacitor filesystem 插件本地缓存（规划中）

## 测试覆盖

### 后端测试
- ** outfits 测试**: `tests/test_outfits.py` (3 个测试用例)
  - 正常生成（200）
  - 空衣橱（422）
  - Atlas 超时（504）

- **健康文章测试**: `tests/test_health.py` (7 个测试用例)
  - 空列表（200）
  - 分类筛选（200）
  - 单篇查询（200）
  - 404 处理（404）
  - AI 生成成功（201）
  - 来源校验失败（422）
  - 禁用词过滤（422）

### 运行测试
```bash
cd laopodada-api
python -m pytest tests/ -v
```

## CI/CD

### GitHub Actions
- **build-android.yml**: Push to main → 自动构建 Debug/Release APK
- **build-ios.yml**: Push to main → 自动构建 iOS Simulator 包
- **触发条件**: 修改 `www/**`, `android/**`, `ios/**`, `package.json`, `capacitor.config.json`

### 本地构建
```bash
# Android Debug
cd android && ./gradlew assembleDebug

# iOS Simulator
cd ios && xcodebuild -sdk iphonesimulator
```

## 环境变量

### 后端
- `LAOPODADA_DATA_DIR`: 数据目录（默认 `/data/laopodada`）
- `LAOPODADA_API_PORT`: API 端口（默认 `8097`）
- `LLM_ROUTER_BEARER`: LLM 路由器认证 token

### 前端
- `window.API_BASE`: API 基础 URL（生产环境 `https://123.57.107.21:8088`）
- `window.IS_DEV`: 开发模式标志（启用 mock 数据）

## 贡献指南

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'feat: add amazing feature'`)
4. 推送分支 (`git push origin feature/amazing-feature`)
5. 创建 Pull Request

## 许可证

MIT
