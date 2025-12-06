try:
    from utils.helper import start_logging, makeDownloadFolder
    start_logging()
    print("Service Logging started. All console output will also be saved.")
except Exception as e:
    print("File Logger Failed", e)

print("Entered Wallpaper Foreground Service...")
import os
import time
import random
from android_notify import Notification
from android_notify.config import get_python_service, get_python_activity_context
from jnius import autoclass

# --- Android classes ---
BuildVersion = autoclass("android.os.Build$VERSION")
ServiceInfo = autoclass("android.content.pm.ServiceInfo")
PythonService = autoclass('org.kivy.android.PythonService')
WallpaperManager = autoclass('android.app.WallpaperManager')
BitmapFactory = autoclass('android.graphics.BitmapFactory')
PythonActivity = autoclass('org.kivy.android.PythonActivity')

# --- Service and Wallpaper setup ---
service = get_python_service()
foreground_type = ServiceInfo.FOREGROUND_SERVICE_TYPE_DATA_SYNC if BuildVersion.SDK_INT >= 30 else 0
context = get_python_activity_context()
wm = WallpaperManager.getInstance(context)

# --- Folder setup ---
download_folder_path = os.path.join(makeDownloadFolder(), ".wallpapers")

# --- Get next wallpaper function ---
def get_next_wallpaper():
    """Get the next wallpaper path and name without setting it yet"""
    try:
        images = [
            os.path.join(download_folder_path, f)
            for f in os.listdir(download_folder_path)
            if f.lower().endswith((".jpg", ".jpeg", ".png"))
        ]
        if not images:
            print(f"Warning: No images found in {download_folder_path}")
            return None, None

        wallpaper_path = random.choice(images)
        return os.path.basename(wallpaper_path), wallpaper_path
    except Exception as e:
        print("Failed to get next wallpaper:", e)
        return None, None

# --- Set wallpaper function ---
def set_wallpaper(wallpaper_path):
    """Actually set the wallpaper"""
    try:
        if not wallpaper_path or not os.path.exists(wallpaper_path):
            print("Invalid wallpaper path")
            return False
            
        bitmap = BitmapFactory.decodeFile(wallpaper_path)
        
        if BuildVersion.SDK_INT >= 24:  # Android 7.0+
            FLAG_LOCK = WallpaperManager.FLAG_LOCK
            wm.setBitmap(bitmap, None, True, FLAG_LOCK)
            print(f"Success: Lock screen wallpaper changed to: {os.path.basename(wallpaper_path)}")
        else:
            print("Fail: Lock screen wallpaper not supported on this Android version.")
            
        return True
    except Exception as e:
        print("Failed to set wallpaper:", e)
        return False

# --- Main service loop with auto-restart ---
INTERVAL = 120  # 2 minutes

def main_loop():
    global notification
    start = time.time()
    
    # Get initial wallpaper
    wallpaper_name, wallpaper_path = get_next_wallpaper()
    wallpaper_name = wallpaper_name or "No image"
    
    # Send initial notification
    notification.updateTitle(f"Running for 0h 0m 0s")
    notification.updateMessage(f"Next: {wallpaper_name}")
    if wallpaper_path and os.path.exists(wallpaper_path):
        notification.setLargeIcon(wallpaper_path)
    notification.send()
    
    last_update = start
    
    while True:
        try:
            current_time = time.time()
            elapsed = current_time - start
            
            # Update elapsed time every minute even while waiting
            if current_time - last_update >= 60:  # Update every minute
                notification.updateTitle(f"Running for {int(elapsed//3600)}h {int((elapsed%3600)//60)}m {int(elapsed%60)}s")
                last_update = current_time
            
            # Check if it's time to change wallpaper
            if current_time - start >= INTERVAL:
                # Set the wallpaper that was previewed
                if wallpaper_path:
                    set_wallpaper(wallpaper_path)
                
                # Get NEXT wallpaper for preview
                wallpaper_name, wallpaper_path = get_next_wallpaper()
                wallpaper_name = wallpaper_name or "No image"
                
                # Update notification with new preview
                notification.updateMessage(f"Next: {wallpaper_name}")
                if wallpaper_path and os.path.exists(wallpaper_path):
                    notification.setLargeIcon(wallpaper_path)
                
                # Reset interval counter
                start = time.time()
                last_update = start
            
            # Short sleep to keep loop responsive
            time.sleep(10)  # Check every 10 seconds
            
        except Exception as e:
            print("Fatal Error: Error in main loop, restarting in 5s:", e)
            time.sleep(5)


# --- Start foreground service ---
# Create and send initial notification for foreground service
notification = Notification(title="Wallpaper Service Starting", message="Initializing...")
builder = notification.start_building()
service.startForeground(notification.id, builder.build(), foreground_type)
service.setAutoRestartService(True)  # auto-restart if killed

# --- Run main loop ---
main_loop()
