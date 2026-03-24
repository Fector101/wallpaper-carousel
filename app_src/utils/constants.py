import os
from enum import Enum


SERVICE_PORT_ARGUMENT_KEY = 'service_port'
SERVICE_UI_PORT_ARGUMENT_KEY = 'ui_port'
DEFAULT_SERVICE_PORT = 5006
DEFAULT_UI_PORT = 5007
SERVICE_LIFESPAN_HOURS = 6
SERVICE_LIFESPAN_SECONDS = SERVICE_LIFESPAN_HOURS * 3600

LIGHT_MODE_BG = [0.7,0.7, 0.7, 1]
DARK_MODE_BG = [26/255, 27/255, 27/255, 1]

TEXT_COLOR_PRIMARY_LIGHT = [0, 0, 0, 1]
TEXT_COLOR_PRIMARY_DARK = [1, 1, 1, 1]  # #FFFFFF

TEXT_COLOR_SECONDARY_LIGHT = [88/255, 85/255, 85/255, 1]
TEXT_COLOR_SECONDARY_DARK = [242/255, 242/255, 242/255, 1]  # #F2F2F2

BUTTON_BG_LIGHT = []
BUTTON_BG_DARK = [.2,.2,.2,1]


THEME_PRIMARY_COLOR = "#98F1DD"
THEME_SECONDARY_COLOR = "#262C3A"


# For helper.py - constants.py should be in same folder as helper.py or this should be moved to helper.py because not really used anywhere else
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WALLPAPER_SERVICE_PATH = os.path.join( BASE_DIR, "android", "services", "wallpaper.py" )


class ServiceServerAddress(Enum):
    START = "/start"
    PAUSE = "/pause"
    RESUME = "/resume"
    STOP = "/stop"
    CHANGE_NEXT = "/change-next"
    SET_WALLPAPER = "/set-wallpaper"
    TOGGLE_HOME_SCREEN_WIDGET_CHANGES = "/toggle_home_screen_widget_changes"
    APPLY_NEXT_WALLPAPER = "/apply_next_wallpaper"

    RESUME_USING_INTERVAL_LOOP = "/resume_using_interval_loop"
    RESUME_USING_ON_WAKE = "/pause_using_interval_loop"

DEV=0
VERSION="1.0.5"
