# 老婆哒哒 iOS App Store 上线指南

## 前置条件（需要你手动完成）

### 1. Apple Developer 账号
- 注册 [developer.apple.com](https://developer.apple.com)（$99/年）
- 记下 **Team ID**（10位字母数字）

### 2. 创建 App ID
- 登录 [developer.apple.com/account](https://developer.apple.com/account)
- Certificates, Identifiers & Profiles → Identifiers → App IDs → "+"
- Bundle ID: `com.laopodada.app`
- 勾选 Capabilities: 无需额外（我们的 App 不需要 Push/HealthKit 等）

### 3. 创建分发证书
- Certificates → "+" → Apple Distribution
- 按提示生成 CSR，下载 .cer 文件

### 4. 创建 Provisioning Profile
- Profiles → "+" → App Store
- 选择 App ID `com.laopodada.app`
- 选择 Distribution Certificate
- 下载 .mobileprovision 文件

### 5. App Store Connect 创建 App
- 登录 [appstoreconnect.apple.com](https://appstoreconnect.apple.com)
- My Apps → "+" → New App
- 平台: iOS，名称: **老婆哒哒**，Bundle ID: `com.laopodada.app`
- SKU: `laopodada-ios-001`

---

## CI/CD 自动构建流程

### 模拟器构建（自动触发）
- **触发**: push main 到 `www/` `ios/` `package.json` 相关文件
- **产物**: `ios-build.zip`（7天保留）
- **用途**: 本地测试、快速验证

### App Store 构建（手动触发）
- **触发**: GitHub Actions → `Build iOS App Store (Capacitor)` → Run workflow
- **输入版本号**: 如 `1.0.5`
- **产物**: `laopodada-ipa-1.0.5.zip`（30天保留）
- **用途**: 上传到 App Store Connect

### 启用自动上传到 App Store
编辑 `.github/workflows/build-ios-appstore.yml`，将末尾的 `if: false` 改为 `if: true`，并在 GitHub Secrets 配置：
- `APPLE_ID`: 你的 Apple ID 邮箱
- `APPLE_APP_SPECIFIC_PASSWORD`: [appleid.apple.com](https://appleid.apple.com) 生成的应用专用密码

---

## 代码侧已完成

| 项目 | 状态 |
|------|------|
| Info.plist - 显示名"老婆哒哒" | ✅ |
| Info.plist - ATS 允许自签 HTTPS | ✅ |
| PrivacyInfo.xcprivacy 隐私清单 | ✅ |
| exportOptions.plist 导出配置 | ✅ |
| App Icon (1024x1024) | ✅ |
| Build iOS Simulator CI | ✅ |
| Build iOS App Store CI | ✅ |
| 版本号 1.0.5 | ✅ |
| Deployment Target iOS 15.0 | ✅ |

## 版本号同步

记得在 `app.py` 和 `capacitor.config.json` 中同步版本号：
- `ios/App/App.xcodeproj/project.pbxproj` — `MARKETING_VERSION`（已设 1.0.5）
- `package.json` — `version` 字段

---

## 提审 Checklist

- [ ] 隐私政策 URL（App Store Connect 必填）
- [ ] 支持 URL（App Store Connect 必填）
- [ ] 截图（6.7" / 6.5" / 5.5" 至少各 1 张）
- [ ] App 描述（中文）
- [ ] 关键词
- [ ] 分类：生活
- [ ] 年龄分级
- [ ] 出口合规（无加密 = 否）

---

## 本地手动构建 IPA（备选）

```bash
cd ios/App
xcodebuild archive \
  -project App.xcodeproj \
  -scheme App \
  -configuration Release \
  -sdk iphoneos \
  -archivePath build/App.xcarchive

xcodebuild -exportArchive \
  -archivePath build/App.xcarchive \
  -exportPath build/export \
  -exportOptionsPlist exportOptions.plist
```

IPA 在 `ios/App/build/export/App.ipa`