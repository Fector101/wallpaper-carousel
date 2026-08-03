import json, os
import traceback
from pathlib import Path
from ui.widgets.android import toast

def is_platform_android():
    # Took this from kivy to fix my logs in P4A.hook, so no need to import things I don't need by doing `from kivy.utils import platform`
    if os.getenv("MAIN_ACTIVITY_HOST_CLASS_NAME"):
        return True
    kivy_build = os.environ.get('KIVY_BUILD', '')
    if kivy_build in {'android'}:
        return True
    elif 'P4A_BOOTSTRAP' in os.environ:
        return True
    elif 'ANDROID_ARGUMENT' in os.environ:
        return True

    return False

class ConfigManager:
    DEFAULT_CONFIG = {
        "interval_mins": 2.0,
        "cols": 0,
        "wallpapers": [],
        "noon_wallpapers":[],
        "day_wallpapers":[],
        "use_on_wake": False,
        "use_group_by_date": True,
        "theme_preference": "dark",
        "start_on_app_launch": True,
        "start_on_boot": True,
    }

    def __init__(self):
        self._ensure_config()

    if is_platform_android():
        from android.storage import app_storage_path  # type: ignore
        config_dir = app_storage_path()
    else:
        config_dir = os.getcwd()

    config_path = Path(config_dir) / "config.json"

    def _ensure_config(self):
        if not self.config_path.exists():
            self.write(self.DEFAULT_CONFIG)

    @classmethod
    def read(cls):
        try:
            with open(cls.config_path, "r") as f:
                return json.load(f)
        except Exception as error_reading_config_file:
            print(f"error reading config file: {error_reading_config_file}")
            traceback.print_exc()
            try:
                cls.write(cls.DEFAULT_CONFIG)
                return cls.DEFAULT_CONFIG
            except PermissionError:
                toast("PD: Cannot access config file")
            except Exception as e:
                toast(str(e))
                traceback.print_exc()
    @classmethod
    def write(cls, data):
        try:
            with open(cls.config_path, "w") as f:
                json.dump(data, f, indent=4)
        except PermissionError:
            toast("PD: Cannot access config file")
        except Exception as e:
            toast(str(e))
            traceback.print_exc()

    # ---------- INTERVAL ----------
    def get_interval(self):
        return self.read().get("interval_mins", 2)

    def set_interval(self, mins: float):
        data = self.read()
        data["interval_mins"] = mins
        self.write(data)

    # ---------- WALLPAPERS ----------
    def get_wallpapers(self):
        return self.read().get("wallpapers", [])

    def set_wallpapers(self, lst):
        data = self.read()
        data["wallpapers"] = lst
        self.write(data)

    def add_wallpaper(self, path):
        data = self.read()
        if path not in data["wallpapers"]:
            data["wallpapers"].append(path)
            self.write(data)

    def remove_wallpaper(self, path):
        data = self.read()
        if path in data["wallpapers"]:
            data["wallpapers"].remove(path)
            self.write(data)

    def get_noon_wallpapers(self):
        return self.read().get("noon_wallpapers", [])

    def get_day_wallpapers(self):
        return self.read().get("day_wallpapers", [])

    def add_wallpaper_to_day_wallpapers(self, path):
        data = self.read()
        if path not in data["day_wallpapers"]:
            data["day_wallpapers"].append(path)
            self.write(data)

    def add_wallpaper_to_noon_wallpapers(self, path):
        data = self.read()
        if path not in data["noon_wallpapers"]:
            data["noon_wallpapers"].append(path)
            self.write(data)

    def remove_wallpaper_to_from(self, wallpaper_key_name, path):
        data = self.read()
        if path in data[wallpaper_key_name]:
            data[wallpaper_key_name].remove(path)
            self.write(data)

    @classmethod
    def get_on_wake_state(cls):
        s=cls.read().get("use_on_wake", False)
        # print("returned",s)
        return s

    @classmethod
    def set_on_wake_state(cls, state: bool):
        # print('called',state)
        data = cls.read()
        data["use_on_wake"] = state
        cls.write(data)

    @classmethod
    def get_cols(cls):
        s=cls.read().get("cols", cls.DEFAULT_CONFIG["cols"])
        return s

    @classmethod
    def set_cols(cls, cols: int):
        data = cls.read()
        data["cols"] = cols
        cls.write(data)

    @property
    def get_use_group_by_date(self):
        if "use_group_by_date" in self.read():
            return self.read().get("use_group_by_date", True)
        else:
            self.set_use_group_by_date(True)
            return True
    def set_use_group_by_date(self, state: bool):
        data = self.read()
        data["use_group_by_date"] = state
        self.write(data)

    # ---------- THEME PREFERENCE ----------
    @classmethod
    def get_theme_preference(cls):
        return cls.read().get("theme_preference", "adaptive")

    @classmethod
    def set_theme_preference(cls, preference: str):
        data = cls.read()
        data["theme_preference"] = preference
        cls.write(data)

    # ---------- START PREFERENCES ----------
    @classmethod
    def get_start_on_app_launch(cls):
        return cls.read().get("start_on_app_launch", True)

    @classmethod
    def set_start_on_app_launch(cls, state: bool):
        data = cls.read()
        data["start_on_app_launch"] = state
        cls.write(data)

    @classmethod
    def get_start_on_boot(cls):
        return cls.read().get("start_on_boot", True)

    @classmethod
    def set_start_on_boot(cls, state: bool):
        data = cls.read()
        data["start_on_boot"] = state
        cls.write(data)
        boot_flag = Path(cls.config_dir) / "start_on_boot.txt"
        with open(boot_flag, "w") as f:
            f.write("true" if state else "false")
