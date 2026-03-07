import logging

from utils.helper import write_logs_to_file
write_logs_to_file()

from android_notify import Notification, logger as android_notify_logger
from android_notify.config import get_python_service, on_android_platform
from android_notify.internal.java_classes import BuildVersion, autoclass

from utils.logger import app_logger
from utils.service_helper import start_service_server


android_notify_logger.setLevel(logging.WARNING if on_android_platform() else logging.ERROR)
app_logger.setLevel(logging.INFO)

service = get_python_service()
foreground_type = autoclass("android.content.pm.ServiceInfo").FOREGROUND_SERVICE_TYPE_SPECIAL_USE if on_android_platform() and BuildVersion.SDK_INT >= 30 else 0

Notification.createChannel(id="service_channel",name="Carousel Service",description="For Controlling and Previewing Next Wallpaper")
notification = Notification(title="Starting Carousel...", name="from service",channel_id="service_channel")
notification.setObeyUserClear(True) # don't reappear when updated after users clear from Tray
notification.addButton(text="Stop", receiver_name="CarouselReceiver", action="ACTION_STOP")
notification.addButton(text="Skip", receiver_name="CarouselReceiver", action="ACTION_SKIP")
builder = notification.fill_args()

service.startForeground(notification.id, builder.build(), foreground_type)
service.setAutoRestartService(True)

start_service_server(notification)
