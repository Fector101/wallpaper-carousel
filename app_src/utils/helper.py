import json
import os, platform
import sys, traceback, socket
from datetime import datetime

from jnius import autoclass, cast
from android_notify.config import get_python_activity_context, from_service_file, on_android_platform
from android_notify.internal.java_classes import BuildVersion, BitmapFactory

from ui.widgets.android import toast
from utils.constants import DEV


def is_wine():
    """
	Detect if the application is running under Wine.
	"""
    # Check environment variables set by Wine
    if "WINELOADER" in os.environ:
        return True

    # Check platform.system for specific hints
    if platform.system().lower() == "windows":
        # If running in "Windows" mode but in a Linux environment, it's likely Wine
        return "XDG_SESSION_TYPE" in os.environ or "HOME" in os.environ

    return False


def makeFolder(my_folder: str):
    """Safely creates a folder if it doesn't exist."""
    # Normalize path for Wine (Windows-on-Linux)
    if is_wine():
        my_folder = my_folder.replace('\\', '/')

    if not os.path.exists(my_folder):
        try:
            os.makedirs(my_folder)
        except Exception as e:
            print(f"Error creating folder '{my_folder}': {e}")
    return my_folder


def appFolder():
    """Creates (if needed) and returns the Laner download folder path."""

    if on_android_platform():
        from android.storage import app_storage_path # type: ignore # , primary_external_storage_path
        # folder_path = os.path.join(primary_external_storage_path(), 'Pictures', 'Waller')
        folder_path = app_storage_path()
    else:
        folder_path = os.getcwd()

    makeFolder(folder_path)
    return folder_path


class Tee:
    """Redirects writes to both the original stream and a file."""

    def __init__(self, file_path, mode='a'):
        self.file = open(file_path, mode, encoding='utf-8')
        self.stdout = sys.__stdout__  # keep original console output

    def write(self, message):
        # Write to console
        self.stdout.write(message)
        self.stdout.flush()

        # Write to file
        self.file.write(message)
        self.file.flush()

    def flush(self):
        self.stdout.flush()
        self.file.flush()


def write_logs_to_file(log_folder_name="logs", file_name="all_output1.txt"):
    # Create folder
    if not DEV:
        return
    try:

        log_folder = os.path.join(appFolder(), log_folder_name)
        makeFolder(log_folder)

        # Log file path
        log_file_path = os.path.join(log_folder, file_name)

        # Add a timestamp header for new session
        with open(log_file_path, 'a', encoding='utf-8') as f:
            f.write("\n" + "=" * 60 + "\n")
            f.write(f"New session started: {datetime.now()}\n")
            f.write("=" * 60 + "\n")

        # Redirect stdout and stderr
        tee = Tee(log_file_path)
        sys.stdout = tee
        sys.stderr = tee
    except Exception as error_saving_logs:
        print('Error directing logs:', error_saving_logs)


class Service:
    def __init__(self, name, args_str="", extra=True):
        try:
            from android import mActivity # type: ignore
        except (ModuleNotFoundError, ImportError):
            mActivity = None
        self.mActivity = mActivity
        self.args_str = args_str
        self.name = name
        self.service = autoclass(self.get_name()) if self.mActivity else None
        self.extra = extra

    def get_name(self):
        if not self.mActivity:
            return None
        context = self.mActivity.getApplicationContext()
        return str(context.getPackageName()) + '.Service' + self.name

    def is_running(self):
        if not self.mActivity:
            return None

        service_name = self.get_name()
        context = self.mActivity.getApplicationContext()
        thing = self.mActivity.getSystemService(context.ACTIVITY_SERVICE)

        manager = cast('android.app.ActivityManager', thing)
        for service in manager.getRunningServices(100):
            found_service = service.service.getClassName()
            print("found_service: ", found_service)
            if found_service == service_name:
                return True
        return False

    def stop(self):
        if not self.mActivity:
            return None

        try:
            if not self.is_running():
                print("Service not running")
                return None

            self.service.stop(self.mActivity)
            return True

        except Exception as error_stopping_service:
            print("Error stopping service:",error_stopping_service)
            traceback.print_exc()
            return False

    def start(self):
        if not on_android_platform():
            self.__run_service_file()
            print('hello')
            return None
        if not self.mActivity:
            return None

        state = self.is_running()
        print(f"service name: {self.get_name()}, state: {state}, passed in name: {self.name}")

        arg = json.dumps(self.args_str)
        try:
            self.service.start(self.mActivity, arg)
        except Exception as error_starting_service:
            print("Error starting service:",error_starting_service)
            traceback.print_exc()

    def __run_service_file(self):
        import runpy, threading

        def start_service():
            os.environ.setdefault("PYTHON_SERVICE_ARGUMENT", json.dumps(self.args_str))
            runpy.run_path(
                "app_src/android/services/wallpaper.py",
                run_name="__main__"
            )

        threading.Thread(
            target=start_service,
            daemon=True  # important
        ).start()


def format_time_remaining(seconds):
    """Format seconds into minutes:seconds for countdown"""
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{minutes:02d}:{secs:02d}"


def smart_convert_minutes(minutes: float) -> str:
    total_seconds = int(minutes * 60)

    hours = total_seconds // 3600
    remaining_seconds = total_seconds % 3600
    mins = remaining_seconds // 60
    secs = remaining_seconds % 60

    result_parts = []

    if hours > 0:
        result_parts.append(f"{hours}hr" if hours == 1 else f"{hours}hrs")

    if mins > 0:
        result_parts.append(f"{mins}min" if mins == 1 else f"{mins}mins")

    if secs > 0:
        result_parts.append(f"{secs}sec" if secs == 1 else f"{secs}secs")

    return " ".join(result_parts) if result_parts else "0secs"


def get_free_port():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.bind(("", 0))  # bind to a random free port
    port = s.getsockname()[1]
    s.close()
    return port


def test_java_action():
    from jnius import autoclass, cast
    # from android import python_act

    # Get current activity and context
    # mActivity = autoclass("org.kivy.android.PythonActivity").mActivity
    context = get_python_activity_context()#mActivity.getApplicationContext()

    # Autoclass necessary Java classes
    RingtoneManager = autoclass("android.media.RingtoneManager")
    Uri = autoclass("android.net.Uri")
    AudioAttributesBuilder = autoclass("android.media.AudioAttributes$Builder")
    AudioAttributes = autoclass("android.media.AudioAttributes")
    AndroidString = autoclass("java.lang.String")
    NotificationManager = autoclass("android.app.NotificationManager")
    NotificationChannel = autoclass("android.app.NotificationChannel")
    NotificationCompat = autoclass("androidx.core.app.NotificationCompat")
    NotificationCompatBuilder = autoclass("androidx.core.app.NotificationCompat$Builder")
    NotificationManagerCompat = autoclass("androidx.core.app.NotificationManagerCompat")
    NotificationCompatActionBuilder = autoclass("androidx.core.app.NotificationCompat$Action$Builder")

    func_from = getattr(NotificationManagerCompat, "from")
    Intent = autoclass("android.content.Intent")
    PendingIntent = autoclass("android.app.PendingIntent")

    # Autoclass your own Java class
    action1 = autoclass("org.wally.waller.Action1")

    # Variables
    channel_id = "channel_id"
    notification_id = 101
    _id = 1  # action id

    # === CREATE CHANNEL ===
    sound = cast(Uri, RingtoneManager.getDefaultUri(RingtoneManager.TYPE_NOTIFICATION))
    att = AudioAttributesBuilder()
    att.setUsage(AudioAttributes.USAGE_NOTIFICATION)
    att.setContentType(AudioAttributes.CONTENT_TYPE_SONIFICATION)
    att = cast(AudioAttributes, att.build())

    name = cast("java.lang.CharSequence", AndroidString("Channel Name"))
    description = AndroidString("Channel Description")
    importance = NotificationManager.IMPORTANCE_HIGH

    channel = NotificationChannel(channel_id, name, importance)
    channel.setDescription(description)
    channel.enableLights(True)
    channel.enableVibration(True)
    channel.setSound(sound, att)

    notificationManager = context.getSystemService(NotificationManager)
    notificationManager.createNotificationChannel(channel)

    # === CREATE NOTIFICATION ===
    builder = NotificationCompatBuilder(context, channel_id)
    builder.setSmallIcon(context.getApplicationInfo().icon)
    builder.setContentTitle(cast("java.lang.CharSequence", AndroidString("Notification Title")))
    builder.setContentText(cast("java.lang.CharSequence", AndroidString("Notification Text")))
    builder.setSound(sound)
    builder.setPriority(NotificationCompat.PRIORITY_HIGH)
    builder.setVisibility(NotificationCompat.VISIBILITY_PUBLIC)

    # Intent for action button
    intent = Intent(context, action1)
    pending_intent = PendingIntent.getBroadcast(
        context, _id, intent, PendingIntent.FLAG_CANCEL_CURRENT | PendingIntent.FLAG_IMMUTABLE
    )
    title = cast("java.lang.CharSequence", AndroidString("Action 1"))

    action1_button = NotificationCompatActionBuilder(
        _id, title, pending_intent
    ).build()
    builder.addAction(action1_button)

    # Send the notification
    compat_manager = func_from(context)
    compat_manager.notify(notification_id, builder.build())


def change_wallpaper(wallpaper_path):
    """Actually set the wallpaper"""
    try:
        if not wallpaper_path:
            return False
        elif not os.path.exists(wallpaper_path):
            print("Invalid wallpaper path")
            return False

        WallpaperManager = autoclass('android.app.WallpaperManager') if on_android_platform() else None
        context = get_python_activity_context()
        wallpaper_manager = WallpaperManager.getInstance(context) if WallpaperManager else None

        if not wallpaper_manager:
            print("Failed to set wallpaper: wallpaper_manager = None")
            return None

        if BuildVersion.SDK_INT >= 24:  # Android 7.0+
            bitmap = BitmapFactory.decodeFile(wallpaper_path)
            FLAG_LOCK = WallpaperManager.FLAG_LOCK
            wallpaper_manager.setBitmap(bitmap, None, True, FLAG_LOCK)
            if not from_service_file():
                toast("Changed Wallpaper")
            # print(f"Success: Lock screen wallpaper changed to: {os.path.basename(wallpaper_path)}")
        else:
            toast("Changed Not Supported")
            print("Fail: Lock screen wallpaper not supported on this Android version.")

        return True
    except Exception as e:
        toast("Failed to Change")
        print("Failed to set wallpaper:", e)
        return False


class Font:
    def __init__(self, name, base_folder):
        self.base_folder = base_folder
        self.name = name

    def get_type_path(self, fn_type):
        """
        Formats font type path
        :param fn_type:
        :return:
        """
        return os.path.join(self.base_folder, self.name + '-' + fn_type + '.ttf')

