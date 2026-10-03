import os
import re
from pathlib import Path
from pythonforandroid.toolchain import ToolchainCL # type: ignore
from android_widgets.maker import Receiver, inject_foreground_service_types

spec_file_path = "/home/fabian/Documents/Laner/mobile/buildozer.spec"
package = "org.wally.waller"# if not os.path.exists(spec_file_path) else None
# package = "vercel.app.androidNotify"


def insert_to_end_of_xml(new_content,xml_file_content) -> str:
    return xml_file_content.replace("</application>", f"{new_content}\n</application>")

def generate_receivers(package_: str = None) -> str:
    receivers = [
        Receiver(
            name="DetectReceiver",
            actions=["android.intent.action.SCREEN_ON", "android.intent.action.SCREEN_OFF","android.intent.action.USER_PRESENT"]
        ),
        Receiver(
            name="CarouselReceiver",
            actions=["ACTION_STOP", "ACTION_SKIP"]
        ),
        Receiver(
            name="CarouselWidgetProvider",
            label="Carousel Widget",
            actions=[
                "android.intent.action.BOOT_COMPLETED",
                "android.appwidget.action.APPWIDGET_UPDATE",
            ],
            meta_resource="@xml/carousel_widget_info",
        ),
        Receiver(
            name="ImageWidgetProvider",
            label="Image Widget",
            actions=["android.appwidget.action.APPWIDGET_UPDATE"],
            meta_resource="@xml/image_widget_info",
        ),
        Receiver(
            name="SimpleWidget",
            label="Simple Text",
            actions=["android.appwidget.action.APPWIDGET_UPDATE"],
            meta_resource="@xml/widgetproviderinfo",
        ),
        Receiver(
            name="ButtonWidget",
            label="Counter Button Demo",
            actions=["android.appwidget.action.APPWIDGET_UPDATE"],
            meta_resource="@xml/button_widget_provider",
        ),

        # Receiver(
        #     name="TheReceiver",
        #     actions=["ALARM_ACTION"]
        # ),
        #
        Receiver(
            name="BootReceiver",
            actions=["android.intent.action.BOOT_COMPLETED"]
        ),
        Receiver(
            name="ConnectivityReceiver",
            actions=[
                "android.net.conn.CONNECTIVITY_CHANGE",
                "android.net.wifi.WIFI_STATE_CHANGED",
            ],
        ),

    ]

    return "\n\n".join(r.to_xml(package = package_,spec_file_path=spec_file_path) for r in receivers)


# SDLActivity.handleNativeState() dereferences mSurface in the RESUMED branch without a null
# check, while the PAUSED branch right above it does check. mSurface is created in
# finishLoad(), which p4a runs from UnpackFilesTask.onPostExecute(), so onStart() ->
# resumeNativeThread() -> handleNativeState() can reach that branch before the surface exists.
# That crashes the app on every activity re-creation (what a wallpaper change triggers on
# MIUI), with no Python frame anywhere in the stack. Same fix upstream SDL landed in
# "SDL: Android: decouple JNI setup from unused subsystems" (2026-07-02), minus their
# surface-less-thread variant, which only makes sense alongside their getInitSubsystems()
# redesign. Here the surface is always created, just later; skipping the transition is safe
# because SDLSurface.handleResume() retries via handleNativeState() once the surface is ready.
SDL_UNGUARDED_RESUME = "if (mSurface.mIsSurfaceReady && (mHasFocus || mHasMultiWindow) && mIsResumedCalled) {"
SDL_GUARDED_RESUME = "if (mSurface != null && mSurface.mIsSurfaceReady && (mHasFocus || mHasMultiWindow) && mIsResumedCalled) {"


# --- Activity re-creation on a wallpaper change -----------------------------------------
# Applying a wallpaper makes MIUI install a runtime theme/resource overlay. That reaches us as a
# config change carrying bit 0x80000000, dispatched through performDisplayOverrideConfigUpdate,
# which destroys and re-creates the activity.
#
# Setting the very same image again does NOT crash, which is what identifies the trigger: no
# overlay means no config change means no re-creation. It also means the damage accumulates --
# the first real change survives, later ones hit already-torn-down state.
#
# Three layers, cheapest first:
#   1. prevent  -- declare the bit in android:configChanges so the platform calls
#                  onConfigurationChanged() instead of re-creating. Handled in after_apk_build.
#                  This is the layer that actually stops the flicker; 2 and 3 are safety nets
#                  for ROMs that re-create anyway.
#   2. survive  -- let SDL re-create instead of calling System.exit(0).
#   3. keep alive -- skip the native teardown on a config-change destroy, so the Python/SDL side
#                  is not restarted underneath us. This is what stops the accumulation.
#
# Layer 1 is verified working, despite CONFIG_ASSETS_PATHS being marked @hide and unnamed in
# API 35's *public* ActivityInfo (its highest named flag there is CONFIG_FONT_SCALE =
# 0x40000000). It works because aapt2 resolves the flag NAME to a bitmask at build time: the
# compiled AndroidManifest.xml stores android:configChanges as the integer 0xc0003fff, with no
# "assetsPaths" string in it at all. The platform therefore compares bits it never has to name.
# Confirmed with `strings AndroidManifest.xml` on the built APK.
#
# The decision itself is plain bitmask arithmetic in ActivityRecord.shouldRelaunchLocked():
#     return (changes & (~configChanged)) != 0;
# where configChanged is the activity's declared configChanges. Declare the bit and that
# expression is 0, so there is no relaunch. The only special case is CONFIG_RESOURCES_UNUSED,
# which suppresses relaunch rather than forcing one; nothing forces a relaunch for
# CONFIG_ASSETS_PATHS.
#
# Widely-cited 2021 sources (a Stack Overflow pair and a Commonsware post) claim this config
# change is unblockable and apps cannot opt out. That was true of Android 12 and has since been
# reversed upstream: AOSP commit 9fd99967 deleted the "@hide We do not want apps handling this
# yet" line from the constant and replaced it with @FlaggedApi(FLAG_HANDLE_ALL_CONFIG_CHANGES),
# and the constant's Javadoc now reads "can itself handle asset path changes". Do not trust the
# older write-ups over the current source.
#
# Two supporting details for layer 1:
#   - Configuration.diff(delta, compareUndefined, publicOnly) sets CONFIG_ASSETS_PATHS when
#     assetsSeq differs even when publicOnly is true, so the diff is non-zero and reaches
#     shouldRelaunchLocked() at all.
#   - ActivityInfo.getRealConfigChanged() only ORs in CONFIG_SCREEN_SIZE|CONFIG_SMALLEST_SCREEN_SIZE
#     when targetSdkVersion < 13. We are minSdk 24, so it never interferes.
#
# Layer 3 relies on isChangingConfigurations() rather than !isFinishing(): only a config-change
# destroy should preserve native state. A real finish (back button, task removal) must still tear
# the SDL thread down, otherwise we leak it and the process lingers.

SDL_RECREATE_DECISION = "boolean allow_recreate = SDLActivity.nativeAllowRecreateActivity();"
SDL_RECREATE_ALLOWED = "boolean allow_recreate = true; // wallpaper overlay re-creation, see p4a hook"

SDL_ONDESTROY_TEARDOWN = """        if (SDLActivity.mSDLThread != null) {

            // Send Quit event to "SDLThread" thread
            SDLActivity.nativeSendQuit();"""
SDL_ONDESTROY_KEPT_ALIVE = """        // Config-change destroy (MIUI runtime overlay after a wallpaper change). Tearing the
        // SDL thread down here would kill the running Python VM and native SDL state, and the
        // re-created activity would then start a *second* SDLMain thread and re-enter
        // start.c -> Py_InitializeFromConfig in an already-initialised process. Keep native
        // state alive so the re-created activity attaches to it via nativeResume().
        if (!isChangingConfigurations()) {
        if (SDLActivity.mSDLThread != null) {

            // Send Quit event to "SDLThread" thread
            SDLActivity.nativeSendQuit();"""

SDL_ONDESTROY_QUIT = """        SDLActivity.nativeQuit();

        super.onDestroy();"""
SDL_ONDESTROY_QUIT_KEPT_ALIVE = """        SDLActivity.nativeQuit();
        } // end !isChangingConfigurations()

        super.onDestroy();"""


def _count_or_fail(source, needle, expected, java_file, explanation):
    occurrences = source.count(needle)
    if occurrences != expected:
        raise RuntimeError(
            f"Expected {expected} occurrence(s) of {needle!r} in {java_file}, found "
            f"{occurrences}. Refusing to build: {explanation} Update the SDL_* constants in this "
            "hook to match the new SDL source."
        )


def patch_sdlactivity_m_surface_null_guard(java_file):
    """Guard the mSurface dereference in SDLActivity.handleNativeState(). Idempotent, and
    raises when the expected line is not found exactly once, so a silent no-op can never ship
    the crash again while looking like a clean build."""
    java_file = Path(java_file)
    source = java_file.read_text(encoding="utf-8")

    if SDL_GUARDED_RESUME in source:
        print(f"SDL mSurface null guard already present in {java_file}")
        return

    _count_or_fail(
        source, SDL_UNGUARDED_RESUME, 1, java_file,
        "without this patch the app crashes with a NullPointerException in "
        "SDLActivity.handleNativeState().",
    )

    java_file.write_text(source.replace(SDL_UNGUARDED_RESUME, SDL_GUARDED_RESUME), encoding="utf-8")
    print(f"Patched mSurface null guard in {java_file}")


def patch_sdlactivity_allow_recreate(java_file):
    """Let SDL re-create the activity instead of System.exit(0). Without this, the re-creation
    block in finishLoad() kills the app on every wallpaper change that MIUI reports."""
    java_file = Path(java_file)
    source = java_file.read_text(encoding="utf-8")

    if SDL_RECREATE_ALLOWED in source:
        print(f"SDL re-creation allowance already present in {java_file}")
        return

    _count_or_fail(
        source, SDL_RECREATE_DECISION, 2, java_file,
        "without this patch SDLActivity.finishLoad() calls System.exit(0) on the re-creation "
        "that a wallpaper change triggers, so the app closes every time a wallpaper is applied.",
    )

    java_file.write_text(source.replace(SDL_RECREATE_DECISION, SDL_RECREATE_ALLOWED), encoding="utf-8")
    print(f"Patched SDL re-creation allowance in {java_file}")


def patch_sdlactivity_keep_native_alive_on_config_change(java_file):
    """Do not tear down the SDL thread / native state on a config-change destroy. Idempotent,
    and raises when the onDestroy teardown is not found exactly as expected."""
    java_file = Path(java_file)
    source = java_file.read_text(encoding="utf-8")

    # Marker must be the replacement blocks themselves, not just the isChangingConfigurations()
    # call: upstream SDL never calls that method today, so a bare substring check would start
    # matching the day SDL uses it in any unrelated lifecycle method, silently skipping this
    # patch and letting the double-Py_InitializeFromConfig crash return with a green build.
    if SDL_ONDESTROY_KEPT_ALIVE in source and SDL_ONDESTROY_QUIT_KEPT_ALIVE in source:
        print(f"SDL keep-alive guard already present in {java_file}")
        return

    _count_or_fail(
        source, SDL_ONDESTROY_TEARDOWN, 1, java_file,
        "without this patch every config-change destroy kills the Python VM, and the next "
        "activity start re-enters Py_InitializeFromConfig in an already-initialised process.",
    )
    _count_or_fail(
        source, SDL_ONDESTROY_QUIT, 1, java_file,
        "without this patch every config-change destroy kills the Python VM, and the next "
        "activity start re-enters Py_InitializeFromConfig in an already-initialised process.",
    )

    patched = source.replace(SDL_ONDESTROY_TEARDOWN, SDL_ONDESTROY_KEPT_ALIVE)
    patched = patched.replace(SDL_ONDESTROY_QUIT, SDL_ONDESTROY_QUIT_KEPT_ALIVE)

    java_file.write_text(patched, encoding="utf-8")
    print(f"Patched SDL onDestroy keep-alive guard in {java_file}")


def before_apk_build(toolchain: ToolchainCL):
    """Runs in the dist directory, immediately before gradle. Patching the dist copy (rather
    than the bootstrap recipe source) means this needs no bootstrap rebuild and is the last
    word before compilation, so it wins even if p4a re-copies the SDL sources.

    Note: this p4a has no replace_src hook -- toolchain.py only calls before_apk_build,
    after_apk_build, before_apk_assemble and after_apk_assemble."""
    sdl_activity = (
        Path(toolchain._dist.dist_dir)
        / "src" / "main" / "java" / "org" / "libsdl" / "app" / "SDLActivity.java"
    )
    patch_sdlactivity_m_surface_null_guard(sdl_activity)
    patch_sdlactivity_allow_recreate(sdl_activity)
    patch_sdlactivity_keep_native_alive_on_config_change(sdl_activity)


MANIFEST_CONFIG_CHANGES = re.compile(r'(android:configChanges=")([^"]*)(")')


def patch_manifest_config_changes(manifest_file):
    """Declare assetsPaths in android:configChanges (layer 1 of the wallpaper re-creation
    problem). MIUI's runtime theme overlay arrives as bit 0x80000000, which is
    ActivityInfo.CONFIG_ASSETS_PATHS as compiled against SDK 36 -- the api this app builds
    with. aapt2 resolves that flag name to a bit at build time, so the compiled manifest holds
    android:configChanges as an int (0xc0003fff) with no flag name in it, and
    ActivityRecord.shouldRelaunchLocked() decides with plain bitmask arithmetic
    (`changes & ~configChanged != 0`). Declaring the bit makes that expression 0, so the
    platform calls onConfigurationChanged() instead of destroying and re-creating the activity.

    Verified working. See the long note above for why the constant being @hide and unnamed in
    API 35's public ActivityInfo does not stop it, and why the 2021 "unblockable config change"
    write-ups are outdated.

    The remaining two layers in before_apk_build still apply, so this is belt-and-braces: if a
    ROM reports the change in a way configChanges cannot absorb, the app re-creates safely
    instead of exiting."""
    manifest_file = Path(manifest_file)
    content = manifest_file.read_text(encoding="utf-8")

    match = MANIFEST_CONFIG_CHANGES.search(content)
    if match is None:
        raise RuntimeError(
            f"Could not find android:configChanges in {manifest_file}. Refusing to build: "
            "without the assetsPaths flag MIUI's wallpaper overlay destroys and re-creates the "
            "activity. Update MANIFEST_CONFIG_CHANGES in this hook to match the new manifest."
        )

    flags = match.group(2)
    if "assetsPaths" in flags:
        print(f"android:configChanges already declares assetsPaths in {manifest_file}")
        return

    patched = content[:match.start()] + match.group(1) + flags + "|assetsPaths" + match.group(3) + content[match.end():]
    manifest_file.write_text(patched, encoding="utf-8")
    print(f"Added assetsPaths to android:configChanges in {manifest_file}")


def after_apk_build(toolchain: ToolchainCL):
    android_manifest_file_path = Path(toolchain._dist.dist_dir) / "src" / "main" / "AndroidManifest.xml"
    print(android_manifest_file_path)
    patch_manifest_config_changes(android_manifest_file_path)

    manifest_file_content = android_manifest_file_path.read_text(encoding="utf-8")


    # Add foregroundServiceType to multiple services
    services = {
        "Wallpapercarousel": "specialUse",
        # "Wallpapercarousel": "dataSync",

        }

    #manifest_file_content = inject_foreground_service_types(
        #manifest_text=manifest_file_content,
        #package=package,
        #spec_file_path=spec_file_path,
        #services=services,
    #)
    manifest_file_content = manifest_file_content.replace(
    'android:screenOrientation="unspecified"',
    'android:screenOrientation="fullSensor"'
    )

    receiver_xml = generate_receivers(package)
    manifest_file_content = insert_to_end_of_xml(receiver_xml, manifest_file_content)

    file_share_to_other_app_provider = f"""
<provider
    android:name="androidx.core.content.FileProvider"
    android:authorities="{package}.fileprovider"
    android:exported="false"
    android:grantUriPermissions="true">
    <meta-data
        android:name="android.support.FILE_PROVIDER_PATHS"
        android:resource="@xml/file_paths" />
</provider>
    """
    manifest_file_content = insert_to_end_of_xml(file_share_to_other_app_provider, manifest_file_content)

    image_share_from_other_apps_to_app_activity = """

<intent-filter>
    <action android:name="android.intent.action.SEND" />
    <category android:name="android.intent.category.DEFAULT" />
    <data android:mimeType="image/*" />
</intent-filter>

<intent-filter>
    <action android:name="android.intent.action.SEND_MULTIPLE" />
    <category android:name="android.intent.category.DEFAULT" />
    <data android:mimeType="image/*" />
</intent-filter>

</activity>
    """
    manifest_file_content = manifest_file_content.replace("</activity>", f"{image_share_from_other_apps_to_app_activity}")

    android_manifest_file_path.write_text(manifest_file_content, encoding="utf-8")
    print("Successfully: Updated Manifest!\n",manifest_file_content)

#     receiver_xml += f"""
#     <receiver
#     android:name="org.wally.waller.MyWorker"
#     android:exported="false" />""" + """
# <provider
#     android:name="androidx.startup.InitializationProvider"
#     android:authorities="${applicationId}.androidx-startup"
#     android:exported="false" />
# """
