# 老婆哒哒 iOS

iOS 客户端 — SwiftUI + iOS 16+。配套后端 [laopodada-api](../)（Flask, port 8097 on 123.57.107.21）。

## 状态

| 模块 | 状态 | 说明 |
|---|---|---|
| 衣橱 (Wardrobe) | ✅ MVP | 列表 / 详情 / 添加(拍照+相册) / 删除 / 7 大类筛选 |
| 食谱 (Recipe) | 🚧 占位 | 占位 Tab,下个版本 |
| 健康知识 (Health) | 🚧 占位 | 占位 Tab,下个版本 |

## 工程结构

```
laopodada-ios/
├── project.yml                    # XcodeGen spec
├── Sources/
│   ├── App/                       # 入口、AppState、RootView
│   ├── Models/                    # 数据模型
│   ├── Networking/                # APIClient + 模块 API
│   ├── Shared/                    # 通用 UI/工具 (ImagePicker、压缩、Placeholder)
│   ├── Wardrobe/                  # 衣橱模块 (List/Detail/Add + ViewModel)
│   └── Support/Info.plist         # 权限 + ATS 例外
├── Resources/Assets.xcassets/     # AppIcon + AccentColor
└── .gitignore
```

`.xcodeproj` **不入库** — 用 [XcodeGen](https://github.com/yonaskolb/XcodeGen) 从 `project.yml` 生成。

## 开发

### 首次 setup

```bash
brew install xcodegen
cd laopodada-ios
xcodegen generate
open laopodada.xcodeproj
```

### 日常

```bash
# 改完 project.yml 后重新生成
xcodegen generate

# 编译 (模拟器)
xcodebuild -project laopodada.xcodeproj \
  -scheme laopodada \
  -destination 'platform=iOS Simulator,name=iPhone 15' \
  build
```

## 后端接口约定

`APIClient` 默认 baseURL: `http://123.57.107.21:8097`

| 路径 | 方法 | 说明 |
|---|---|---|
| `/api/v1/items?category=...` | GET | 列表 |
| `/api/v1/items/:id` | GET | 详情 |
| `/api/v1/items` | POST (multipart) | 上传,fields: `file`, `category`, `title`, `brand?`, `color?` |
| `/api/v1/items/:id` | DELETE | 删除 |

返回/上传的图片 URL 是绝对地址 (Nginx 直出 `/images/`)。

## 已知限制

- v0.1 无登录,所有数据视为当前用户(单用户模式)
- v0.1 无离线缓存,无 CoreData/SwiftData
- v0.1 无搭配推荐,无 AI 分类
- 上传图片自动压缩到长边 2048px / JPEG 0.8
