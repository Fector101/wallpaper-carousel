import os
from enum import Enum

from kivy.event import EventDispatcher
from kivy.properties import StringProperty, ListProperty
from kivy.utils import get_color_from_hex


SERVICE_PORT_ARGUMENT_KEY = 'service_port'
SERVICE_UI_PORT_ARGUMENT_KEY = 'ui_port'
DEFAULT_SERVICE_PORT = 5006
DEFAULT_UI_PORT = 5007
SERVICE_LIFESPAN_HOURS = 6
SERVICE_LIFESPAN_SECONDS = SERVICE_LIFESPAN_HOURS * 3600


def _rgba(r, g, b, a=1):
    return [r / 255, g / 255, b / 255, a]


def _hex(h):
    return get_color_from_hex(h)


_COLORS = {
    "PRIMARY":                {"light": _hex("#98F1DD"), "dark": _hex("#98F1DD")},
    "SECONDARY":              {"light": _hex("#262C3A"), "dark": _hex("#262C3A")},
    "BG":                     {"light": _rgba(230, 230, 230), "dark": _rgba(26, 27, 27)},
    "BG_ELEVATED":            {"light": _rgba(209, 209, 209), "dark": _rgba(59, 59, 59)},
    "BG_CARD":                {"light": _rgba(255, 255, 255), "dark": _rgba(38, 38, 38)},
    "BG_CARD_SUBTLE":         {"light": _rgba(255, 255, 255), "dark": _rgba(51, 51, 51)},
    "BG_NOTIFICATION_AREA":   {"light": _rgba(183, 212, 227), "dark": _hex("#1C6B92")},
    "BG_NOTIFICATION_CARD":   {"light": _rgba(255, 255, 255), "dark": _hex("#222020")},
    "BG_SKIP_PILL":           {"light": _hex("#EAE9E9"), "dark": _hex("#565252")},
    "BG_CHEVRON":             {"light": _rgba(226, 223, 223), "dark": _hex("#575656")},
    "TEXT_PRIMARY":           {"light": _rgba(0, 0, 0), "dark": _rgba(255, 255, 255)},
    "TEXT_SECONDARY":         {"light": _rgba(88, 85, 85), "dark": _rgba(242, 242, 242)},
    "TEXT_ACCENT":            {"light": _rgba(46, 95, 169), "dark": _hex("#C3DBFF")},
    "TEXT_SKIP":              {"light": _rgba(0, 0, 0), "dark": _hex("#EFEAEA")},
    "ICON":                   {"light": _rgba(77, 77, 77), "dark": _rgba(204, 204, 204)},
    "ICON_INACTIVE":          {"light": _rgba(77, 77, 77), "dark": _rgba(153, 153, 153)},
    "BUTTON_BG":              {"light": _rgba(230, 230, 230), "dark": _rgba(51, 51, 51)},
    "BUTTON_PRIMARY":         {"light": _rgba(55, 151, 252), "dark": _hex("#2A92FF")},
    "BUTTON_DANGER":          {"light": _rgba(243, 170, 170), "dark": _hex("#FF3F3F")},
    "BUTTON_WHITE_LAYER":     {"light": _rgba(255, 255, 255), "dark": _hex("#FEFEFE")},
    "THEME_SELECTOR_ACCENT":  {"light": _hex("#98F1DD"), "dark": _hex("#98F1DD")},
    "THEME_SELECTOR_INACTIVE":{"light": _rgba(209, 209, 209), "dark": _rgba(51, 51, 51)},
    "CHECKBOX_SELECTED":      {"light": _hex("#98F1DD"), "dark": _hex("#98F1DD")},
    "CHECKBOX_UNSELECTED":    {"light": _rgba(179, 179, 179), "dark": _rgba(179, 179, 179)},
    "INPUT_BORDER":           {"light": _rgba(179, 179, 179), "dark": _rgba(255, 255, 255)},
    "INPUT_FOCUS_BORDER":     {"light": _hex("#98F1DD"), "dark": _hex("#98F1DD")},
    "ACTIVE_INACTIVE":        {"light": _rgba(77, 77, 77), "dark": _rgba(77, 77, 77)},
    "CAMERA_BG":              {"light": _rgba(31, 31, 31), "dark": _rgba(31, 31, 31)},
    "CAMERA_BUTTON":          {"light": _rgba(51, 51, 51), "dark": _rgba(51, 51, 51)},
    "CAMERA_CAPTURE":         {"light": _rgba(230, 77, 51), "dark": _rgba(230, 77, 51)},
    "CAMERA_FLIP":            {"light": _rgba(77, 128, 204), "dark": _rgba(77, 128, 204)},
    "TAB_ACTIVE_BG":          {"light": _hex("#98F1DD"), "dark": _hex("#98F1DD")},
    "TAB_INACTIVE_BG":        {"light": _rgba(64, 64, 64), "dark": _rgba(64, 64, 64)},
    "TAB_ACTIVE_TEXT":        {"light": _rgba(0, 0, 0), "dark": _rgba(0, 0, 0)},
    "TAB_INACTIVE_TEXT":      {"light": _rgba(217, 217, 217), "dark": _rgba(217, 217, 217)},
    "FAB_BG":                 {"light": _hex("#262C3A"), "dark": _hex("#262C3A")},
    "FAB_ICON":               {"light": _hex("#98F1DD"), "dark": _hex("#98F1DD")},
    "LOG_ERROR":              {"light": _hex("#FF5252"), "dark": _hex("#FF5252")},
    "LOG_WARN":               {"light": _hex("#FFB300"), "dark": _hex("#FFB300")},
    "LOG_INFO":               {"light": _hex("#E0E0E0"), "dark": _hex("#E0E0E0")},
}

_DEFAULTS = {name: vals["dark"] for name, vals in _COLORS.items()}


class ThemeColors(EventDispatcher):
    theme = StringProperty("dark")

    PRIMARY = ListProperty(_DEFAULTS["PRIMARY"])
    SECONDARY = ListProperty(_DEFAULTS["SECONDARY"])
    BG = ListProperty(_DEFAULTS["BG"])
    BG_ELEVATED = ListProperty(_DEFAULTS["BG_ELEVATED"])
    BG_CARD = ListProperty(_DEFAULTS["BG_CARD"])
    BG_CARD_SUBTLE = ListProperty(_DEFAULTS["BG_CARD_SUBTLE"])
    BG_NOTIFICATION_AREA = ListProperty(_DEFAULTS["BG_NOTIFICATION_AREA"])
    BG_NOTIFICATION_CARD = ListProperty(_DEFAULTS["BG_NOTIFICATION_CARD"])
    BG_SKIP_PILL = ListProperty(_DEFAULTS["BG_SKIP_PILL"])
    BG_CHEVRON = ListProperty(_DEFAULTS["BG_CHEVRON"])
    TEXT_PRIMARY = ListProperty(_DEFAULTS["TEXT_PRIMARY"])
    TEXT_SECONDARY = ListProperty(_DEFAULTS["TEXT_SECONDARY"])
    TEXT_ACCENT = ListProperty(_DEFAULTS["TEXT_ACCENT"])
    TEXT_SKIP = ListProperty(_DEFAULTS["TEXT_SKIP"])
    ICON = ListProperty(_DEFAULTS["ICON"])
    ICON_INACTIVE = ListProperty(_DEFAULTS["ICON_INACTIVE"])
    BUTTON_BG = ListProperty(_DEFAULTS["BUTTON_BG"])
    BUTTON_PRIMARY = ListProperty(_DEFAULTS["BUTTON_PRIMARY"])
    BUTTON_DANGER = ListProperty(_DEFAULTS["BUTTON_DANGER"])
    BUTTON_WHITE_LAYER = ListProperty(_DEFAULTS["BUTTON_WHITE_LAYER"])
    THEME_SELECTOR_ACCENT = ListProperty(_DEFAULTS["THEME_SELECTOR_ACCENT"])
    THEME_SELECTOR_INACTIVE = ListProperty(_DEFAULTS["THEME_SELECTOR_INACTIVE"])
    CHECKBOX_SELECTED = ListProperty(_DEFAULTS["CHECKBOX_SELECTED"])
    CHECKBOX_UNSELECTED = ListProperty(_DEFAULTS["CHECKBOX_UNSELECTED"])
    INPUT_BORDER = ListProperty(_DEFAULTS["INPUT_BORDER"])
    INPUT_FOCUS_BORDER = ListProperty(_DEFAULTS["INPUT_FOCUS_BORDER"])
    ACTIVE_INACTIVE = ListProperty(_DEFAULTS["ACTIVE_INACTIVE"])
    CAMERA_BG = ListProperty(_DEFAULTS["CAMERA_BG"])
    CAMERA_BUTTON = ListProperty(_DEFAULTS["CAMERA_BUTTON"])
    CAMERA_CAPTURE = ListProperty(_DEFAULTS["CAMERA_CAPTURE"])
    CAMERA_FLIP = ListProperty(_DEFAULTS["CAMERA_FLIP"])
    TAB_ACTIVE_BG = ListProperty(_DEFAULTS["TAB_ACTIVE_BG"])
    TAB_INACTIVE_BG = ListProperty(_DEFAULTS["TAB_INACTIVE_BG"])
    TAB_ACTIVE_TEXT = ListProperty(_DEFAULTS["TAB_ACTIVE_TEXT"])
    TAB_INACTIVE_TEXT = ListProperty(_DEFAULTS["TAB_INACTIVE_TEXT"])
    FAB_BG = ListProperty(_DEFAULTS["FAB_BG"])
    FAB_ICON = ListProperty(_DEFAULTS["FAB_ICON"])
    LOG_ERROR = ListProperty(_DEFAULTS["LOG_ERROR"])
    LOG_WARN = ListProperty(_DEFAULTS["LOG_WARN"])
    LOG_INFO = ListProperty(_DEFAULTS["LOG_INFO"])

    def on_theme(self, instance, value):
        for name, vals in _COLORS.items():
            setattr(self, name, vals[value])


theme_colors = ThemeColors()


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
VERSION="1.0.8"
