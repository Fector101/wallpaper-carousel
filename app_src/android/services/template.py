print("Entered python Service File...")

import os, threading
import time
import random, traceback
from os import environ
from jnius import autoclass
from pythonosc import dispatcher, osc_server, udp_client

from android_notify import Notification
from android_notify.config import get_python_service, get_python_activity_context

BuildVersion = autoclass("android.os.Build$VERSION")
ServiceInfo = autoclass("android.content.pm.ServiceInfo")

def get_service_port():
    service_port = None
    try:
        service_port = int(environ.get('PYTHON_SERVICE_ARGUMENT', '5006'))
    except (TypeError, ValueError):
        service_port = 5006
    return service_port


# Start foreground service
service = get_python_service()
foreground_type = ServiceInfo.FOREGROUND_SERVICE_TYPE_DATA_SYNC if BuildVersion.SDK_INT >= 30 else 0
context = get_python_activity_context()

notification = Notification(title="Service Running for 0h 0m 0s", message="service lifespan: 6hrs")
builder = notification.start_building()
service.startForeground(notification.id, builder.build(), foreground_type)
service.setAutoRestartService(True)  # auto-restart if killed

print("Foreground Service is alive. Entering main loop...")

fmt = lambda s: f"{int(s // 3600)}h {int((s % 3600) // 60)}m {int(s % 60)}s"


class MyWallpaperReceiver:
    def __init__(self):
        self.live = True
        self.next_wallpaper_path = ''
        self.current_sleep = 1
        self.current_wait_seconds = 2 * 60
        self.service_start_time = time.time()
        self.changes = 0
        self.start()

    def heart(self):
        start = time.time()
        while self.live:
            elapsed = time.time() - start
            notification.updateTitle(f"Total runtime {fmt(elapsed)}")
            time.sleep(1)

    def start(self, data=None):
        threading.Thread(target=self.heart, daemon=True).start()

    def stop(self, data=None):
        self.live = False
        notification.cancel()

    def pause(self, data=None):
        notification.updateTitle("Carousel Pause")
        self.current_sleep = 1000 ** 100
        pass

    def resume(self, data=None):
        self.current_sleep = 1

    def next(self, data=None):
        self.current_wait_seconds = 0

    def set_wallpaper(self, wallpaper_path):
        change_wallpaper(wallpaper_path)

    def destroy(self, data=None):
        service.stopSelf()


myWallpaperReceiver = MyWallpaperReceiver()
myDispatcher = dispatcher.Dispatcher()

myDispatcher.map("/start", myWallpaperReceiver.start)
myDispatcher.map("/pause", myWallpaperReceiver.pause)
myDispatcher.map("/resume", myWallpaperReceiver.resume)
myDispatcher.map("/next", myWallpaperReceiver.next)
myDispatcher.map("/stop", myWallpaperReceiver.stop)
myDispatcher.map("/destroy", myWallpaperReceiver.destroy)
myDispatcher.map("/set", myWallpaperReceiver.set_wallpaper)

server = osc_server.ThreadingOSCUDPServer(("0.0.0.0", get_service_port()), myDispatcher)

try:
    server.serve_forever()
except Exception as e:
    print("Service Main loop Failed:", e)
    traceback.print_exc()
    # Avoiding process is bad java.lang.SecurityException
