try:
    from utils.helper import start_logging, makeDownloadFolder
    start_logging()
    # print("Service Logging started. All console output will also be saved.")
except Exception as e:
    print("File Logger Failed", e)

print("Entered Wallpaper Foreground Service...")
import os, threading
import time
import random, traceback
from os import environ
from jnius import autoclass
from pythonosc import dispatcher, osc_server, udp_client

from android_notify import Notification
from android_notify.config import get_python_service, get_python_activity_context
from android_notify.core import get_app_root_path
from android_widgets import Layout, RemoteViews, AppWidgetManager

# --- Android classes ---
BuildVersion = autoclass("android.os.Build$VERSION")
ServiceInfo = autoclass("android.content.pm.ServiceInfo")
PythonService = autoclass('org.kivy.android.PythonService')
WallpaperManager = autoclass('android.app.WallpaperManager')
BitmapFactory = autoclass('android.graphics.BitmapFactory')
PythonActivity = autoclass('org.kivy.android.PythonActivity')
AndroidString = autoclass("java.lang.String")

# --- Folder setup ---
download_folder_path = os.path.join(makeDownloadFolder(), "wallpapers")


def get_service_port():
    try:
        service_port = int(environ.get('PYTHON_SERVICE_ARGUMENT', '5006'))
    except (TypeError, ValueError):
        service_port = 5006
    try:
        current_wallpaper_store_path = os.path.join(get_app_root_path(), 'port.txt')
        with open(current_wallpaper_store_path, "w") as f:
            f.write(str(service_port))
    except Exception as error_write_port:
        print("Error writing wallpaper port:", error_write_port)
        traceback.print_exc()
    return service_port


# --- Get next wallpaper function ---
def get_next_wallpaper():
    """Get the next wallpaper path and name without setting it yet
    :return: [absolute_path, name]
    """
    try:
        images = [
            os.path.join(download_folder_path, f)
            for f in os.listdir(download_folder_path)
            if f.lower().endswith((".jpg", ".jpeg", ".png"))
        ]
        # print("service found:",images)
        if not images:
            print(f"Warning: No images found in {download_folder_path}")
            return '', ''

        wallpaper_path = random.choice(images)
        return os.path.basename(wallpaper_path), wallpaper_path
    except Exception as e:
        print("Failed to get next wallpaper:", e)
        return '', ''


# --- Set wallpaper function ---
def change_wallpaper(wallpaper_path):
    """Actually set the wallpaper"""
    try:
        if not wallpaper_path or not os.path.exists(wallpaper_path):
            print("Invalid wallpaper path")
            return False

        bitmap = BitmapFactory.decodeFile(wallpaper_path)

        if BuildVersion.SDK_INT >= 24:  # Android 7.0+
            FLAG_LOCK = WallpaperManager.FLAG_LOCK
            wm.setBitmap(bitmap, None, True, FLAG_LOCK)
            # print(f"Success: Lock screen wallpaper changed to: {os.path.basename(wallpaper_path)}")
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
        config = ConfigManager()
        t = int(float(config.get_interval()) * 60)
        return t
    except Exception as e:
        print("Service Failed to get Interval:", e)
        traceback.print_exc()
        return 120


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


# Start foreground service

service = get_python_service()
foreground_type = ServiceInfo.FOREGROUND_SERVICE_TYPE_DATA_SYNC if BuildVersion.SDK_INT >= 30 else 0
context = get_python_activity_context()
wm = WallpaperManager.getInstance(context)

notification = Notification(title="Next in 02:00", message="service lifespan: 6hrs")
notification.addButton(text="Stop", receiver_name="CarouselReceiver", action="ACTION_STOP")
notification.addButton(text="Skip", receiver_name="CarouselReceiver", action="ACTION_SKIP")
builder = notification.start_building()
service.startForeground(notification.id, builder.build(), foreground_type)
service.setAutoRestartService(True)  # auto-restart if killed


class MyWallpaperReceiver:
    def __init__(self):
        self.skip_now = False
        self.live = True
        self.next_wallpaper_path = ''
        self.current_sleep = 1
        self.current_wait_seconds = get_interval()
        self.service_start_time = time.time()
        self.__start_main_loop()
        self.changes = 0
    def __start_main_loop(self):
        threading.Thread(target=self.heart, daemon=True).start()

    def __count_down(self):
        self.current_wait_seconds = get_interval()
        while self.current_wait_seconds > 0:

            time.sleep(self.current_sleep)
            self.current_wait_seconds -= 1
            if self.current_wait_seconds <= 0:
                notification.updateTitle(f"Next in {format_time_remaining(get_interval())}")
                break
            notification.updateTitle(f"Next in {format_time_remaining(self.current_wait_seconds)}")

            current_time = time.time()
            elapsed_since_service_start = current_time - self.service_start_time
            if int(elapsed_since_service_start) % 3600 == 0:  # Every hour
                notification.updateMessage(get_service_lifespan_text(elapsed_since_service_start))

    def heart(self):
        # wait - so it waits before first change so user can cancel if they don't want feature
        # set

        while self.live:
            # Get Upcoming
            wallpaper = get_next_wallpaper()
            self.next_wallpaper_path = wallpaper[1]
            self.__set_next_img_in_notification(self.next_wallpaper_path)

            # Wait for a while
            # time.sleep(get_interval())
            self.__count_down()

            if not self.skip_now:
                # Then change wallpaper
                change_wallpaper(self.next_wallpaper_path)
                self.__write_wallpaper_path_to_file(self.next_wallpaper_path)
            self.skip_now = False

    def __write_wallpaper_path_to_file(self, wallpaper_path):
        # Writing for Java to see for home screen widget
        if not os.path.exists(wallpaper_path):
            self.__log(f"Image - {wallpaper_path} does not exist, can't store path", "ERROR")
            return

        current_wallpaper_store_path = os.path.join(get_app_root_path(), 'wallpaper.txt')
        with open(current_wallpaper_store_path, "w") as f:
            f.write(wallpaper_path)

        try:
            self.update_widget_image(wallpaper_path)
        except Exception as e:
            self.__log(f"Error update_widget_image  -{e} ping Java Listener", "WARNING")
            traceback.print_exc()

        #try:
          #  self.changed_widget_text()
        #except Exception as e:
         #   self.__log(f"Error changed_widget_text -{e} ping Java Listener", "WARNING")
         #   traceback.print_exc()
        #self.changes += 1

    def __set_next_img_in_notification(self, wallpaper_path):
        if os.path.exists(wallpaper_path):  # setting next in notification
            notification.setLargeIcon(wallpaper_path)
        else:
            self.__log(f"Image - {wallpaper_path} does not exist, can't set notification preview", "ERROR")

    @staticmethod
    def __log(msg, _type):
        print(f"\n{_type.upper()}: {msg}")

    def start(self, data=None):
        # self.__start_main_loop()
        pass

    def stop(self, *args):
        print("stop args:",args)
        self.current_wait_seconds = 0
        self.live = False
        # notification.cancel() android auto removes it
        service.setAutoRestartService(False) # On Android 12 service continued after swiping app from Recents this is best bet
        service.stopSelf()

    def pause(self, data=None):
        notification.updateTitle("Carousel Pause")
        self.current_sleep = 1000 ** 100
        pass

    def resume(self, data=None):
        self.current_sleep = 1

    def set_next_data(self, *args):
        print("next args:",args)
        self.skip_now = True
        self.current_wait_seconds = 0

    def set_wallpaper(self, wallpaper_path):
        change_wallpaper(wallpaper_path)



    def changed_widget_text(self):
        appWidgetManager = AppWidgetManager("CarouselWidgetProvider")

        text_layout = Layout("carousel_widget")
        views = RemoteViews(layout=text_layout)
        views.setTextViewText(text_id="widget_text", text=f"Count: {self.changes}")

        appWidgetManager.updateAppWidget(java_view_object=views.main)

    def update_widget_image(self, wallpaper_path):
        Bitmap = autoclass('android.graphics.Bitmap')
        BitmapConfig = autoclass('android.graphics.Bitmap$Config')
        Canvas = autoclass('android.graphics.Canvas')
        Paint = autoclass('android.graphics.Paint')
        Rect = autoclass('android.graphics.Rect')
        RectF = autoclass('android.graphics.RectF')
        PorterDuffMode = autoclass('android.graphics.PorterDuff$Mode')
        PorterDuffXfermode = autoclass('android.graphics.PorterDuffXfermode')

        BitmapFactory = autoclass('android.graphics.BitmapFactory')
        BitmapFactoryOptions = autoclass('android.graphics.BitmapFactory$Options')

        AppWidgetManager = autoclass('android.appwidget.AppWidgetManager')
        ComponentName = autoclass('android.content.ComponentName')
        RemoteViews = autoclass('android.widget.RemoteViews')

        context = get_python_activity_context()
        resources = context.getResources()
        package_name = context.getPackageName()

        image_file = os.path.join(
            context.getFilesDir().getAbsolutePath(),
            "app",
            wallpaper_path
        )

        if not os.path.exists(image_file):
            self.__log(f"Image not found: {image_file}", "ERROR")
            return

        opts = BitmapFactoryOptions()
        opts.inSampleSize = 4  # widget-safe memory usage
        src = BitmapFactory.decodeFile(image_file, opts)

        if src is None:
            self.__log("Bitmap decode failed", "ERROR")
            return

        # Crop bitmap to square
        size = min(src.getWidth(), src.getHeight())
        x = (src.getWidth() - size) // 2
        y = (src.getHeight() - size) // 2
        square = Bitmap.createBitmap(src, x, y, size, size)

        # Scale bitmap to widget size
        widget_dp = 120  # widget layout width/height in dp
        density = context.getResources().getDisplayMetrics().density
        widget_px = int(widget_dp * density)  # convert dp to pixels

        scaled_bitmap = Bitmap.createScaledBitmap(square, widget_px, widget_px, True)

        # Create rounded bitmap using Canvas
        output = Bitmap.createBitmap(widget_px, widget_px, BitmapConfig.ARGB_8888)
        canvas = Canvas(output)

        paint = Paint()
        paint.setAntiAlias(True)

        rect = Rect(0, 0, widget_px, widget_px)
        rectF = RectF(rect)

        corner_radius_px = 16 * density  # 16dp corners
        canvas.drawARGB(0, 0, 0, 0)
        canvas.drawRoundRect(rectF, corner_radius_px, corner_radius_px, paint)

        paint.setXfermode(PorterDuffXfermode(PorterDuffMode.SRC_IN))
        canvas.drawBitmap(scaled_bitmap, rect, rect, paint)

        # Update widget
        layout_id = resources.getIdentifier("carousel_widget", "layout", package_name)
        image_id = resources.getIdentifier("test_image", "id", package_name)

        views = RemoteViews(package_name, layout_id)
        views.setImageViewBitmap(image_id, output)

        component = ComponentName(context, f"{package_name}.CarouselWidgetProvider")
        appWidgetManager = AppWidgetManager.getInstance(context)
        ids = appWidgetManager.getAppWidgetIds(component)
        appWidgetManager.updateAppWidget(ids, views)

        # self.__log(f"Changed Home Screen Widget: {wallpaper_path}", "SUCCESS")



myWallpaperReceiver = MyWallpaperReceiver()
myDispatcher = dispatcher.Dispatcher()

myDispatcher.map("/start", myWallpaperReceiver.start)
myDispatcher.map("/pause", myWallpaperReceiver.pause)
myDispatcher.map("/resume", myWallpaperReceiver.resume)
myDispatcher.map("/next", myWallpaperReceiver.set_next_data)
myDispatcher.map("/stop", myWallpaperReceiver.stop)
myDispatcher.map("/set", myWallpaperReceiver.set_wallpaper)

server = osc_server.ThreadingOSCUDPServer(("0.0.0.0", get_service_port()), myDispatcher)

try:
    server.serve_forever()
except Exception as e:
    print("Service Main loop Failed:", e)
    traceback.print_exc()
    # Avoiding process is bad java.lang.SecurityException
