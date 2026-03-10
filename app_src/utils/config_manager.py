import json, os
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
        "wallpapers": [],
        "noon_wallpapers":[],
        "day_wallpapers":[],
        "use_on_wake": False,
        "use_group_by_date": True,

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
            self._write(self.DEFAULT_CONFIG)

    @classmethod
    def _read(cls):
        try:
            with open(cls.config_path, "r") as f:
                return json.load(f)
        except Exception as error_reading_config_file:
            print(f"error reading config file: {error_reading_config_file}")
            try:
                cls._write(cls.DEFAULT_CONFIG)
                return cls.DEFAULT_CONFIG
            except PermissionError:
                toast("PD: Cannot access config file")
            except Exception as e:
                toast(str(e))
    @classmethod
    def _write(cls, data):
        try:
            with open(cls.config_path, "w") as f:
                json.dump(data, f, indent=4)
        except PermissionError:
            toast("PD: Cannot access config file")
        except Exception as e:
            toast(str(e))

    # ---------- INTERVAL ----------
    def get_interval(self):
        return self._read().get("interval_mins", 2)

    def set_interval(self, mins: float):
        data = self._read()
        data["interval_mins"] = mins
        self._write(data)

    # ---------- WALLPAPERS ----------
    def get_wallpapers(self):
        return self._read().get("wallpapers", [])

    def set_wallpapers(self, lst):
        data = self._read()
        data["wallpapers"] = lst
        self._write(data)

    def add_wallpaper(self, path):
        data = self._read()
        if path not in data["wallpapers"]:
            data["wallpapers"].append(path)
            self._write(data)

    def remove_wallpaper(self, path):
        data = self._read()
        if path in data["wallpapers"]:
            data["wallpapers"].remove(path)
            self._write(data)

    def get_noon_wallpapers(self):
        return self._read().get("noon_wallpapers", [])

    def get_day_wallpapers(self):
        return self._read().get("day_wallpapers", [])

    def add_wallpaper_to_day_wallpapers(self, path):
        data = self._read()
        if path not in data["day_wallpapers"]:
            data["day_wallpapers"].append(path)
            self._write(data)

    def add_wallpaper_to_noon_wallpapers(self, path):
        data = self._read()
        if path not in data["noon_wallpapers"]:
            data["noon_wallpapers"].append(path)
            self._write(data)

    def remove_wallpaper_to_from(self, wallpaper_key_name, path):
        data = self._read()
        if path in data[wallpaper_key_name]:
            data[wallpaper_key_name].remove(path)
            self._write(data)

    @classmethod
    def get_on_wake_state(cls):
        s=cls._read().get("use_on_wake", False)
        # print("returned",s)
        return s

    @classmethod
    def set_on_wake_state(cls, state: bool):
        # print('called',state)
        data = cls._read()
        data["use_on_wake"] = state
        cls._write(data)

    @property
    def get_use_group_by_date(self):
        if "use_group_by_date" in self._read():
            return self._read().get("use_group_by_date", True)
        else:
            self.set_use_group_by_date(True)
            return True
    def set_use_group_by_date(self, state: bool):
        data = self._read()
        data["use_group_by_date"] = state
        self._write(data)
