import os
from enum import Enum



SERVICE_PORT_ARGUMENT_KEY = 'service_port'
SERVICE_UI_PORT_ARGUMENT_KEY = 'ui_port'
DEFAULT_SERVICE_PORT = 5006
DEFAULT_UI_PORT = 5007
SERVICE_LIFESPAN_HOURS = 6
SERVICE_LIFESPAN_SECONDS = SERVICE_LIFESPAN_HOURS * 3600

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WALLPAPER_SERVICE_PATH = os.path.join( str(BASE_DIR), "android", "services", "wallpaper.py" )


class ServiceServerAddress(Enum):
    START = "/start"
    PAUSE = "/pause"
    RESUME = "/resume"
    STOP = "/stop"
    CHANGE_NEXT = "/change-next"
    SET_WALLPAPER = "/set-wallpaper"
    TOGGLE_HOME_SCREEN_WIDGET_CHANGES = "/toggle_home_screen_widget_changes"
    APPLY_NEXT_WALLPAPER = "/apply_next_wallpaper"
    SERVICE_STATUS = "/service_status"

    RESUME_USING_INTERVAL_LOOP = "/resume_using_interval_loop"
    RESUME_USING_ON_WAKE = "/pause_using_interval_loop"


class ServiceStatus(Enum):
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    FAILED = "failed"
    RESTARTING = "restarting"
    RETRYING = "retrying"
    ATTEMPT_FAILED = "attempt_failed"

DEV=0
VERSION="1.0.11"
