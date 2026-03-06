import logging

from utils.helper import write_logs_to_file
write_logs_to_file()

from android_notify import Notification, logger as android_notify_logger
from android_notify.config import get_python_service, on_android_platform, autoclass
from android_notify.internal.java_classes import BuildVersion

from utils.logger import app_logger
from utils.constants import SERVICE_PORT_ARGUMENT_KEY
from utils.service_helper import ReceivedData, start_service_server


android_notify_logger.setLevel(logging.WARNING if on_android_platform() else logging.ERROR)
app_logger.setLevel(logging.INFO)

receivedData = ReceivedData()
service = get_python_service()
foreground_type = autoclass("android.content.pm.ServiceInfo").FOREGROUND_SERVICE_TYPE_SPECIAL_USE if on_android_platform() and BuildVersion.SDK_INT >= 30 else 0

Notification.createChannel(id="service_channel",name="Carousel Service",description="For Controlling and Previewing Next Wallpaper")
notification = Notification(title="Next in 02:00", name="from service",channel_id="service_channel",id=101)
notification.setData({"next wallpaper path": "test.jpg", SERVICE_PORT_ARGUMENT_KEY: receivedData.service_port})
notification.setObeyUserClear(True) # don't show after users clear from Tray
notification.addButton(text="Stop", receiver_name="CarouselReceiver", action="ACTION_STOP")
notification.addButton(text="Skip", receiver_name="CarouselReceiver", action="ACTION_SKIP")
builder = notification.fill_args()

service.startForeground(notification.id, builder.build(), foreground_type)
service.setAutoRestartService(True)

start_service_server()
