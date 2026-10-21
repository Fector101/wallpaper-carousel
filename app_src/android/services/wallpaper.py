import logging, os

from utils.helper import write_logs_to_file
write_logs_to_file()

from android_notify import Notification, logger as android_notify_logger
from android_notify.config import get_python_service, on_android_platform
from android_notify.internal.java_classes import BuildVersion, autoclass
from android_notify.widgets.images import get_img_absolute_path

from utils.logger import app_logger
from utils.service_helper import start_service_server

# setting log levels tom avoid logs overload
android_notify_logger.setLevel(logging.WARNING if on_android_platform() else logging.ERROR)
app_logger.setLevel(logging.INFO)


# get service type
service = get_python_service()
foreground_type = autoclass("android.content.pm.ServiceInfo").FOREGROUND_SERVICE_TYPE_SPECIAL_USE if on_android_platform() and BuildVersion.SDK_INT >= 34 else 0


# set custom notification icon
appIcon_relative_to_main_path = os.path.join("assets","icons","icon.png")
Notification.app_icon = get_img_absolute_path(appIcon_relative_to_main_path) if on_android_platform() else appIcon_relative_to_main_path


# create notification channel
Notification.createChannel(id="service_channel",name="Carousel Service",description="For Controlling and Previewing Next Wallpaper")


# create notification
notification = Notification(title="Starting Carousel...", name="from service",channel_id="service_channel")
notification.setObeyUserClear(True) # don't reappear when updated after users clear from Tray
notification.addButton(text="Stop", receiver_name="CarouselReceiver", action="ACTION_STOP")
notification.addButton(text="Skip", receiver_name="CarouselReceiver", action="ACTION_SKIP")
builder = notification.fill_args()


# Promote background service to foreground service and send notification
service.startForeground(notification.id, builder.build(), foreground_type)
service.setAutoRestartService(True)

# start service server, which:
# - runs wallpaper changes on time intervals,
# - keeps detect screen on & off broadcast receiver alive
# - and sends and receives requests from app main thread changes receives.
start_service_server(notification)
