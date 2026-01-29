import json
import traceback, threading
import os, random
import time, logging
from android_notify.config import on_android_platform

if on_android_platform():
    try:
        from utils.helper import start_logging
        start_logging()
    except Exception as e:
        print("File Logger Failed", e)
        traceback.print_exc()
        # e-File Logger Failed JVM exception occurred: Attempt to invoke virtual method 'android.view.WindowManager org.kivy.android.PythonActivity.getWindowManager()' on a null object reference java.lang.NullPointerException

print("Entered Wallpaper Foreground Service...")
from jnius import autoclass
from pythonosc import dispatcher, osc_server, udp_client
from android_notify import Notification, logger as android_notify_logger
from android_notify.config import get_python_service, get_python_activity_context, on_android_platform
from android_notify.internal.java_classes import BuildVersion, BitmapFactory
from android_widgets import Layout, RemoteViews, AppWidgetManager

from utils.logger import app_logger
from utils.helper import change_wallpaper, appFolder, format_time_remaining
from utils.constants import SERVICE_PORT_ARGUMENT_KEY, SERVICE_UI_PORT_ARGUMENT_KEY,DEFAULT_SERVICE_PORT, SERVICE_LIFESPAN_HOURS

android_notify_logger.setLevel(logging.WARNING if on_android_platform() else logging.ERROR)
app_logger.setLevel(logging.INFO)

class ReceivedData:
    # Always use `json.dumps(args)` to start service.
    def __init__(self):
        self.data = self.__get_object_sent_from_ui()
        self.__store_service_port(self.service_port)

    @staticmethod
    def __get_object_sent_from_ui():
        data = {}
        try:
            service_argument = os.environ.get('PYTHON_SERVICE_ARGUMENT', json.dumps(''))
            data = json.loads(service_argument)
        except Exception as error_getting_ui_data:
            app_logger.exception(f"Error getting ui data {error_getting_ui_data}")
            traceback.print_exc()
        return data

    @property
    def service_port(self):
        port = DEFAULT_SERVICE_PORT
        if SERVICE_PORT_ARGUMENT_KEY in self.data:
            port = self.data[SERVICE_PORT_ARGUMENT_KEY]
            try:
                port = int(port)
            except ValueError as error_changing_port_to_int:
                app_logger.exception(f"Error: {error_changing_port_to_int}, received port: '{port}'")
                port = DEFAULT_SERVICE_PORT
        return port

    @property
    def ui_port(self):
        port = None
        if SERVICE_UI_PORT_ARGUMENT_KEY in self.data:
            port = self.data[SERVICE_UI_PORT_ARGUMENT_KEY]
        return port

    @staticmethod
    def __store_service_port(port):
        try:
            service_port_store_path = os.path.join(appFolder(), 'port.txt')
            with open(service_port_store_path, "w") as f:
                f.write(str(port))
            app_logger.info(f"Stored Service Port for Java - Port: {port}, file_path: {service_port_store_path}")
        except Exception as error_write_port:
            app_logger.exception(f"Error writing wallpaper port: {error_write_port}")
            traceback.print_exc()


receivedData = ReceivedData()



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
        # rint("service found:",images)
        if not images:
            app_logger.exception(f"Warning: No images found in {download_folder_path}")
            return '', ''

        wallpaper_path = random.choice(images)
        return os.path.basename(wallpaper_path), wallpaper_path
    except Exception as error_getting_next_wallpaper:
        app_logger.exception(f"Failed to get next wallpaper: {error_getting_next_wallpaper}")
        return '', ''


def get_interval():
    try:
        from utils.config_manager import ConfigManager
        config = ConfigManager()
        t = int(float(config.get_interval()) * 60)
        return t
    except Exception as error_getting_saved_interval:
        app_logger.exception(f"Service Failed to get Interval: {error_getting_saved_interval}")
        traceback.print_exc()
        return 120


def get_service_lifespan_text(elapsed_seconds):
    """Get service lifespan text like 'service lifespan: 6hrs'"""
    remaining_hours = max(0, SERVICE_LIFESPAN_HOURS - int(elapsed_seconds // 3600))
    return f"service lifespan: {remaining_hours}hrs"


class MyWallpaperReceiver:
    def __init__(self):
        self.current_wallpaper = None
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
                break

            value_ = format_time_remaining(get_interval()) if self.current_wait_seconds <= 0 else format_time_remaining(self.current_wait_seconds)
            self.__send_data_to_ui("/countdown_change", {"seconds": value_})
            notification.updateTitle(f"Next in {value_}")

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
            self.__send_data_to_ui("/changed_homescreen_widget",
                                   {"current_wallpaper": None, "next_wallpaper": self.next_wallpaper_path})
            self.__send_data_to_ui("/changed_wallpaper",
                                   {"current_wallpaper": None, "next_wallpaper": self.next_wallpaper_path})
            notification.setData({"next wallpaper path": self.next_wallpaper_path})

            # Wait for a while
            # time.sleep(get_interval())
            self.__count_down()

            if not self.skip_now:
                # Then change wallpaper
                self.current_wallpaper = self.next_wallpaper_path
                self.set_wallpaper(self.next_wallpaper_path)

                self.__write_wallpaper_path_to_file(self.next_wallpaper_path)
            self.skip_now = False

    def __write_wallpaper_path_to_file(self, wallpaper_path):
        # Writing for Java to see for home screen widget
        if not wallpaper_path:
            return
        if not os.path.exists(wallpaper_path):
            app_logger.error(f"Image - {wallpaper_path} does not exist, can't store path")
            return

        current_wallpaper_store_path = os.path.join(appFolder(), 'wallpaper.txt')
        with open(current_wallpaper_store_path, "w") as f:
            f.write(wallpaper_path)

        try:
            self.update_widget_image(wallpaper_path)
        except Exception as error_updating_widget:
            app_logger.exception(f"Error update_widget_image  -{error_updating_widget}")
            traceback.print_exc()

        #try:
          #  self.changed_widget_text()
        #except Exception as e:
         #   self.__log(f"Error changed_widget_text -{e} ping Java Listener", "WARNING")
         #   traceback.print_exc()
        #self.changes += 1

    @staticmethod
    def __set_next_img_in_notification(wallpaper_path):
        if not wallpaper_path:
            return
        if os.path.exists(wallpaper_path):
            notification.setLargeIcon(wallpaper_path)
        else:
            app_logger.error(f"Image - {wallpaper_path} does not exist, can't set notification preview")

    def start(self, data=None):
        # self.__start_main_loop()
        pass

    def stop(self, *args):
        app_logger.info(f"stop args: {args}")
        self.__send_data_to_ui("/stopped", {})
        time.sleep(1)
        self.current_wait_seconds = 0
        self.live = False
        # notification.cancel() android auto removes it
        service.setAutoRestartService(False) # On Android 12 service continued after swiping app from Recents this is best bet
        service.stopSelf()

    def pause(self, _=None):
        notification.updateTitle("Carousel Pause")
        self.current_sleep = 1000 ** 100
        pass

    def resume(self, _=None):
        self.current_sleep = 1

    def set_next_data(self, *_):
        # app_logger.info(f"next args: {args}")
        self.skip_now = True
        self.current_wait_seconds = 0

    @staticmethod
    def __send_data_to_ui(path, dict_data):
        client.send_message(address=path,value=json.dumps(dict_data))

    def set_wallpaper(self, wallpaper_path):
        self.__send_data_to_ui("/changed_wallpaper", {"current_wallpaper": self.current_wallpaper,"next_wallpaper":self.next_wallpaper_path})
        change_wallpaper(wallpaper_path)

    def changed_widget_text(self):
        appWidgetManager = AppWidgetManager("CarouselWidgetProvider")

        text_layout = Layout("carousel_widget")
        views = RemoteViews(layout=text_layout)
        views.setTextViewText(text_id="widget_text", text=f"Count: {self.changes}")

        appWidgetManager.updateAppWidget(java_view_object=views.main)

    def update_widget_image(self, wallpaper_path):
        if not on_android_platform():
            self.__send_data_to_ui("/changed_homescreen_widget", {"current_wallpaper": self.current_wallpaper,"next_wallpaper":None})
            app_logger.warning("Failed to Change Home Screen Widget: Not on Android platform")
            return None
        context = get_python_activity_context()
        Bitmap = autoclass('android.graphics.Bitmap')
        BitmapConfig = autoclass('android.graphics.Bitmap$Config')
        Canvas = autoclass('android.graphics.Canvas')
        Paint = autoclass('android.graphics.Paint')
        Rect = autoclass('android.graphics.Rect')
        RectF = autoclass('android.graphics.RectF')
        PorterDuffMode = autoclass('android.graphics.PorterDuff$Mode')
        PorterDuffXfermode = autoclass('android.graphics.PorterDuffXfermode')

        BitmapFactoryOptions = autoclass('android.graphics.BitmapFactory$Options')

        AppWidgetManager_ = autoclass('android.appwidget.AppWidgetManager')
        ComponentName = autoclass('android.content.ComponentName')
        RemoteViews_ = autoclass('android.widget.RemoteViews')
        View = autoclass('android.view.View')
        resources = context.getResources()
        package_name = context.getPackageName()

        image_file = os.path.join(
            context.getFilesDir().getAbsolutePath(),
            "app",
            wallpaper_path
        )

        if not os.path.exists(image_file):
            app_logger.error(f"Image not found: {image_file}")
            return None

        opts = BitmapFactoryOptions()
        opts.inSampleSize = 4  # widget-safe memory usage
        src = BitmapFactory.decodeFile(image_file, opts)

        if src is None:
            app_logger.error("Bitmap decode failed")
            return None

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
        placeholder_id = resources.getIdentifier("placeholder_text", "id", package_name)
        app_logger.info(f"layout_id:{layout_id}, image_id:{image_id}, placeholder_id:{placeholder_id}")
        views = RemoteViews_(package_name, layout_id)
        views.setImageViewBitmap(image_id, output)

        views.setViewVisibility(image_id, View.VISIBLE)
        views.setViewVisibility(placeholder_id, View.GONE)

        component = ComponentName(context, f"{package_name}.CarouselWidgetProvider")
        appWidgetManager = AppWidgetManager_.getInstance(context)
        ids = appWidgetManager.getAppWidgetIds(component)
        appWidgetManager.updateAppWidget(ids, views)
        self.__send_data_to_ui("/changed_homescreen_widget", {"current_wallpaper": self.current_wallpaper,"next_wallpaper":None})
        return None
        # app_logger.info(f"Changed Home Screen Widget: {wallpaper_path}")


ServiceInfo = autoclass("android.content.pm.ServiceInfo") if on_android_platform() else None

# print("appFolder()",appFolder())
download_folder_path = os.path.join(appFolder(), "wallpapers")
# download_folder_path = download_folder_path if os.path.exists(download_folder_path) else os.path.join(appFolder(),"..", "wallpapers")


service = get_python_service()
foreground_type = ServiceInfo.FOREGROUND_SERVICE_TYPE_DATA_SYNC if BuildVersion.SDK_INT >= 30 else 0

notification = Notification(title="Next in 02:00", message=f"service lifespan: {SERVICE_LIFESPAN_HOURS}hrs",name="from service")
notification.setData({"next wallpaper path": "test.jpg"})
notification.addButton(text="Stop", receiver_name="CarouselReceiver", action="ACTION_STOP")
notification.addButton(text="Skip", receiver_name="CarouselReceiver", action="ACTION_SKIP")
builder = notification.start_building()
service.startForeground(notification.id, builder.build(), foreground_type)
service.setAutoRestartService(True)


client = udp_client.SimpleUDPClient("0.0.0.0", receivedData.ui_port)
myWallpaperReceiver = MyWallpaperReceiver()
myDispatcher = dispatcher.Dispatcher()

myDispatcher.map("/start", myWallpaperReceiver.start)
myDispatcher.map("/pause", myWallpaperReceiver.pause)
myDispatcher.map("/resume", myWallpaperReceiver.resume)
myDispatcher.map("/change-next", myWallpaperReceiver.set_next_data)
myDispatcher.map("/stop", myWallpaperReceiver.stop)
myDispatcher.map("/set-wallpaper", myWallpaperReceiver.set_wallpaper)

server = osc_server.ThreadingOSCUDPServer(("0.0.0.0", receivedData.service_port), myDispatcher)

if not on_android_platform():
    # (venv) fabian@fabian-HP-Pavilion-Laptop-15t-eg300:~/Documents/Laner/mobile/app_src$ python3 -m android.services.wallpaper
    app_logger.info(f"Service Running From PC- {server.server_address[0]}:{server.server_address[1]}")


try:
    server.serve_forever()
except Exception as e:
    app_logger.exception(f"Service Main loop Failed: {e}")
    traceback.print_exc()
    # Avoiding process is bad java.lang.SecurityException
