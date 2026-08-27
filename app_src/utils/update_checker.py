import threading

from android_notify import Notification, NotificationHandler
from android_notify.config import on_android_platform

from utils.constants import VERSION
from utils.logger import app_logger

NOTIFICATION_CHANNEL_ID = "update_channel"
NOTIFICATION_CHANNEL_NAME = "App Updates"
NOTIFICATION_ID = 999

PREFS_NAME = "update_checker_prefs"
KEY_LAST_NOTIFIED = "last_notified_timestamp"


def check_and_notify():
    """Check GitHub for new version and send notification if available."""
    import requests

    try:
        api_url = "https://api.github.com/repos/Fector101/wallpaper-carousel/releases/latest"
        r = requests.get(api_url, timeout=10)
        r.raise_for_status()
        data = r.json()

        latest_version = data["tag_name"].lstrip("v")
        if latest_version == VERSION:
            return

        release_notes = _get_release_notes(data, latest_version)
        _send_update_notification(latest_version, release_notes)
        _save_last_notified_timestamp()
        app_logger.info(f"Update notification sent for v{latest_version}")

    except Exception as e:
        app_logger.exception(f"Update check failed: {e}")


def _get_release_notes(data, version):
    import requests as _requests

    file_name = f"update-note-v{version}.txt"
    for asset in data.get("assets", []):
        if asset["name"] == file_name:
            try:
                r = _requests.get(asset["browser_download_url"], timeout=10)
                r.raise_for_status()
                return r.text
            except Exception:
                app_logger.exception("Failed to fetch release notes")
            break

    return f"Version {version} is available."


def _send_update_notification(version, release_notes):
    if not NotificationHandler.has_permission():
        app_logger.warning("No notification permission, skipping update notification")
        return

    Notification.createChannel(
        id=NOTIFICATION_CHANNEL_ID,
        name=NOTIFICATION_CHANNEL_NAME,
        importance="high",
    )

    short_notes = release_notes.split("\n")[0] if release_notes else ""
    message = f"v{version} is ready. Tap to update."
    if short_notes and short_notes != release_notes:
        message = f"{short_notes}\nTap to update."

    notification = Notification(
        title="New version available",
        message=message,
        name="open_update",
        channel_id=NOTIFICATION_CHANNEL_ID,
        channel_name=NOTIFICATION_CHANNEL_NAME,
        id=NOTIFICATION_ID,
    )
    notification.setData({"action": "open_update", "version": version})
    notification.send(silent=True)


def _save_last_notified_timestamp():
    if not on_android_platform():
        return
    try:
        from android_notify.internal.java_classes import autoclass

        PythonActivity = autoclass("org.kivy.android.PythonActivity")
        context = PythonActivity.mActivity.getApplicationContext()
        prefs = context.getSharedPreferences(PREFS_NAME, 0)
        editor = prefs.edit()
        editor.putLong(KEY_LAST_NOTIFIED, _java_system_current_time_millis())
        editor.apply()
    except Exception:
        app_logger.exception("Failed to save last notified timestamp")


def _java_system_current_time_millis():
    from android_notify.internal.java_classes import autoclass

    System = autoclass("java.lang.System")
    return System.currentTimeMillis()


def handle_update_intent(app):
    """Read activity intent extras and handle update-related navigation."""
    if not on_android_platform():
        return

    try:
        from android_notify.internal.java_classes import autoclass

        PythonActivity = autoclass("org.kivy.android.PythonActivity")
        activity = PythonActivity.mActivity
        intent = activity.getIntent()
        if intent is None:
            return

        extras = intent.getExtras()
        if extras is None:
            return

        if extras.getBoolean("check_for_update", False):
            intent.replaceExtras(None)
            threading.Thread(target=check_and_notify, daemon=True).start()

        action = extras.getString("action")
        if action == "open_update":
            version = extras.getString("version", "")
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
