# APK v10 — 主页重构 + AI 嵌 tab 内 设计文档

**日期**: 2026-06-15
**作者**: SxLiuYu + Hermes
**项目**: laopodada Capacitor App
**状态**: 设计已批准,待 writing-plans 出实施计划

## 1. 背景与目标

v9 APK 5 tab 模式(衣橱/点餐/健康/AI聊天/我的)经用户实际使用后,存在以下问题:
- 6 tab 候选(加穿搭)拥挤
- "AI聊天"独立 tab 但其他 tab 也有 AI 功能(AI 菜谱推荐、AI 健康生成),tab 命名不一致
- 用户心智混乱:"AI 到底是 tab 还是功能?"

**核心目标**:
- 3 大主功能(衣橱/点餐/健康) + 1 AI 通用对话 + 1 我的
- AI 能力嵌各主功能 tab 内,不单独占 tab
- 主页作为"功能总览"页,3 大卡片入口

## 2. 用户旅程

```
[首屏:主页]
  → 3 张大渐变卡片(衣橱/点餐/健康)+ 底部 3 tab(主页/对话/我的)
  → 用户点衣橱卡片
  → [衣橱 tab]:顶部 filter + 衣物 2/3 列网格 + 右下渐变 ✨ AI FAB + 底部黑色 📷 添加衣物横条
  → 用户点 ✨ AI 浮动按钮
  → [AI 弹窗/底部 sheet] 输入"今日穿搭"
  → 调 POST /api/v1/outfits/generate
  → 返回搭配建议 + 调用衣橱单品图片
```

## 3. UI 设计(已批准)

### 3.1 主页(3 卡片)
**G 方案**(screen-3-3cards-ai.html)

```
┌────────────────────────┐
│  嗨,老婆 👋            │
│  今天想做点什么?        │
│                        │
│  ┌──────────────────┐  │
│  │ 👗 衣橱          │  │
│  │ 2 件单品 · 智能搭配│  │
│  │ ✨ AI 穿搭推荐    │  │
│  └──────────────────┘  │
│  ┌──────────────────┐  │
│  │ 🍳 点餐          │  │
│  │ 15 道菜谱 · 不知道吃啥?│
│  │ ✨ AI 菜品推荐    │  │
│  └──────────────────┘  │
│  ┌──────────────────┐  │
│  │ 💪 健康          │  │
│  │ 9 篇科普 · 想了解啥?│
│  │ ✨ AI 健康科普    │  │
│  └──────────────────┘  │
├────────────────────────┤
│ [主页] [对话] [我的]    │
└────────────────────────┘
```

### 3.2 衣橱 tab(K3 方案)
```
┌────────────────────────┐
│ 衣橱     12 件    🔍  │
│                        │
│ [全部 12] [上衣 5] [下装 3] [外套 2] │
│                        │
│ ┌──┐ ┌──┐ ┌──┐        │
│ │  │ │  │ │  │        │
│ └──┘ └──┘ └──┘        │
│ ┌──┐ ┌──┐ ┌──┐        │
│ │  │ │  │ │  │        │
│ └──┘ └──┘ └──┘        │
│                        │
│ ┌────────────────────┐│
│ │ 📷 添加衣物到衣橱   ││ ← 黑色横条按钮
│ └────────────────────┘│   ┌──┐
│                       │   │✨│ ← 渐变 AI FAB
│                       │   └──┘
├────────────────────────┤
│ [主页] [对话] [我的]    │
└────────────────────────┘
```

### 3.3 点餐/健康 tab
K 方案(单 FAB,无拍照):
```
┌────────────────────────┐
│ 点餐     15 道    🔍  │
│                        │
│ [推荐] [中式] [西式]  │
│ ┌──┐ ┌──┐ ┌──┐        │
│ │  │ │  │ │  │ 卡片  │
│ └──┘ └──┘ └──┘        │
│                        │
│                       ┌──┐
│                       │✨│ ← 渐变 AI FAB(单按钮)
│                       └──┘
├────────────────────────┤
│ [主页] [对话] [我的]    │
└────────────────────────┘
```

### 3.4 对话 tab
保留 v9 完整 chat.js 流程(3.95MB APK 装过的版本),但 UI 微调:
- 顶部加返回主页按钮
- 下方 3 tab 同其他 tab

### 3.5 我的 tab
保留 v9 统计卡片。

## 4. 数据流 & API

### 4.1 已有 API(不需改)
- `GET /api/v1/items` 衣物列表
- `POST /api/v1/items` 衣物上传(multipart `file` + `category`)
- `GET /api/v1/items/{id}` 单个衣物
- `DELETE /api/v1/items/{id}` 删除
- `GET /api/v1/recipes` 菜谱列表
- `GET /api/v1/recipes/{id}` 单个菜谱
- `POST /api/v1/recipes/generate` AI 生成菜谱(已有)
- `GET /api/v1/health/articles` 健康文章列表
- `GET /api/v1/health/articles/{id}` 单篇文章
- `POST /api/v1/health/articles/generate` AI 生成健康文章(已有,extract_json 鲁棒版)
- `POST /api/chat` atlas 通用聊天(via nginx 8088 反代)

### 4.2 需新增 API
- `POST /api/v1/outfits/generate` AI 穿搭推荐
  - 请求: `{ "occasion": "casual/date/work/...", "weather": "hot/mild/cold" }`
  - 响应: `{ "outfit": { "items": [{"id": "...", "url": "..."}], "description": "...", "tips": "..." } }`
  - 后端:从衣橱 items 随机选 2-3 件 + LLM 生成搭配描述
  - 安全:1h 缓存,atlas 转 minimax M2.7

### 4.3 字段映射修正
- 后端 create item 返回 `thumb_url`,前端用 `thumbnail_url`(SPEC.md 此前误标)
- 前端用 `it.thumb_url || it.thumbnail_url || it.original_url` 兜底

## 5. 组件 & 文件结构

### 5.1 新增文件
- `www/css/ai-fab.css` — 浮动按钮样式(渐变 + 阴影)
- `www/js/ai-fab.js` — 浮动按钮通用组件 + 触发 AI 弹窗
- `www/css/main-page.css` — 主页 3 卡片样式
- `www/js/main-page.js` — 主页卡片渲染 + 跳 tab

### 5.2 重构文件
- `www/index.html` — 改 5 tab → 3 tab,加主页 page 容器,移除旧 page 容器
- `www/js/app.js` — 改 switchTab 支持 3 tab,加主页卡片逻辑
- `www/js/wardrobe.js` — 已在 v8/v9 加回拍照;v10 调整为 K3 模式
- `www/js/recipe.js` — 加 AI 浮动按钮触发
- `www/js/health.js` — 加 AI 浮动按钮触发
- `www/js/chat.js` — 微调顶部返回按钮

### 5.3 后端新增
- `laopodada-api/outfits.py` — 穿搭推荐 endpoint 逻辑
- `laopodada-api/app.py` — 注册新 route

## 6. 错误处理

- LLM 超时(>120s):前端展示"AI 正在思考,请稍候",不报错
- LLM 不返 JSON(extract_json 失败):后端 422 + 友好提示"主题太专业,试试更常见的"
- 衣橱为空,点 AI 穿搭:前端拦截,弹"请先添加衣物"
- 拍照上传失败(>20M,格式不支持):前端 toast 提示
- 网络断开:onclick 兜底,localStorage 缓存上次列表

## 7. 测试计划

### 7.1 后端(curl)
- `GET /api/v1/items?category=top` 返回 ≥1 件
- `POST /api/v1/outfits/generate` occasion=casual 返回 200 + 2-3 个单品 + 描述
- LLM 异常(故意填超大 context):500 + 友好错误

### 7.2 前端(Playwright 或 http.server + 浏览器)
- 主页加载:3 卡片可见,3 tab 可见
- 切到衣橱 tab:filter 渲染,2/3 列网格,黑色横条 + 渐变 FAB 可见
- 切到点餐 tab:无拍照横条,只 1 渐变 FAB
- 切到健康 tab:同点餐
- 切到对话 tab:聊天界面可输入
- 切到我的 tab:4 统计卡片显示
- 点主页衣橱卡片 → switchTab('wardrobe') 工作
- 衣橱 tab 拍照 → multipart POST → 200 → 网格新增 1 个

### 7.3 端到端 APK(用户在 123 下载)
- 装 APK 启动:看到 3 tab 主页
- 主页点衣橱 → 衣橱 tab
- 衣橱 tab 点 ✨ AI → 弹窗输入"今日穿搭" → 后端生成 → 显示搭配
- 拍照上传:选 1 张 → 上传成功 → 网格显示

## 8. 实施阶段

按 `writing-plans` skill 即将产出详细计划;粗粒度:
1. 后端 `outfits.py` + 测
2. 前端 `ai-fab.js` 通用组件
3. 前端 `index.html` 改 3 tab + `main-page.js` 主页卡片
4. 各 tab JS 加 FAB 触发
5. CI 触发 + APK v10 build + 同步 123

## 9. 风险

- LLM 抽风不返 JSON(已知,extract_json 鲁棒版已修)
- 阿里云 8088 /api/chat(/.*)?$ regex 需保留
- 用户已装 v8/v9 APK,Capacitor 升级可能需 capacitor sync
- 3 tab 跟之前 5 tab 状态管理差异,需清理 localStorage 旧 key

## 10. 验收标准(DoD)

- [ ] 主页 3 卡片 + 3 tab 视觉与 spec 一致
- [ ] 衣橱 tab K3:黑色横条 + 渐变 FAB 共存
- [ ] 点餐/健康 tab 各 1 渐变 FAB
- [ ] AI 穿搭 endpoint 200 + 2-3 单品 + 描述
- [ ] 拍照上传 multipart 200 + 网格更新
- [ ] 切 tab 不闪屏,状态保留
- [ ] CI APK build success,APK 装机能跑通
- [ ] 用户在 123 下载 APK 实测 OK
