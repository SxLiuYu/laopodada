# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- 统一状态管理模块 `www/js/state.js`，避免各页面分散维护全局变量
- 公共 UI 组件库 `www/js/components.js`，提供可复用的 modal、bottom-sheet、filter-bar 等组件
- 健康文章数据库持久化模块 `laopodada-api/health.py`，AI 生成的文章现在持久化到数据库
- 健康文章 API 端点：`GET /api/v1/health/articles`、`GET /api/v1/health/articles/<id>`、`POST /api/v1/health/articles/generate`
- 健康文章前端 API 函数 `www/js/api.js` 中新增 `api.health` 命名空间
- 健康文章前端页面 `www/js/health.js` 升级为 v2 数据库持久化版本
- 健康文章测试套件 `laopodada-api/tests/test_health.py`，包含 7 个测试用例
- 页面可见性优化：切换回页面时自动刷新数据
- 全局键盘快捷键：ESC 关闭所有弹窗
- 骨架屏加载动画增强
- 空状态动画增强（bounceIn 效果）
- Toast 成功/错误状态样式变体
- 卡片 hover 效果和自定义滚动条

### Changed
- `laopodada-api/app.py` 注册 health 和 outfits Blueprint
- `laopodada-api/app.py` 修复 outfits Blueprint 注册顺序问题
- `www/index.html` 新增 state.js 和 components.js 脚本引用
- `www/js/app.js` 优化 switchTab 逻辑，增加页面可见性监听
- `www/js/health.js` 完全重写为 v2 数据库持久化版本，支持 prevention 分类
- `www/js/api.js` 新增健康文章相关 API 函数
- `www/css/app.css` 增强骨架屏、页面加载、空状态、Toast 等样式

### Fixed
- 健康文章 AI 生成后重启丢失的问题（现在持久化到数据库）
- outfits Blueprint 未注册导致的 405 Method Not Allowed 错误
- 健康文章前端未使用数据库 API 的问题
- 页面切换时状态丢失问题（通过统一 state 管理）

### Performance
- 统一状态管理减少重复代码和维护成本
- 健康文章数据库持久化避免重复生成
- 骨架屏提升用户感知加载速度
- 页面可见性优化减少不必要的刷新

### Security
- 健康文章生成增加来源白名单验证
- 健康文章生成增加禁用词过滤
- 健康文章内容长度校验（100-10000 字）

## [1.0.0] - 2026-07-19

### Added
- 衣橱管理：拍照/相册上传、分类筛选、详情查看、编辑、删除
- 点餐决策：菜谱列表、分类筛选、AI 生成、手工录入
- 健康知识：文章列表、分类筛选、AI 生成、已读标记
- AI 对话：MiniMax M3 中文对话、历史记录、快捷入口
- 穿搭推荐：规则引擎 + LLM 智能推荐
- 记账功能：支出记录、月度统计、分类管理
- 个人中心：数据统计、设置、导出、关于
- Android 客户端：Capacitor 8.4 跨端壳
- iOS 客户端：SwiftUI 子项目
- CI/CD：GitHub Actions 自动构建 APK

### Technical
- 后端：Flask 3 + gunicorn + SQLite (WAL) + Pillow
- 前端：Vanilla JS + CSS，无构建步骤
- 移动端：Capacitor 8.4 跨端壳
- LLM：MiniMax M3 经 atlas panel 中转
- 部署：阿里云 ECS + Nginx 反代
