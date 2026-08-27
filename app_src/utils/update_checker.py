from android_notify.config import on_android_platform

from utils.logger import app_logger

WORK_TAG = "update_check_work"


def schedule_update_check():
    """Schedule periodic background update check via WorkManager."""
    if not on_android_platform():
        return
    try:
        from android_notify.internal.java_classes import autoclass

        Context = autoclass("android.content.Context")
        PythonActivity = autoclass("org.kivy.android.PythonActivity")
        context = PythonActivity.mActivity.getApplicationContext()

        WorkManager = autoclass("androidx.work.WorkManager")
        PeriodicWorkRequest = autoclass("androidx.work.PeriodicWorkRequest")
        Constraints = autoclass("androidx.work.Constraints")
        NetworkType = autoclass("androidx.work.NetworkType")
        ExistingPeriodicWorkPolicy = autoclass("androidx.work.ExistingPeriodicWorkPolicy")
        TimeUnit = autoclass("java.util.concurrent.TimeUnit")
        UpdateCheckWorker = autoclass("org.wally.waller.UpdateCheckWorker")

        constraints = (Constraints.Builder()
            .setRequiredNetworkType(NetworkType.CONNECTED)
            .build())

        work_request = (PeriodicWorkRequest.Builder(
            UpdateCheckWorker, 15, TimeUnit.MINUTES)
            .setConstraints(constraints)
            .addTag(WORK_TAG)
            .build())

        work_manager = WorkManager.getInstance(context)
        work_manager.enqueueUniquePeriodicWork(
            WORK_TAG,
            ExistingPeriodicWorkPolicy.KEEP,
            work_request)

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
