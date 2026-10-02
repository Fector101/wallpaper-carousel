# `p4a/hook.py` — what it does and why

`hook.py` isn't app logic. It's a **build-time script that edits generated files before Gradle
compiles them**. python-for-android (p4a) generates `SDLActivity.java` and `AndroidManifest.xml`
from templates. We change SDL's behaviour by patching those files on disk each build.

---

## The mechanics

Two p4a functions are entry points, called automatically during the build:

| function | when | what it patches |
| --- | --- | --- |
| `before_apk_build` | right before Gradle | `SDLActivity.java` |
| `after_apk_build` | also before compilation (despite the name) | `AndroidManifest.xml` |

Both call `_count_or_fail(hook.py:137)`, which is the important bit:

```python
if occurrences != expected:
    raise RuntimeError("Refusing to build: ...")
```

If a future SDL version changes the code we're looking for, the build **crashes loudly** instead
of silently skipping the fix and shipping a broken app. The alternative — patch best-effort — is
how you end up with a "successful" build and the original bug back.

---

## Patch 1 — `mSurface` null guard (the old crash)

`SDL_UNGUARDED_RESUME` → `SDL_GUARDED_RESUME` (`hook.py:85-86`). Adds `mSurface != null &&`.
Simple find-and-replace.

```java
// before
if (mSurface.mIsSurfaceReady && (mHasFocus || mHasMultiWindow) && mIsResumedCalled) {
// after
if (mSurface != null && mSurface.mIsSurfaceReady && (mHasFocus || mHasMultiWindow) && mIsResumedCalled) {
```

`mSurface` is created in `finishLoad()`, which p4a runs from `UnpackFilesTask.onPostExecute()`
(an AsyncTask), so `onStart()` can reach the RESUMED branch before the surface exists.

---

## Patch 2 — allow re-creation (`hook.py:168`)

SDL asked native code whether it may re-create the activity, and the answer was no:

```java
boolean allow_recreate = SDLActivity.nativeAllowRecreateActivity();   // → false
...
} else {
    Log.v(TAG, "activity finished");
    System.exit(0);      // ← your app disappearing, no crash
}
```

We rewrite that line to `boolean allow_recreate = true;`, so the `else` branch is dead. There are
exactly **2** such sites, hence `expected=2` — if SDL ships a third, the build tells us to update
the constant.

---

## Patch 3 — don't kill Python on the way out (`hook.py:188`)

This is the subtle one, and it's why patch 2 alone would have been *worse*.

Re-creating an activity means the **old** one is destroyed first. Its `onDestroy()` does:

```
nativeSendQuit()   →   mSDLThread.join(1000)   →   nativeQuit()
```

`nativeQuit()` kills the SDL thread, which kills the running Python VM. Meanwhile the **new**
activity starts up and — because p4a moved SDL's setup out of `onCreate` into an AsyncTask —
begins launching a *second* `SDLMain` thread, which calls `Py_InitializeFromConfig` in a process
that already has CPython initialised. Garbage.

So the fix wraps the teardown in a check. Android tells you *why* an activity is being destroyed:

```java
if (!isChangingConfigurations()) {   // only a real finish tears down
    ... nativeSendQuit() / join / nativeQuit() ...
}
```

`isChangingConfigurations()` is true for config-change destroys (our wallpaper case) and false
when the user actually leaves (back button, app closed). That's why the comment on
`hook.py:106-108` stresses using this rather than `!isFinishing()` — a real exit must still tear
down, otherwise we leak the thread.

---

## Patch 4 — prevent it entirely (`hook.py:235`)

Layers 2 and 3 make re-creation survivable. But not re-creating at all is better.
`android:configChanges` lists config changes the activity handles itself instead of being
destroyed for. The hook adds `assetsPaths` to it, so MIUI's overlay calls
`onConfigurationChanged()` and nothing happens.

Cheapest layer first: **prevent → survive → keep alive**. If patch 4 works, patches 2 and 3 never
fire.

---

## Two things worth calling out

**The nesting looks wrong but isn't.** `SDL_ONDESTROY_KEPT_ALIVE` produces:

```java
if (!isChangingConfigurations()) {
if (SDLActivity.mSDLThread != null) {
```

The second `if` isn't indented to match. Ugly, but this is string substitution into a generated
file — re-indenting would mean reconstructing the whole method body as one giant string, and a
re-indent that fails is a silent no-op. Braces balance, which is what matters.

**Everything is idempotent.** Each patch checks for its own marker first
(`if SDL_GUARDED_RESUME in source: return`). Without that, a second build in the same directory
would double-patch and break the Java.

---

## Don't use a `replace_src` hook

**This p4a version has no `replace_src` hook.** `toolchain.py` only calls `before_apk_build`,
`after_apk_build`, `before_apk_assemble`, `after_apk_assemble`. A `replace_src` hook would be
silently dead code.

Patching the **dist** copy (not the bootstrap recipe source) is deliberate:

- `before_apk_build` runs with cwd = `dist_dir`, immediately before gradle, so it is the last
  word before compilation and wins even if p4a re-copies SDL sources.
- No need to delete the 1.3G `build/bootstrap_builds/sdl3` to force a recipe re-prepare.

---

## Verification

Do not trust the source check alone. Confirm in the bytecode.

```bash
cd /tmp && unzip -qo ~/Documents/python-android/bin/waller-*-debug.apk classes5.dex
~/.buildozer/android/platform/android-sdk/build-tools/37.0.0/dexdump -d classes5.dex > d5.txt
```

Two gotchas:

- `strings classes.dex` does **not** work — dex keeps no Java source text.
- The app's `SDLActivity` is in `classes5.dex` of 7, not `classes.dex`.

Patch 3 in `onDestroy` must show the jump that skips the teardown:

```
001e: invoke-virtual {v4}, Landroid/app/Activity;.isChangingConfigurations:()Z
0022: if-nez v0, 004d          <- jumps straight to invoke-super onDestroy
0028: invoke-static {}, Lorg/libsdl/app/SDLActivity;.nativeSendQuit:()V
002f: invoke-virtual {v0, v2, v3}, Ljava/lang/Thread;.join:(J)V
004a: invoke-static {}, Lorg/libsdl/app/SDLActivity;.nativeQuit:()V
004d: invoke-super {v4}, Landroid/app/Activity;.onDestroy:()V
```

Patch 4, from the built APK:

```bash
aapt2 dump xmltree bin/waller-*-debug.apk --file AndroidManifest.xml
# A: android:configChanges(0x0101001f)=0xc0003fff     # bit 0x80000000 (assetsPaths) SET
```

Note the two `System;.exit:(I)V` calls remain in `finishLoad` bytecode — they are now on
constant-`true`-dead paths, which is why checking for their *absence* is the wrong test.

---

## Testing

**There is no pytest coverage for any of this and there cannot be.** It is Java-side and needs a
device.

Hook patches can still be checked against the real generated sources in a temp dir — idempotence,
fail-fast on all of them, brace balance. On-device:

```bash
adb shell am force-stop org.wally.waller   # clear the bad-process state first, or the next
                                           # launch fails for that unrelated reason
adb logcat -c
adb install -r bin/waller-*-debug.apk
```

Then reproduce the original trigger — `test_wallpaper()` in
`app_src/ui/screens/settings_screen.py` is a good repeat button for it — and confirm no
`FATAL EXCEPTION: SDLActivity` and no `activity finished` in logcat.

pytest is unchanged at **332 passed / 11 failed** — the 11 are pre-existing and unrelated
(3 toggle-row, 3 intent-extra, 4 log-truncation, 1 permission).

---

## Note on the hook's existing lint warnings

`hook.py` has 3 pre-existing ruff F-errors (unused `os`, unused
`inject_foreground_service_types`, unused `services`). Verified identical at `HEAD`; left alone
rather than mixing cleanup into a crash fix.