import os, platform
import sys, traceback, socket
from datetime import datetime
from pathlib import Path

from jnius import autoclass, cast
from .config_manager import ConfigManager


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


def makeDownloadFolder():
    """Creates (if needed) and returns the Laner download folder path."""
    from kivy.utils import platform

    if platform == 'android':
        from android.storage import primary_external_storage_path  # type: ignore
        folder_path = os.path.join(primary_external_storage_path(), 'Download', 'Laner')
    else:
        folder_path = os.path.join(os.getcwd(), 'Download', 'Laner')

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


def start_logging(log_folder_name="logs", file_name="all_output1.txt"):
    # Create folder
    log_folder = os.path.join(makeDownloadFolder(), log_folder_name)
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


class Service:
    def __init__(self, name, args_str="", extra=True):
        try:
            from android import mActivity
        except (ModuleNotFoundError, ImportError):
            mActivity = None
        self.mActivity = mActivity
        self.args_str = args_str
        self.name = name
        self.service = autoclass(self.get_service_name()) if self.mActivity else None
        self.extra = extra

    def get_service_name(self):
        if not self.mActivity:
            return None
        context = self.mActivity.getApplicationContext()
        return str(context.getPackageName()) + '.Service' + self.name

    def service_is_running(self):
        if not self.mActivity:
            return None

        service_name = self.get_service_name()
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
            if self.service_is_running:
                self.service.stop(self.mActivity)
            return True
        except:
            traceback.print_exc()
            return False

    def start(self):
        if not self.mActivity:
            return None

        state = self.service_is_running()
        print(state, "||", self.name, "||", self.get_service_name())
        # if state:
        #     return

        title = self.name + ' Service'
        msg = 'Started'
        arg = str(self.args_str)
        icon = 'round_music_note_white_24'
        try:
            if self.extra:
                print('Calling Start Service...')
                self.service.start(self.mActivity, icon, title, msg, arg)
            else:
                self.service.start(self.mActivity, arg)
        except Exception as e:
            print("Error starting service:",e)
            traceback.print_exc()

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

import shutil

class FileOperation:
    def __init__(self,update_thumbnails_function):
        self.app_dir = Path(makeDownloadFolder())
        self.myconfig = ConfigManager(self.app_dir)
        self.wallpapers_dir = self.app_dir / ".wallpapers"
        self.update_thumbnails_function = update_thumbnails_function

    def copy_add(self, files):
        if not files:
            return
        new_images = []
        for src in files:
            if not os.path.exists(src):
                continue
            dest = self.unique(os.path.basename(src))
            try:
                shutil.copy2(src, dest)
            except:
                continue
            new_images.append(str(dest))
        for img in new_images:
            self.myconfig.add_wallpaper(img)
        self.update_thumbnails_function(new_images)

    def unique(self, dest_name):
        dest = self.wallpapers_dir / dest_name
        base, ext = os.path.splitext(dest_name)
        i = 1
        while dest.exists():
            dest = self.wallpapers_dir / f"{base}_{i}{ext}"
            i += 1
        return dest


def get_free_port():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.bind(("", 0))  # bind to a random free port
    port = s.getsockname()[1]
    s.close()
    return port


from android_notify.config import get_python_activity_context

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
    id = 1  # action id

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
    pendingintent = PendingIntent.getBroadcast(
        context, id, intent, PendingIntent.FLAG_CANCEL_CURRENT | PendingIntent.FLAG_IMMUTABLE
    )
    title = cast("java.lang.CharSequence", AndroidString("Action 1"))

    action1_button = NotificationCompatActionBuilder(
        id, title, pendingintent
    ).build()
    builder.addAction(action1_button)

    # Send the notification
    compatmanager = func_from(context)
    compatmanager.notify(notification_id, builder.build())

