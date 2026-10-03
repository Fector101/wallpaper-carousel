# Testing the update flow without GitHub

Waller checks GitHub for new releases and downloads the APK from there. This
guide covers testing that whole flow — release check, notes, download, resume,
install — with **no internet access and nothing deployed to GitHub**.

A fake GitHub runs on your laptop and the phone talks to it directly. Nothing
leaves your machine, and no real release is created or consumed.

## What is covered

| layer | what it proves | needs a phone |
| --- | --- | --- |
| pytest | endpoint override, version check, notes, download, progress, resume/restart, timeouts, error handling, notification intent payloads | no |
| device E2E | the real app really fetches the release JSON and notes and downloads a byte-identical APK over real HTTP | yes |
| Java notifier | Java-side release check and notification build | yes, manual |

## Files

| file | role |
| --- | --- |
| `local_release_server.py` | fake GitHub: release JSON, APK, notes, Range handling, request log |
| `test_release_download_local.py` | the pytest layer (28 tests, ~9s) |
| `update_download_e2e.py` | the device E2E driver, standalone and executable |

## The loop

Two commands. **No version files need editing.**

```shell
venv/bin/python app_src/tests/update_download_e2e.py --build-new-apk --install
```

Note the `advertising as new:` line near the top. Then **tap Install** on the
phone's system installer, and finish with:

```shell
venv/bin/python app_src/tests/update_download_e2e.py --verify-installed --version 1.0.15
```

The advertised version is always one above whatever the phone currently has, so
you just read it off the output each time. Repeat as often as you like.

Expected output (the exact version numbers depend on your tree and what the
phone currently has installed):

```
==> Checking the device
  device: H6YPAAWSYLP7CAIN
  app VERSION in source: 1.0.10
  installed versionName: 1.0.16
  advertising as new:    1.0.17
  temporarily setting buildozer.spec to version=1.0.17 android.numeric_version=102410013
  (android.numeric_version is not in buildozer.spec; injecting it for this build only)
  buildozer.spec restored
  full build log: bin/e2e-build.log
  [PASS] the served APK really is the version we advertise
  waller-1.0.15-arm64-v8a_armeabi-v7a-debug.apk  64393415 bytes  sha256=7ecf838b1f24d5c5...

==> Starting the local release server
  adb reverse tcp:8000 -> this machine

==> Clearing cached APKs so the download really runs
  removed cached waller-v1.0.14.apk

==> Pointing the app at the local server
  api_url  http://127.0.0.1:8000/repos/Fector101/wallpaper-carousel/releases/latest
  base_url http://127.0.0.1:8000/releases/download

==> Restarting the app -- the auto-check runs because an override is present
  [PASS] the app fetched the release JSON from this laptop
  [PASS] the app then fetched the release notes from this laptop

==> Asking the app to download the new release
  [PASS] the app downloaded from http://127.0.0.1:8000/releases/download
  [PASS] the app reported the download finished

==> Comparing what landed on the phone against what was served
  [PASS] waller-v1.0.15.apk is in the app's files dir
  [PASS] size matches
  [PASS] sha256 matches
  fresh download, no Range header sent

==> Firing the install intent
  [PASS] the app asked the system installer to open

PASS end-to-end release download verified
removed the endpoint override from the device
```

`--build-new-apk` writes buildozer's output to `bin/e2e-build.log` rather than
flooding your terminal, and shows the tail only if the build fails.

## While you are coding

The pytest layer is the fast loop. It drives the real production functions
against the same fake server, and needs no phone:

```shell
venv/bin/python -m pytest app_src/tests/test_release_download_local.py -q
```

Run it after every change to `app_src/ui/screens/download_apk_screen.py`,
`app_src/utils/update_checker.py`, or the Java notifier's Python side.

## Skipping the rebuild

If you only changed Python logic, serve an APK that is already built:

```shell
venv/bin/python app_src/tests/update_download_e2e.py \
  --apk bin/waller-1.0.15-arm64-v8a_armeabi-v7a-debug.apk --version 1.0.15 --install
```

This works while the phone is on a lower version. Once you confirm an install,
that APK is spent and you need `--build-new-apk` again.

## One-time setup

### 1. Allow cleartext HTTP

`targetSdk` is 36, so plain `http://` is refused by default. This file is
gitignored, and `app_src/android/p4a/hook.py` only injects
`android:networkSecurityConfig` when it exists — so a clean checkout (CI, a
release build) is unaffected.

```shell
cat > app_src/android/res/xml/network_security_config.xml <<'EOF'
<?xml version="1.0" encoding="utf-8"?>
<network-security-config>
    <base-config cleartextTrafficPermitted="true" />
</network-security-config>
EOF
```

The manifest is generated at build time, so this needs a rebuild, not just an
app restart.

### 2. Put a debuggable build on the phone

The test pushes the endpoint file into the app's private dir with `run-as` and
pulls the downloaded APK back out. Android refuses both on a release build, and
a debug APK cannot install over a release one.

```shell
adb uninstall org.wally.waller          # destroys the installed app's data
VIRTUAL_ENV=$PWD/venv PATH="$PWD/venv/bin:$PATH" venv/bin/buildozer android debug
adb install -r bin/waller-*-debug.apk
```

Check it took:

```shell
adb shell "run-as org.wally.waller echo ok"
```

If that errors with `package not debuggable`, the E2E will fail at the
endpoint-push step.

`adb` lives at `~/.buildozer/android/platform/android-sdk/platform-tools/adb` if
it is not on your `PATH`.

### 3. Note the signing requirement

Both the installed app and the served APK must be **debug-signed**. A
release-signed APK from `my-release-key.jks` cannot update a debug build, and
Android fails the install with `INSTALL_FAILED_UPDATE_INCOMPATIBLE`.
`--build-new-apk` handles the served side for you.

## How it works

### The endpoint override

Two hardcoded GitHub URLs became overridable:

| what | default | override |
| --- | --- | --- |
| release JSON | `https://api.github.com/repos/Fector101/wallpaper-carousel/releases/latest` | `WALLER_UPDATE_API_URL` / `api_url` |
| APK + notes | `https://github.com/Fector101/wallpaper-carousel/releases/download` | `WALLER_UPDATE_BASE_URL` / `base_url` |

Resolution order, identical in Python and Java:

1. environment variable
2. `<filesDir>/update_endpoint.json`
3. the GitHub default

- Python: `get_release_api_url()` / `get_release_base_url()` in
  `app_src/ui/screens/download_apk_screen.py`
- Java: `app_src/android/src/UpdateEndpoints.java`

The E2E writes `files/update_endpoint.json` and removes it again in a `finally`
block, so a failed run does not leave the phone pointing at your laptop.

### Reaching the laptop from the phone

`adb reverse tcp:8000 tcp:8000` makes the phone's `127.0.0.1:8000` reach your
laptop, so you never need to know its LAN IP. Use `--lan --host <ip>` to go over
the network instead.

### `versionCode` and `android.numeric_version`

`buildozer.spec` does not carry an `android.numeric_version` line. p4a derives one from
`version` instead, as `"10" + minSdk + folded_version`, so `1.0.11` with `minSdk 24`
becomes `102410011`. That derivation is monotonic, so the line is not needed for normal
builds.

The E2E still pins an exact code, because it has to guarantee the served APK outranks
whatever is on the phone — and the phone can outrank `buildozer.spec`, since the E2E
restores the spec after every run. So for the duration of the build it injects
`android.numeric_version = max(spec value, installed versionCode) + 1`, then writes the
original spec back byte for byte. If the build is killed hard rather than exiting, that
line can survive; `git diff buildozer.spec` will show it.

> Going forward, only raise `version`. Dropping back to a version whose derived code is
> below one already published (for example `1.0.10`, which derives to `102410010`) makes
> Android treat it as a downgrade.

### Why adb intents instead of tapping

Kivy draws to a canvas and exposes nothing to the accessibility tree, so
`uiautomator` cannot find its buttons. `app_src/utils/update_checker.py`
therefore accepts intents:

```shell
adb shell am start -n org.wally.waller/org.kivy.android.PythonActivity \
  --es action open_update --es version 1.0.15
adb shell am start -n org.wally.waller/org.kivy.android.PythonActivity \
  --es action download_update --es version 1.0.15
adb shell am start -n org.wally.waller/org.kivy.android.PythonActivity \
  --es action install_update --es version 1.0.15
```

`--ei apk_size <bytes>` is also accepted on all three, matching what the Java
notifier sends.

## What the E2E asserts

Not just "it did not crash":

- the **laptop** logged a request for the release JSON and for the notes, so the
  phone genuinely talked to your server
- the **phone** logged `Download completed:`
- the APK in `files/` matches the served APK by **size and SHA-256**
- `Called do_android_install` appears in logcat
- `--verify-installed` then confirms `versionName` actually moved

Cleared cached APKs first, so the download always runs for real.

## Flags

| flag | effect |
| --- | --- |
| `--build-new-apk` | build a debug APK one version above the phone (bump is temporary) |
| `--install` | also fire the install intent |
| `--verify-installed --version X.Y.Z` | only check the installed version, then exit |
| `--apk PATH` / `--version X.Y.Z` | serve an APK you already built |
| `--range-mode {honor,ignore,reject}` | how the server answers `Range` |
| `--lan --host IP` | reach the laptop by LAN IP instead of `adb reverse` |
| `--port N` | server port, default 8000 |
| `--timeout N` | seconds to wait per stage, default 180 |
| `--serial` / `--adb` | pick a device or an adb binary |
| `--keep-endpoint` | leave the endpoint override on the phone (debugging) |

`--range-mode ignore` is the interesting one: it makes the server answer `200`
with the whole file even when the client asked for a range, which is what a
resume bug would corrupt. See the next section.

## Testing resume

An interrupted download resumes with a `Range` request. `--range-mode` controls
how the fake GitHub answers one, and is available on the E2E too:

| mode | server answers | what it exercises |
| --- | --- | --- |
| `honor` | `206` + the requested bytes | the normal resume path |
| `ignore` | `200` + the whole file | a server that ignores `Range`; the app **must discard** the partial file instead of appending |
| `reject` | `416` | an unsatisfiable range; the app **must** retry from byte zero |

```shell
venv/bin/python app_src/tests/update_download_e2e.py --range-mode ignore --install
```

`ignore` is the regression case that matters most. Answering `200` with the whole
body for a ranged request used to append that body to the existing partial file,
producing an APK that looked complete but was corrupt. The E2E's SHA-256
comparison catches it, because the phone's bytes no longer match what was served.

`reject` covers the other restart trigger: a `416` means the server considers the
requested range unsatisfiable, so the partial file is worthless and the download
has to start over rather than fail or stay stuck.

To stall a response mid-transfer, construct `ReleaseServer(stall_seconds=...)`
directly. That is how the pytest tests pause a download; neither CLI exposes it.

## Troubleshooting

**`OSError: [Errno 98] Address already in use`**
Two runs at once. The default port is 8000, so wait for the other run to finish,
or pass `--port 8010`.

**`INSTALL_FAILED_UPDATE_INCOMPATIBLE`**
The installed app and the served APK are signed differently. The phone must run
a debug build and the served APK must be debug-signed.

**`package not debuggable` from `run-as`**
The phone has a release-signed install. See one-time setup step 2.

**`ModuleNotFoundError: No module named 'android_notify'` on startup**
A stray space in `buildozer.spec`'s `requirements` line makes a package parse as
a separate value and never install:

```
requirements = ...,android-widgets, android-notify    <- broken
requirements = ...,android-widgets,android-notify     <- fixed
```

The app is fine on desktop because the tests mock `android_notify`, so only a
device build catches this. Check the build log's `All possible dists:` line for
any recipe you expect to be listed.

**The APK is older than your source**
```
warning: waller-1.0.16-...apk is older than app_src/utils/constants.py -- it was served as-is, not rebuilt
```
You served an existing APK after editing the source. The run can still pass, but
it proved nothing about your change. Re-run with `--build-new-apk`.

**`process is bad` / `SecurityException: Unable to start service`**
Android's crash-loop protection, not an app bug — it kicks in after the
wallpaper service is restarted repeatedly. Clear it with:

```shell
adb shell am force-stop org.wally.waller
```

It does not affect the download flow.

**The test hangs waiting for a request**
Check the app actually restarted with the override in place, and that the build
has the cleartext config. `bin/e2e-build.log` and `adb logcat` both help.

## The Java notifier

`UpdateNotifier` reads the same `update_endpoint.json` and sends an `apk_size`
extra so the app can validate a partially downloaded file. Its Python side —
the notification intent payload — is covered by the intent-routing tests. The
Java HTTP call and notification build are manual, because the check runs on a
**7 day** `PeriodicWorkRequest` (`app_src/android/src/WorkScheduler.java`) that
cannot be triggered on demand.

To exercise it, temporarily switch the interval in `WorkScheduler.java` to
`15, TimeUnit.MINUTES` (the shorter interval is already commented out there),
rebuild, and wait for the notification. Reset the cooldown afterwards with
`adb shell pm clear org.wally.waller`.

## Caveat

`--build-new-apk` bumps `buildozer.spec` only and restores it in a `finally`. The
served APK's `utils/constants.py::VERSION` therefore stays at whatever the source
says, so after installing, the settings screen shows the source version while
`versionName` shows the new one, and the app still offers that same version as an
update. Bump the real version in `constants.py`, `buildozer.spec` and `README.md`
together when you cut an actual release — see
`.github/steps-to-create-new-version.md`.

The test itself is unaffected: it always advertises a version above the installed
one. `build_new_apk` rewrites only `buildozer.spec` on purpose — it deliberately does
not touch `constants.py`, so a test run can never leave a source file bumped.