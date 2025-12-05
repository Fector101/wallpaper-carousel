try:
    from .helper import start_logging,makeDownloadFolder
    start_logging()
    print("Service Logging started. All console output will also be saved.")
except Exception as e:
    print("File Logger Failed", e)

print("Entered Wallpaper Foreground Service...")
import os
import time
import random
from android_notify import Notification
from android_notify.config import get_python_activity
from jnius import autoclass

# --- Android classes ---
BuildVersion = autoclass("android.os.Build$VERSION")
ServiceInfo = autoclass("android.content.pm.ServiceInfo")
PythonService = autoclass('org.kivy.android.PythonService')
WallpaperManager = autoclass('android.app.WallpaperManager')
BitmapFactory = autoclass('android.graphics.BitmapFactory')
PythonActivity = autoclass('org.kivy.android.PythonActivity')

# --- Service and Wallpaper setup ---
service = PythonService.mService
foreground_type = ServiceInfo.FOREGROUND_SERVICE_TYPE_DATA_SYNC if BuildVersion.SDK_INT >= 30 else 0
wm = WallpaperManager.getInstance(PythonActivity.mActivity)

# --- Folder setup ---
download_folder_path = makeDownloadFolder()

# --- Notification setup ---
def create_notification(title: str, message: str):
    n = Notification(title=title, message=message)
    n.send()
    return n

n_runtime = Notification(title="Wallpaper Service Running")
n_runtime.send()

# --- Wallpaper function ---
def set_random_lock_wallpaper():
    try:
        images = [
            os.path.join(download_folder_path, f)
            for f in os.listdir(download_folder_path)
            if f.lower().endswith((".jpg", ".jpeg", ".png"))
        ]
        if not images:
            print(f"Warning: No images found in {download_folder_path}")
            return None

        wallpaper_path = random.choice(images)
        bitmap = BitmapFactory.decodeFile(wallpaper_path)

        if BuildVersion.SDK_INT >= 24:  # Android 7.0+
            FLAG_LOCK = WallpaperManager.FLAG_LOCK
            wm.setBitmap(bitmap, None, True, FLAG_LOCK)
            print(f"Success: Lock screen wallpaper changed to: {os.path.basename(wallpaper_path)}")
        else:
            print("Fail: Lock screen wallpaper not supported on this Android version.")

        return os.path.basename(wallpaper_path)
    except Exception as e:
        print("Failed to set wallpaper:", e)
        return None

# --- Main service loop with auto-restart ---
INTERVAL = 120  # 2 minutes

def main_loop():
    start = time.time()
    while True:
        try:
            elapsed = time.time() - start
            wallpaper_name = set_random_lock_wallpaper() or "No image"
            n_runtime.updateTitle(f"Running for {int(elapsed//3600)}h {int((elapsed%3600)//60)}m {int(elapsed%60)}s | Last: {wallpaper_name}")
            time.sleep(INTERVAL)
        except Exception as e:
            print("Fatal Error:  Error in main loop, restarting in 5s:", e)
            time.sleep(5)

# --- Start foreground service ---
builder = Notification(title="Foreground Service Active", message="Random lock screen wallpaper running").start_building()
service.startForeground(Notification().id, builder.build(), foreground_type)
service.setAutoRestartService(True)  # auto-restart if killed

# --- Run main loop ---
main_loop()
