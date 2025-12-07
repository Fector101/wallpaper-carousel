try:
    from utils.helper import start_logging, makeDownloadFolder
    start_logging()
    print("Service Logging started. All console output will also be saved.")
except Exception as e:
    print("File Logger Failed", e)

print("Entered Wallpaper Foreground Service...")
import os
import time
import random, traceback
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
def get_interval():
    try:
        from utils.config_manager import ConfigManager
        config = ConfigManager(makeDownloadFolder())
        t=float(config.get_interval()) * 60
        return t
    except Exception as e:
        print("Service Failed to get Interval:", e)
        traceback.print_exc()
        return 120


INTERVAL =   get_interval() #120

    
    
    
SERVICE_LIFESPAN_HOURS = 6  # Service will run for 6 hours
SERVICE_LIFESPAN_SECONDS = SERVICE_LIFESPAN_HOURS * 3600

def format_time_remaining(seconds):
    """Format seconds into minutes:seconds for countdown"""
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{minutes:02d}:{secs:02d}"

def get_service_lifespan_text(elapsed_seconds):
    """Get service lifespan text like 'service lifespan: 6hrs'"""
    remaining_hours = max(0, SERVICE_LIFESPAN_HOURS - int(elapsed_seconds // 3600))
    return f"service lifespan: {remaining_hours}hrs"

def main_loop():
    global notification
    service_start_time = time.time()
    wallpaper_change_time = service_start_time
    countdown_start = INTERVAL
    
    # Get initial wallpaper
    wallpaper_name, wallpaper_path = get_next_wallpaper()
    wallpaper_name = wallpaper_name or "No image"
    
    # Set initial notification
    notification.updateTitle(f"Next in {format_time_remaining(countdown_start)}")
    notification.updateMessage(get_service_lifespan_text(0))
    if wallpaper_path and os.path.exists(wallpaper_path):
        notification.setLargeIcon(wallpaper_path)
    
    while True:
        try:
            current_time = time.time()
            elapsed_since_service_start = current_time - service_start_time
            elapsed_since_wallpaper_change = current_time - wallpaper_change_time
            time_remaining = max(0, INTERVAL - elapsed_since_wallpaper_change)
            
            # Update countdown every second
            notification.updateTitle(f"Next in {format_time_remaining(time_remaining)}")
            
            # Update service lifespan every hour
            if int(elapsed_since_service_start) % 3600 == 0:  # Every hour
                notification.updateMessage(get_service_lifespan_text(elapsed_since_service_start))
            
            # Check if it's time to change wallpaper
            if elapsed_since_wallpaper_change >= INTERVAL:
                # Set the wallpaper that was previewed
                if wallpaper_path:
                    set_wallpaper(wallpaper_path)
                
                # Reset wallpaper change timer
                wallpaper_change_time = current_time
                
                # Get NEXT wallpaper for preview
                wallpaper_name, wallpaper_path = get_next_wallpaper()
                wallpaper_name = wallpaper_name or "No image"
                
                # Update large icon with upcoming wallpaper
                if wallpaper_path and os.path.exists(wallpaper_path):
                    notification.setLargeIcon(wallpaper_path)
            
            # Check if service lifespan has expired
            if elapsed_since_service_start >= SERVICE_LIFESPAN_SECONDS:
                print("Service lifespan expired. Stopping service.")
                notification.updateTitle("Service Completed")
                notification.updateMessage("6 hours service lifespan finished")
                time.sleep(5)
                # service.stopSelf()
                break
            
            # Update more frequently for smooth countdown
            time.sleep(1)  # Update every second
            
        except Exception as e:
            print("Fatal Error: Error in main loop, restarting in 5s:", e)
            time.sleep(5)

# --- Start foreground service ---
# Create and send initial notification for foreground service
notification = Notification(title="Next in 02:00", message="service lifespan: 6hrs")
builder = notification.start_building()
service.startForeground(notification.id, builder.build(), foreground_type)
service.setAutoRestartService(True)  # auto-restart if killed

# --- Run main loop ---
main_loop()
