# Build signed Android APK (laopodada)
Prereqs: JDK 17 + Android SDK in `PATH`, `ANDROID_SDK_ROOT` exported, `cordova` CLI.
**Local debug:** `cd cordova && npm run build && cd platforms/android && ./gradlew assembleDebug` → `app/build/outputs/apk/debug/app-debug.apk` (signed with `/Users/sxliuyu/.android/debug.keystore` via `debug-signing.properties`).
Install: `adb install -r app/build/outputs/apk/debug/app-debug.apk`.
**Local release:** `keytool -genkey -v -keystore ~/laopodada-release.keystore -alias laopodada -keyalg RSA -keysize 2048 -validity 10000 -dname "CN=laopodada,O=laopodada,C=CN"`; then `cp platforms/android/release-signing.properties.example platforms/android/release-signing.properties` and fill passwords; then `cd cordova && cordova build android --release` → `app/build/outputs/apk/release/app-release.apk`.
**CI (GitHub Actions):** cache `~/.android/debug.keystore` + `debug-signing.properties`; install JDK 17 + SDK; `./gradlew assembleRelease` with `release-signing.properties` populated from repo secrets (don't commit it).
