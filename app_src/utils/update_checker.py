import traceback

from android_notify.config import on_android_platform

from utils.logger import app_logger


def schedule_update_check():
    """Schedule periodic background update check via WorkManager."""
    if not on_android_platform():
        return
    try:
        from android_notify.internal.java_classes import autoclass

        PythonActivity = autoclass("org.kivy.android.PythonActivity")
        context = PythonActivity.mActivity.getApplicationContext()

        WorkScheduler = autoclass("org.wally.waller.WorkScheduler")
        WorkScheduler.scheduleUpdateCheck(context)
        app_logger.info("Update check WorkManager task scheduled (7 day interval, network required)")
    except Exception:
        traceback.print_exc()
        app_logger.exception("Failed to schedule update check WorkManager task")


def handle_update_intent(app, intent=None):
    """Read activity intent extras and handle update-related navigation."""
    if not on_android_platform():
        return

    try:
        from android_notify.internal.java_classes import autoclass

        if intent is None:
            PythonActivity = autoclass("org.kivy.android.PythonActivity")
            activity = PythonActivity.mActivity
            intent = activity.getIntent()

        if intent is None:
            return

        extras = intent.getExtras()
        if extras is None:
            return

        action = extras.getString("action")
        if action not in ("open_update", "download_update", "install_update"):
            return

        version = extras.getString("version", "")
        release_notes = extras.getString("release_notes", "")
        apk_size = _apk_size_from_extras(extras)
        app_logger.info(
            f"handle_update_intent: action={action} version={version} apk_size={apk_size}"
        )
        intent.replaceExtras(None)
        _navigate_to_update_screen(
            app,
            version,
            release_notes,
            apk_size,
            next_step={"download_update": "download", "install_update": "install"}.get(action),
        )

    except Exception:
        app_logger.exception("Failed to handle update intent")


def _apk_size_from_extras(extras):
    """The APK size may arrive as a long (from Java) or an int (from `am start --ei`)."""
    for getter in ("getLong", "getInt"):
        try:
            size = int(getattr(extras, getter)("apk_size", 0) or 0)
            if size > 0:
                return size
        except Exception:
            app_logger.exception(f"Could not read apk_size via {getter}")
    return 0


def _navigate_to_update_screen(app, version, release_notes="", apk_size=0, next_step=None):

    def _go(notes):
        if not hasattr(app, "sm") or app.sm is None:
            return
        try:
            screen = app.sm.download_apk_screen
            screen.show(
                new_version=version,
                release_notes=notes or f"Version {version} is available.",
                apk_size=apk_size,
            )
            if next_step == "download":
                Clock.schedule_once(lambda dt: screen.start_download(), 1)
            elif next_step == "install":
                Clock.schedule_once(lambda dt: screen.start_install(), 1)
        except Exception:
            app_logger.exception("Failed to navigate to update screen")

    from kivy.clock import Clock

    Clock.schedule_once(lambda dt: _go(release_notes), 0.5)
