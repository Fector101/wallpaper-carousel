
# Important

- adb install does NOT sync assets incrementally
So if new assets added it doesn't add new files
- This works to view app data

```shell
adb shell
run-as org.wally.waller
cd files
ls -l
```
How to see WAKE INTENT
```shell
adb logcat | grep Intent
```
```shell
adb logcat | grep -E "python|Wallpapercarousel|BootReceiver"
```
```shell
buildozer android debug && adb install bin/waller-1.0.4-arm64-v8a-debug.apk
```

## Local release server: test the update download without GitHub

Full guide: [`app_src/tests/README.md`](../tests/README.md). Summary below.

`check_update` normally talks to `api.github.com` and `download_apk` to
`github.com/.../releases/download`. Both now resolve through
`get_release_api_url()` / `get_release_base_url()`
(`app_src/ui/screens/download_apk_screen.py`), which read an override from
`WALLER_UPDATE_API_URL` / `WALLER_UPDATE_BASE_URL` or from
`update_endpoint.json` in the app's files dir. The Java notifier reads the same
file via `app_src/android/src/UpdateEndpoints.java`.

### 1. Allow cleartext HTTP (dev builds only)

`targetSdk` is 36, so plain `http://` is refused by default. The config file is
gitignored and `app_src/android/p4a/hook.py` only injects
`android:networkSecurityConfig` when the file exists, so CI and release builds
that check out a clean tree are unaffected.

```shell
cat > app_src/android/res/xml/network_security_config.xml <<'EOF'
<?xml version="1.0" encoding="utf-8"?>
<network-security-config>
    <base-config cleartextTrafficPermitted="true" />
</network-security-config>
EOF
```

Then rebuild once (the manifest is generated at build time):
`buildozer android debug`

### 2. Run the device end-to-end test

The phone must have a **debuggable** install. The test pushes
`update_endpoint.json` into the app's private dir with `run-as` and pulls the
downloaded APK back out, both of which Android refuses on a release build.

```shell
# swaps a release install for a debug one -- this deletes the installed app's data
adb uninstall org.wally.waller
buildozer android debug
adb install -r bin/waller-<version>-arm64-v8a_armeabi-v7a-debug.apk
```

Then run the test:

```shell
# builds an APK with a versionCode above the installed one, serves it, and checks
# the bytes that land on the phone against the bytes that were served
venv/bin/python app_src/tests/update_download_e2e.py --build-new-apk --install

# afterwards, after confirming in the system installer on the phone
venv/bin/python app_src/tests/update_download_e2e.py --verify-installed --version <new>
```

It uses `adb reverse tcp:8000 tcp:8000` so the phone reaches this machine on
`127.0.0.1` -- no need to know the laptop's LAN IP. Use `--lan --host <ip>` to go
over the network instead.

`--build-new-apk` sends buildozer's output to `bin/e2e-build.log` instead of
flooding the terminal, and shows the tail only if the build fails.

Both the installed app and the served APK must be **debug-signed**, so that the
install in the system installer does not fail with
`INSTALL_FAILED_UPDATE_INCOMPATIBLE`. `--build-new-apk` handles the served side
for you.

The advertised version is `next_version(max(source VERSION, installed
versionName))`, so it is always a real upgrade. Pass `--version X.Y.Z` to
override, or `--apk path/to.apk` to serve an APK you built yourself.

The test drives the app over adb intents rather than tapping the Kivy UI, because
a Kivy canvas exposes nothing to the accessibility tree. It also clears cached
APKs first, so the download always runs for real, and removes the endpoint
override again in a `finally` block.

### 3. Just the logic, no phone

```shell
venv/bin/python -m pytest app_src/tests/test_release_download_local.py -q
```

`app_src/tests/local_release_server.py` serves the release JSON and the assets on
127.0.0.1 and the tests drive the real production functions against it.

### Driving the flow by hand

```shell
adb shell am start -n org.wally.waller/org.kivy.android.PythonActivity \
  --es action open_update --es version 1.0.11
adb shell am start -n org.wally.waller/org.kivy.android.PythonActivity \
  --es action download_update --es version 1.0.11
adb shell am start -n org.wally.waller/org.kivy.android.PythonActivity \
  --es action install_update --es version 1.0.11
```

### 4. The Java notification path

`UpdateNotifier` reads the same `update_endpoint.json`, and also sends an
`apk_size` extra so the app can validate a partially downloaded file. It is
driven by WorkManager on a **7 day** `PeriodicWorkRequest`
(`app_src/android/src/WorkScheduler.java`), which cannot be triggered on demand.

To exercise it against the local server, temporarily switch the interval in
`WorkScheduler.java` to `15, TimeUnit.MINUTES` (the shorter interval is already
commented out there), rebuild, push the endpoint file, then wait for the
notification. Reset the WorkManager cooldown afterwards with
`adb shell pm clear org.wally.waller`.

The Python side of the notification payload is covered by the intent-routing
tests in `app_src/tests/test_release_download_local.py`, so only the Java HTTP
call and notification build are manual.

### Known caveats of `--build-new-apk`

- It only bumps `version` and `android.numeric_version` in `buildozer.spec`, and
  restores both in a `finally`. The served APK's `utils/constants.py::VERSION`
  therefore stays at the old value, so after installing it the app will still
  offer that same version as an update. Bump the real version to make the
  installed app agree with its `versionName`.
- The debug-only auto-check (which only runs when an override is present) is what
  makes the download leg hermetic. Without an override, a debug build would go
  to the real GitHub API.
## How to Create Release Version

### Release signing, locally
```shell
keytool -genkey -v -keystore my-release-key.jks -alias key-stuff -keyalg RSA -keysize 2048 -validity 10000 -storepass 12345 -keypass 12345 -dname "CN=Fabian, OU=Mobile, O=FabianCorp, L=New York, ST=NY, C=US"
```

```shell
sudo apt install zipalign apksigner
buildozer -v android release
zipalign -v -p 4 bin/waller-1.0.6-arm64-v8a_armeabi-v7a-release-unsigned.apk bin/waller-aligned.apk
apksigner sign --ks my-release-key.jks --ks-key-alias key-stuff --ks-pass pass:123456789 --key-pass pass:123456789 --out bin/waller-signed.apk bin/waller-aligned.apk
apksigner verify --verbose bin/waller-signed.apk
adb install -r bin/waller-signed.apk
```

## On GitHub Actions
Create my-release-key.jks Locally by running

```shell
keytool -genkey -v -keystore my-release-key.jks -alias key-stuff -keyalg RSA -keysize 2048 -validity 10000 -storepass 12345 -keypass 12345 -dname "CN=Fabian, OU=Mobile, O=FabianCorp, L=New York, ST=NY, C=US"
```

Then run `base64 my-release-key.jks > keystore.txt`, Copy its contents to `https://github.com/Fector101/wallpaper-carousel/settings/secrets/actions`
Saved as `KEYSTORE_BASE64` and `copied content`
Save `KEY_PASS` as `123456789`
Save `KS_PASS` as `123456789`

Action File
```yaml
name: Build Android APK

on:
  workflow_dispatch:

jobs:
  build-android:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Get version from constants.py
        id: version
        run: |
          VERSION=$(python -c "from app_src.utils.constants import VERSION; print(VERSION)")
          echo "VERSION=$VERSION" >> $GITHUB_OUTPUT
          echo "Building version: $VERSION"

      - name: Decode keystore
        run: |
          echo "${{ secrets.KEYSTORE_BASE64 }}" | base64 -d > my-release-key.jks

      - name: Build with Buildozer
        uses: n8marti/buildozer-action@fix-user-doesnt-exist
        id: buildozer
        with:
          workdir: .
          buildozer_version: stable
          command: pip install android-widgets; buildozer android release

      - name: Zipalign APK
        run: |
          zipalign -v -p 4 bin/*release-unsigned.apk bin/aligned.apk

      - name: Sign APK
        run: |
          apksigner sign \
            --ks my-release-key.jks \
            --ks-key-alias key-stuff \
            --ks-pass pass:${{ secrets.KS_PASS }} \
            --key-pass pass:${{ secrets.KEY_PASS }} \
            --out bin/waller.apk \
            bin/aligned.apk

      - name: Verify APK
        run: |
          apksigner verify --verbose bin/waller.apk

      - name: Create GitHub Release
        uses: softprops/action-gh-release@v2
        with:
          tag_name: v${{ steps.version.outputs.VERSION }}
          name: Release v${{ steps.version.outputs.VERSION }}
          files: bin/waller.apk

```

## How to Copy from APK directory(running app) to desktop
### Failed
1. ~/.buildozer/android/platform/android-sdk/platform-tools/adb shell "mkdir -p /data/local/tmp/waller_files" — created a temp dir (failed attempt, kept for context)
2. ~/.buildozer/android/platform/android-sdk/platform-tools/adb shell "run-as org.wally.waller sh -c 'cp -r /data/user/0/org.wally.waller/files/. /data/local/tmp/waller_files/'" — failed: Permission denied
3. ~/.buildozer/android/platform/android-sdk/platform-tools/adb shell "chmod 777 /data/local/tmp/waller_files && run-as ... cp ..." — failed again
### Worked
4. ~/.buildozer/android/platform/android-sdk/platform-tools/adb shell "run-as org.wally.waller sh -c 'which tar'" — confirmed tar exists on device
5. ~/.buildozer/android/platform/android-sdk/platform-tools/adb exec-out run-as org.wally.waller tar -cf - -C /data/user/0/org.wally.waller files > /tmp/waller_files.tar — streamed the dir into a local tar
6. mkdir -p ~/Desktop && tar -xf /tmp/waller_files.tar -C ~/Desktop — extracted to ~/Desktop/files/


## How to inject code for hot refresh on debug APK 
```shell
 2045  adb push app_src/ui/widgets/layouts.py /data/local/tmp/layouts.py
 2046  adb shell "run-as org.wally.waller sh -c 'cp /data/local/tmp/layouts.py files/app/ui/widgets/layouts.py'"
 2047  adb shell am force-stop org.wally.waller && adb logcat -c && adb shell monkey -p org.wally.waller -c android.intent.category.LAUNCHER 1
 2048  adb logcat | grep python


```
