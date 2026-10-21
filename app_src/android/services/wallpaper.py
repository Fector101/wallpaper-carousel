import logging, os, traceback

from utils.helper import write_logs_to_file
write_logs_to_file()

from android_notify import Notification, logger as android_notify_logger
from android_notify.config import get_python_service, on_android_platform, get_python_activity_context, get_package_name
from android_notify.internal.java_classes import BuildVersion, autoclass, Intent, PendingIntent, String, cast
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


# ---------------------------------------

# package = get_package_name()

# def add_broadcast_button(notification, text, action, request_code):
#     """Add a notification button that broadcasts `action` (implicit, package-scoped).

#     `notification.addButton(receiver_name=...)` builds an explicit
#     `Intent(context, <pkg>.<receiver_name>)`, so it can only reach a manifest-declared
#     receiver. p4a's `android.broadcast.BroadcastReceiver` is matched by intent-filter
#     only (an explicit intent never reaches a runtime-registered receiver), so the button
#     must broadcast the action instead of naming a component. `setPackage()` keeps the
#     intent deliverable under Android 14's safer-intents rule for non-exported receivers.
#     """
#     if not on_android_platform():
#         return  # `notification.builder` is None off-device
#     context = get_python_activity_context()
#     intent = Intent(action)
#     intent.setPackage(package)
#     pending_action_intent = PendingIntent.getBroadcast(
#         context, request_code, intent,
#         PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE)
#     action_text = cast('java.lang.CharSequence', String(text))
#     notification.builder.addAction(int(context.getApplicationInfo().icon), action_text, pending_action_intent)
# ---------------------------------------


# create notification
notification = Notification(title="Starting Carousel...", name="from service",channel_id="service_channel")
notification.setObeyUserClear(True) # don't reappear when updated after users clear from Tray


# ---------------------------------------
notification.addButton(text="Stop", receiver_name="CarouselReceiver", action="ACTION_STOP")
notification.addButton(text="Skip", receiver_name="CarouselReceiver", action="ACTION_SKIP")
# add_broadcast_button(notification, text="Stop", action=package + ".ACTION_STOP", request_code=1)
# add_broadcast_button(notification, text="Skip", action=package + ".ACTION_SKIP", request_code=2)
# ---------------------------------------

builder = notification.fill_args()


# Promote background service to foreground service and send notification
service.startForeground(notification.id, builder.build(), foreground_type)
service.setAutoRestartService(True)


# ---------------------------------------
# def on_broadcast(*args, **kwargs):
#     print(f"BroadcastReceiver: args: {args}, kwargs: {kwargs}")

# try:
#     from utils.android_broadcast import BroadcastReceiver
#     br=BroadcastReceiver(on_broadcast, actions=[package+'.ACTION_STOP',package+'.ACTION_SKIP'])
#     br.start()
# except Exception as e:
#     print(e)
#     traceback.print_exc()
# # ---------------------------------------


# start service server, which:
# - runs wallpaper changes on time intervals,
# - keeps detect screen on & off broadcast receiver alive
# - and sends and receives requests from app main thread changes receives.
start_service_server(notification)
