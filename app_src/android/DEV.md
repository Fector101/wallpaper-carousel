# Important

- adb install does NOT sync assets incrementally
So if new assets added it doesn't add new files
- This works to view app data

```shell
adb shell
run-as org.wally.waller
ls -l files
cd files
```
How to see WAKE INTENT
```shell
adb logcat | grep Intent
```
```shell
adb logcat | grep -E "python|Wallpapercarousel"
```
```shell
buildozer android debug && adb install bin/waller-1.0.4-arm64-v8a-debug.apk
```

How to Create Release Version
## Locally
```python
def download_apk(url="",filename="update.apk"):
    url = url or "http://10.92.3.140:8000/Laner/mobile/bin/waller-1.0.4-arm64-v8a-release.apk"
    try:
        import os
        import requests
        if on_android_platform():
            from android import mActivity
            context = mActivity.getApplicationContext()
            files_dir = context.getFilesDir().getAbsolutePath()
        else:
            files_dir = "./"
        apk_path = os.path.join(files_dir, filename)

        r = requests.get(url, stream=True)

        with open(apk_path, "wb") as f:
            for chunk in r.iter_content(8192):
                if chunk:
                    f.write(chunk)

        print("APK saved to:", apk_path)
        return apk_path

    except Exception as e:
        print("Download failed:", e)
        traceback.print_exc()
        return None

def install_apk(apk_path):
    import os
    from jnius import autoclass
    from android import mActivity

    if not os.path.exists(apk_path):
        print("APK not found:", apk_path)
        return

    Intent = autoclass('android.content.Intent')
    Uri = autoclass('android.net.Uri')
    File = autoclass('java.io.File')

    intent = Intent(Intent.ACTION_VIEW)

    apk_file = File(apk_path)
    uri = Uri.fromFile(apk_file)

    intent.setDataAndType(uri, "application/vnd.android.package-archive")
    intent.setFlags(Intent.FLAG_ACTIVITY_NEW_TASK)

    mActivity.startActivity(intent)

def install_apk15(apk_path):
    import os
    from jnius import autoclass
    from android import mActivity

    if not os.path.exists(apk_path):
        print("APK not found:", apk_path)
        return

    context = mActivity.getApplicationContext()

    Intent = autoclass('android.content.Intent')
    File = autoclass('java.io.File')
    FileProvider = autoclass('androidx.core.content.FileProvider')
    Uri = autoclass('android.net.Uri')

    apk_file = File(apk_path)

    authority = context.getPackageName() + ".fileprovider"

    uri = FileProvider.getUriForFile(
        context,
        authority,
        apk_file
    )

    intent = Intent(Intent.ACTION_VIEW)
    intent.setDataAndType(uri, "application/vnd.android.package-archive")
    intent.setFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
    intent.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)

    mActivity.startActivity(intent)

def get_new_apk(*args):
    print("get_new_apk",args)
    server_ip="pc_ip"
    apk_path = download_apk(url=f"http://{server_ip}:8000/Laner/mobile/bin/waller-1.0.5-arm64-v8a_armeabi-v7a-release.apk")
    if apk_path:
        try:
            install_apk15(apk_path)
        except Exception as e:
            print("install_apk15 failed:", e)
            try:
                install_apk(apk_path)
            except Exception as e1:
                print("install_apk failed:", e1)

```
## Installed On Redmi 15C
python3 -m http.server 8000
keytool -genkey -v -keystore my-release-key.jks -alias key-stuff -keyalg RSA -keysize 2048 -validity 10000 -storepass 12345 -keypass 12345 -dname "CN=Fabian, OU=Mobile, O=FabianCorp, L=New York, ST=NY, C=US"


buildozer -v android release
zipalign -v -p 4 bin/waller-1.0.6-arm64-v8a_armeabi-v7a-release-unsigned.apk bin/waller-aligned.apk
apksigner sign --ks my-release-key.jks --ks-key-alias key-stuff --ks-pass pass:123456789 --key-pass pass:123456789 --out bin/waller-signed.apk bin/waller-aligned.apk
apksigner verify --verbose bin/waller-signed.apk
adb install -r bin/waller-signed.apk

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
### To see Only App Logs
```shell
adb logcat | grep -E "python"
```


## P4a.hook
Peek at AndroidManifest.xml File before editing with [hook.py](p4a/hook.py)
[AndroidManifest.xml Location](../../.buildozer/android/platform/build-arm64-v8a_armeabi-v7a/dists/waller/src/main/AndroidManifest.xml)
