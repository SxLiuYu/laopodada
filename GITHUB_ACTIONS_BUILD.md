# Android CI Build — GitHub Actions

## 概览

iOS 模拟器本机跑端到端被卡(缺 iOS 26 runtime,7GB),改走 GitHub Actions CI 跑 Android APK build。CI runner **自带 Android SDK** + JDK 17 + Gradle,Mac 本地啥也不用装。

## 1. 加 workflow 文件

新建 `~/repos/laopodada/.github/workflows/build-android.yml`:

```yaml
name: Build Android APK

on:
  push:
    branches: [main]
    paths:
      - 'cordova/**'
      - '.github/workflows/build-android.yml'
  workflow_dispatch:  # 手动触发

jobs:
  build:
    runs-on: ubuntu-latest
    timeout-minutes: 30

    steps:
      - uses: actions/checkout@v4

      - name: Setup Node
        uses: actions/setup-node@v4
        with:
          node-version: '20'

      - name: Setup Java
        uses: actions/setup-java@v4
        with:
          distribution: 'temurin'
          java-version: '17'

      - name: Setup Android SDK
        uses: android-actions/setup-android@v3

      - name: Install Cordova
        run: npm install -g cordova@12

      - name: Build Debug APK
        run: |
          cd cordova
          cordova platform add android  # 第一次跑
          cordova build android --release --buildConfig=build.json

      - name: Upload APK artifact
        uses: actions/upload-artifact@v4
        with:
          name: laopodada-apk
          path: cordova/platforms/android/app/build/outputs/apk/release/app-release.apk
          if-no-files-found: error
```

## 2. 配 signing

`~/repos/laopodada/cordova/build.json`(本机已有,跟 `release-signing.properties` 配对):

```json
{
  "android": {
    "release": {
      "keystore": "release.keystore",
      "storePassword": "laopodada2024",
      "alias": "laopodada",
      "password": "laopodada2024",
      "keystoreType": "jks"
    }
  }
}
```

keystore 文件**不入仓**(用 GitHub Actions secret 注入)。简化起见 debug keystore 也跑得通。

## 3. 触发

```bash
cd ~/repos/laopodada
mkdir -p .github/workflows
# 把上面 yaml 粘到 .github/workflows/build-android.yml
git add .github/workflows/build-android.yml
git commit -m "ci: Android APK build workflow"
git push origin main
```

去 https://github.com/SxLiuYu/laopodada/actions 看 build 状态,跑完下载 artifact `laopodada-apk`。

## 4. 已知坑

- **第一次跑 `cordova platform add android` 慢**(~3 分钟),后续用 cache
- **Gradle 8.x** + JDK 17 配 Cordova 12 稳,Cordova 11 配 JDK 11
- **签名失败**先 `cat ~/.gradle/init.d/init.gradle` 确认 mirror 通
- **Build timeout 30 min** 够,首次 15-20 min

## 5. 不在本机 build 的理由

- Mac 本地无 Android SDK 装(数 GB)
- CI runner 免费 2000 min/月 私仓
- 自动跨 SDK 版本(JDK 17 / Gradle 8 / compileSdk 34)保证可复现
- artifact 30 天可下,review + 设备分发都用 artifact
