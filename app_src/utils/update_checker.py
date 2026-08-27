import traceback

from android_notify.config import on_android_platform

from utils.logger import app_logger

WORK_TAG = "update_check_work"


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
        app_logger.info("Update check WorkManager task scheduled (15min interval, network required)")
    except Exception:
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
        if action == "open_update":
            version = extras.getString("version", "")
            app_logger.info(f"handle_update_intent: navigating to update screen for version={version}")
            intent.replaceExtras(None)
            _navigate_to_update_screen(app, version)

    except Exception:
        app_logger.exception("Failed to handle update intent")


def _navigate_to_update_screen(app, version):
    def _go(_):
        if not hasattr(app, "sm") or app.sm is None:
            return
        try:
            screen = app.sm.download_apk_screen
            screen.show(
                new_version=version,
                release_notes=f"Version {version} is available.",
                apk_size=0,
            )
        except Exception:
            app_logger.exception("Failed to navigate to update screen")

    from kivy.clock import Clock

    Clock.schedule_once(_go, 0.5)
