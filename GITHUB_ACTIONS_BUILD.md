# GitHub Actions: Android signed APK 自动构建

> 2026-06-10 / Hermes Agent

## 现状

- iOS workflow `.github/workflows/build-ios.yml` 已就绪(每次 push 自动 build .app 上传 artifact)
- **Android workflow 缺失** — 本地 Mac 无 Android SDK,需要 CI 自动 build

## 推荐:加 `.github/workflows/build-android.yml`

每次 push 到 main,GitHub Actions 自动 build signed APK 并上传 3 天。

## 完整工作流(可直接 copy 进 `.github/workflows/build-android.yml`)

```yaml
name: Build Android signed APK

on:
  push:
    branches: [main]
  workflow_dispatch:  # 允许手动触发

jobs:
  build:
    runs-on: ubuntu-latest
    timeout-minutes: 25

    steps:
      - uses: actions/checkout@v4

      - name: Set up JDK 17
        uses: actions/setup-java@v4
        with:
          java-version: '17'
          distribution: 'temurin'

      - name: Set up Android SDK
        uses: android-actions/setup-android@v3
        with:
          android-version: '34'
          build-tools-version: '34.0.0'
          components: 'platform-tools,platforms;android-34,build-tools;34.0.0'

      - name: Cache Gradle
        uses: actions/cache@v4
        with:
          path: |
            ~/.gradle/caches
            ~/.gradle/wrapper
          key: ${{ runner.os }}-gradle-${{ hashFiles('**/*.gradle*') }}

      - name: Generate debug keystore
        run: |
          mkdir -p ~/.android
          keytool -genkey -v \
            -keystore ~/.android/debug.keystore \
            -alias androiddebugkey \
            -keyalg RSA -keysize 2048 -validity 10000 \
            -storepass android -keypass android \
            -dname "CN=Android Debug,O=Android,C=US"

      - name: Create signing properties
        run: |
          cat > cordova/platforms/android/debug-signing.properties <<EOF
          storeFile=$HOME/.android/debug.keystore
          storePassword=android
          keyAlias=androiddebugkey
          keyPassword=android
          EOF

      - name: Install Cordova
        run: npm install -g cordova@11

      - name: Build APK
        working-directory: cordova
        run: |
          cordova platform add android  # 第一次需要,后续可去掉
          cordova build android --release

      - name: Locate APK
        id: find_apk
        run: |
          find cordova/platforms/android/app/build/outputs -name "*.apk" -type f
          echo "apk_path=$(find cordova/platforms/android/app/build/outputs -name '*.apk' -type f | head -1)" >> $GITHUB_OUTPUT

      - name: Upload APK artifact
        uses: actions/upload-artifact@v4
        with:
          name: android-signed-apk
          path: ${{ steps.find_apk.outputs.apk_path }}
          retention-days: 7
          if-no-files-found: error
```

## 验证流程

1. push 触发 → GitHub Actions 跑 ~8-10 分钟
2. 完成后到 Actions 页下载 `android-signed-apk` artifact
3. APK 可直接装真机:`adb install xxx.apk`
4. 启动 App,baseURL 拼 `:8088/laopodada/api/v1/...`,**注意:手机需能访问 123.57.107.21**

## 关键依赖

- `cordova/platforms/android/debug-signing.properties` 已存在(指向本机 debug.keystore,见 BUILD_STEPS.md)
- CI 上重新生成 keystore(不用带进 repo)
- `cordova/platforms/android/release-signing.properties.example` 是模板,生产 release 用真实 keystore(不入库,加 GH Secrets)

## 已知限制

- iOS build artifact 已有(`.app` zip),Android 这个 workflow **新增**
- 第一次 build 慢(10 分钟,装 SDK + Gradle 缓存),后续快(3-5 分钟)
- 装 APK 到真机需 USB 调试启用 + adb 配对

## 不做的事

- 不在 CI 里跑端到端 UI 测试(太慢,留给真机手动测)
- 不在 CI 里跑后端测试(后端在 123.57 跑,与 CI 无关)
