from typing import Optional
from kivymd.app import MDApp
from utils.ui_service_bridge import UIServiceListener, UIServiceMessenger
from typing import cast
from utils.image_operations import ImageOperation

# types/screen_manager_model.py
from typing import Callable, Literal, Any

class BottomButtonBarModel:
    # callbacks provided from outside
    on_camera: Callable[..., Any] | None
    on_settings: Callable[..., Any] | None

    # inner widgets
    button_box: "MDBoxLayout"
    btn_camera: "MDIconButton"
    btn_settings: "MDIconButton"

    # public API
    def changeBottomBtnsTheme(self, app, theme: str) -> None: ...
    def hide(self) -> None: ...
    def show(self) -> None: ...

    # internal handlers (still useful for autocomplete sometimes)
    def _camera_pressed(self, *args) -> None: ...
    def _settings_pressed(self, *args) -> None: ...
    def color_tab_buttons(self, current: Literal["thumbs", "fullscreen", "settings", "welcome", "logs"]) -> None: ...

class MyScreenManagerModel:
    # screens
    gallery_screen: "GalleryScreen"
    full_screen: "FullscreenScreen"
    settings_screen: "SettingsScreen"
    welcome_screen: "WelcomeScreen"
    log_screen: "LogsScreen"

    # navigation helpers (functions assigned in real class)
    go_to_settings: Callable
    go_to_thumbs: Callable

    # kivy ScreenManager state
    current: Literal["thumbs", "fullscreen", "settings", "welcome", "logs"]

    # public API
    def open_image_in_full_screen(self, index: int) -> None: ...


    def bind(self, **kwargs: Callable[..., Any]) -> None: ...


class WallpaperCarouselAppModel:
    interval: int
    device_theme: str

    service_port: Optional[int]
    ui_messenger_to_service: Optional[UIServiceMessenger]
    file_operation: Optional[ImageOperation]
    ui_service_listener: Optional[UIServiceListener]

    root_layout: object
    sm: MyScreenManagerModel
    bottom_bar: BottomButtonBarModel

    def bind(self, **kwargs: Callable[..., Any]) -> None: ...
    def monitor_dark_and_light_device_change(self) -> Literal["light","dark"]: ...

def get_app() -> WallpaperCarouselAppModel:
    return cast(WallpaperCarouselAppModel, MDApp.get_running_app())

from enum import Enum

class GalleryTabs(Enum):
    DAY = "Day"
    NOON = "Noon"
    BOTH = "Both"

# # Usage examples
# print(TimeOfDay.DAY)  # TimeOfDay.DAY
# print(TimeOfDay.DAY.value)  # "day"
# print(TimeOfDay("day"))  # TimeOfDay.DAY
# print(TimeOfDay.NOON.name)  # "NOON"