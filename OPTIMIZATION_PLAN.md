# 老婆哒哒 (laopodada) 全面优化方案

**日期**: 2026-06-26
**基于**: 项目代码全量分析 (v10.4, Capacitor 8.4.0 + Flask API)

---

## 一、项目现状总结

老婆哒哒是一个面向单用户(老婆)的私人助理 App,聚焦 **衣橱管理 / 点餐决策 / 健康科普 / AI 闲聊** 四大场景。

### 技术架构
- **客户端**: Capacitor 8.4.0 跨端壳 + vanilla JS/CSS (无框架,无构建步骤)
- **服务端**: Flask 3 + gunicorn + SQLite + MiniMax M3 LLM
- **部署**: 阿里云 ECS,Nginx 反代,GitHub Actions CI 自动构建 APK

### 当前 Tab 结构 (v10)
底部 3 个 Tab: 主页 / 对话 / 我的
主页含 3 张渐变卡片入口(衣橱/点餐/健康),点击跳转后隐藏底部 Tab

---

## 二、界面显示优化

### 2.1 整体视觉升级

**问题**: 当前 UI 使用大量内联样式 (尤其是 `wardrobe.js`, `recipe.js` 的 modal/overlay 全是 inline style),导致样式难维护、不统一。

**优化方案**:

| 项 | 现状 | 优化 |
|---|---|---|
| 设计系统 | 无,每个 JS 文件自建 HTML+inline style | 提取公共 CSS 类: `.overlay`, `.bottom-sheet`, `.modal-box`, `.form-field` |
| 字体 | 仅系统字体栈 | 增加中文优化字体栈: `PingFang SC`, `Hiragino Sans GB`, `Microsoft YaHei` |
| 颜色系统 | `#FF8C94` 硬编码到处散落 | 提取 CSS 变量: `--primary: #FF8C94`, `--accent: #ff5e94`, `--gradient: linear-gradient(135deg, #ff7a45, #ff5e94)` |
| 圆角/阴影 | 8px/12px/16px 混用 | 统一 token: `--radius-sm: 8px`, `--radius-md: 12px`, `--radius-lg: 16px` |
| 间距 | padding/margin 各处不一致 | 统一 4px 基准网格 |

### 2.2 主页优化

**问题**: 主页只有 3 张静态卡片,信息密度低,缺乏个性化。

**优化方案**:
1. **动态问候语** — 根据时间段显示不同问候(早上好/下午好/晚上好),加入日期和天气提示
2. **统计徽标** — 卡片上的统计从"加载中..."改为骨架屏(shimmer loading),而非文字
3. **快捷操作入口** — 主页底部增加"今日穿搭"、"随机菜谱"、"健康小知识"3 个快捷按钮
4. **最近活动流** — 卡片下方增加最近操作记录(最近添加的衣物/最近生成的菜谱)
5. **动画过渡** — 卡片点击加入 `translateY` + `opacity` 过渡,页面切换加 `fadeIn`

### 2.3 各功能页优化

**衣橱页**:
- 网格从 3 列改为 **2 列**,每张卡片更大、图片更清晰(手机端 3 列太小)
- Filter chips 增加计数徽标(如"上装 (5)")
- 卡片长按进入多选模式,支持批量删除
- 详情页增加编辑功能(当前只能查看和删除)
- 图片加载增加渐显动画(当前无过渡)

**点餐页**:
- 菜谱卡片增加 cook_time 标签和食材数量提示
- AI 生成栏改为折叠式(默认收起),减少首屏干扰
- 分类 + 难度双行 filter 改为单行 tab 切换 + 下拉选择
- 新建菜谱表单增加"拍照上传封面图"功能

**健康页**:
- 文章卡片增加已读/未读视觉区分(当前仅 localStorage 计数,无视觉反馈)
- 文章正文改为 Markdown 渲染(当前是纯文本 `white-space: pre-wrap`)
- AI 生成文章改为落库(当前存内存,重启丢失)

**对话页**:
- 聊天气泡增加时间戳显示
- 支持 Markdown 格式渲染(AI 回复常含列表/代码)
- 增加消息重试按钮(AI 不可用时)
- 输入框增加多行支持(当前是单行 `<input>`)

**我的页**:
- 统计卡片增加趋势指示(如"本周新增 3 件")
- 增加设置入口(清除缓存/关于/检查更新)
- 增加数据导出功能

### 2.4 全局交互优化

1. **Toast 组件升级** — 当前 `toast()` 是简单 `display:none/block`,改为从底部滑入 + 自动消失动画
2. **Loading 状态** — 所有 API 调用增加骨架屏/ shimmer,而非"加载中..."文字
3. **页面切换动画** — `switchTab()` 增加淡入淡出,当前是瞬间切换
4. **下拉刷新** — 各列表页增加 `pull-to-refresh` 手势支持
5. **图片懒加载优化** — 当前使用 `loading="lazy"`,增加加载失败占位图
6. **安全区域适配** — Android 全面屏手势导航区域适配(当前 `env(safe-area-inset-bottom)` 仅在 tabbar 使用)

---

## 三、安卓端设计优化

### 3.1 Android 原生层优化

**问题**: `MainActivity.java` 是空壳(仅继承 `BridgeActivity`),所有 UI 在 WebView,未利用任何原生能力。

**优化方案**:

| 优化项 | 详情 |
|---|---|
| **状态栏** | 设置沉浸式状态栏(transparent status bar),让 WebView 内容延伸到状态栏下方,与粉橙渐变 header 融合 |
| **启动屏** | 当前使用默认 splash.png,替换为品牌色(#FF8C94)渐变启动屏,增加动画过渡到 WebView |
| **主题色** | `styles.xml` 当前是默认 Material 主题,改为自定义品牌色 `colorPrimary=#FF8C94` |
| **应用图标** | 当前是 Capacitor 默认图标,设计品牌专属图标(适配 adaptive icon) |
| **APK 名称** | `capacitor.config.json` 的 `appName` 是 "laopodada",改为"老婆哒哒" |
| **版本管理** | `versionCode=2, versionName=1.0.4`,建议改为语义化版本自动递增 |

### 3.2 Android Capacitor 插件集成

**当前未使用的原生能力(强烈建议集成)**:

| 插件 | 用途 | 优先级 |
|---|---|---|
| `@capacitor/camera` | 原生相机/相册选择,替代 `<input type="file" capture>` | **高** — 当前 capture 在部分 Android 设备不生效 |
| `@capacitor/filesystem` | 本地文件缓存,支持离线查看衣物图片 | **高** |
| `@capacitor/haptics` | 触觉反馈(上传成功/删除确认) | 中 |
| `@capacitor/status-bar` | 状态栏颜色动态切换 | 中 |
| `@capacitor/keyboard` | 键盘弹出时自动调整布局(当前 chat 输入框会被键盘遮挡) | **高** |
| `@capacitor/share` | 分享菜谱/穿搭到微信 | 低 |
| `@capacitor/network` | 网络状态检测,离线提示 | 中 |

### 3.3 Android Manifest 完善

```xml
<!-- 缺少的权限(按需添加) -->
<uses-permission android:name="android.permission.CAMERA" />
<uses-permission android:name="android.permission.READ_EXTERNAL_STORAGE" />
<uses-permission android:name="android.permission.WRITE_EXTERNAL_STORAGE" />
<!-- Android 13+ 细分权限 -->
<uses-permission android:name="android.permission.READ_MEDIA_IMAGES" />
```

### 3.4 安全面优化

- 当前 `usesCleartextTraffic=true` 允许所有明文流量,应限制为仅开发环境
- `network_security_config.xml` 白名单过于宽泛,生产环境应仅允许自签证书域名
- `CORS: *` 应改为仅允许 APP 来源

### 3.5 性能优化

| 项 | 现状 | 优化 |
|---|---|---|
| WebView 初始化 | 默认配置 | 启用 `setMixedContentMode(MIXED_CONTENT_COMPATIBILITY_MODE)`,启用 WebView 缓存 |
| 图片加载 | 每次 API 请求拉取 | Capacitor filesystem 插件本地缓存图片 |
| 启动速度 | Splash → WebView 加载 | 预加载 WebView,缓存 `index.html` |
| APK 体积 | 4.4 MB | 移除 Cordova 遗留代码(`cordova/` 目录可删除),启用 R8 压缩 |
| DOM 操作 | 每次切换 Tab 完全重建 innerHTML | 改为显示/隐藏 + 增量更新 |

---

## 四、功能优化

### 4.1 高优先级

1. **穿搭推荐页接入主流程**
   - 当前 `recommend.html/js/css` 存在但无 Tab 入口,用户无法触达
   - 方案: 主页增加"今日穿搭"快捷入口,或在衣橱页 header 增加"穿搭推荐"按钮

2. **健康文章持久化**
   - 当前 AI 生成的健康文章仅存内存,服务重启丢失
   - 方案: 新增 `health_articles` 数据库表,`POST /api/v1/health/articles/generate` 改为 INSERT

3. **离线缓存**
   - 当前仅健康页有 localStorage 降级
   - 方案: Service Worker 缓存静态资源 + API 响应,衣橱/菜谱数据本地缓存

4. **图片上传优化**
   - 当前拍照后立即调用 AI 自动识别(autoTag),失败则静默回退
   - 方案: 增加手动填写优先级,autoTag 作为辅助;支持批量上传

5. **搜索功能增强**
   - 当前菜谱搜索是 API 端模糊搜索,健康文章是客户端过滤
   - 方案: 统一为客户端即时搜索(减少网络请求),增加"最近搜索"记录

### 4.2 中优先级

6. **穿搭推荐升级** — 从规则引擎(随机 2-3 件)升级为 LLM + 用户偏好反馈的智能推荐
7. **数据统计增强** — 我的页面增加"本周添加"、"最常穿搭"等有意义统计
8. **推送提醒** — 集成 Capacitor Push,定时推送"今天穿什么"提醒
9. **多图上传** — 衣橱支持一次选择多张照片批量上传

### 4.3 低优先级

10. **用户系统** — 虽然当前单用户,但增加简单 PIN 锁保护隐私
11. **数据导出/备份** — 支持导出衣橱/菜谱数据为 JSON
12. **深色模式** — 跟随系统暗色模式切换

---

## 五、代码架构优化

### 5.1 前端架构

**问题**: 所有 JS 是全局函数,无模块化,`escapeHtml` 在 `recipe.js`, `health.js`, `chat.js` 重复定义 3 次。

**优化方案**:

```
www/
  js/
    utils.js          ← 公共工具(escapeHtml, toast, loading)
    api.js            ← 保持不变(已良好封装)
    config.js        ← 保持不变
    components.js    ← 公共 UI 组件(modal, bottom-sheet, filter-bar, empty-state)
    app.js            ← 入口,路由管理
    main-page.js      ← 主页
    wardrobe.js      ← 衣橱
    recipe.js         ← 菜谱
    health.js         ← 健康
    chat.js           ← 对话
    profile.js        ← 我的
    ai-fab.js         ← AI FAB 组件
```

### 5.2 状态管理

**问题**: 状态分散在各文件的全局变量中(`wardrobeFilter`, `recipeFilter`, `healthFilter`, `chatSessionId`),切换 Tab 时状态丢失。

**优化方案**:
- 创建简单的 `window.appState` 对象,统一管理所有页面状态
- Tab 切换时保留滚动位置和筛选条件
- API 响应缓存,避免重复请求

### 5.3 后端优化

- `app.py` 已 1738 行,建议拆分为 Blueprint:
  - `routes/wardrobe.py`
  - `routes/recipe.py`
  - `routes/health.py`
  - `routes/outfit.py`
  - `routes/chat.py`
- `llm.py` 的 1h 内存缓存在 2 worker 模式下不同步,改为 Redis 或 SQLite 缓存
- 健康文章从内存改为 DB 持久化

### 5.4 清理遗留代码

- 删除 `cordova/` 目录(已迁移到 Capacitor)
- 删除 `www/js/camera.js`(已合并到 wardrobe.js)
- 删除 `www/recommend.html/js/css`(未使用的独立穿搭推荐页)
- 删除 `laopodada-ios/`(SwiftUI 子项目,已不在活跃开发)

---

## 六、实施优先级排序

### Phase 1: 界面基础优化 (1-2 周)
1. 提取 CSS 变量和公共组件
2. 消除重复 `escapeHtml`,统一 `utils.js`
3. 衣橱网格改为 2 列
4. Toast/Loading 组件升级
5. 状态栏沉浸式 + 启动屏品牌化

### Phase 2: 功能补全 (2-3 周)
6. 穿搭推荐接入主流程
7. 健康文章落库
8. 集成 Capacitor Camera/Keyboard 插件
9. 对话页多行输入 + 时间戳
10. 衣橱详情增加编辑功能

### Phase 3: 体验升级 (2-3 周)
11. 离线缓存 Service Worker
12. 页面切换动画 + 骨架屏
13. 下拉刷新
14. 搜索统一优化
15. APK 体积优化 + Cordova 遗留清理

### Phase 4: 架构演进 (3-4 周)
16. 前端模块化重构
17. 后端 Blueprint 拆分
18. LLM 缓存升级
19. 数据导出/备份
20. 深色模式

---

## 七、关键技术决策

| 决策点 | 建议 | 理由 |
|---|---|---|
| 是否引入前端框架 | **暂不引入** | 项目规模小,vanilla JS 足够,引入 React/Vue 会增加 CI 复杂度 |
| 是否迁移到 Kotlin 原生 | **暂不迁移** | Capacitor WebView 性能满足需求,维护成本低 |
| 后端是否迁移到 FastAPI | **可选** | Flask 足够,但 FastAPI 的 async + 自动文档对后续维护更有利 |
| 数据库是否迁移到 PostgreSQL | **暂不迁移** | 单用户 SQLite 够用,文件级部署简单 |
| 是否引入 Redis | **可选** | 仅当 LLM 缓存同步成为实际问题时再引入 |
