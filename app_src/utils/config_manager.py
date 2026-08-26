import json, os
import tempfile
import threading
import traceback
from pathlib import Path

from utils.platform_compat import toast as _toast, on_android_platform as is_platform_android

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

    _cached_config_dir = None
    _cached_config_path = None
    _lock = threading.RLock()

    @classmethod
    def config_dir(cls):
        if cls._cached_config_dir is not None:
            return cls._cached_config_dir
        if is_platform_android():
            android_private = os.environ.get('ANDROID_PRIVATE')
            if android_private:
                cls._cached_config_dir = android_private
            else:
                from android.storage import app_storage_path  # type: ignore
                cls._cached_config_dir = app_storage_path()
        else:
            cls._cached_config_dir = os.getcwd()
        return cls._cached_config_dir

    @classmethod
    def config_path(cls):
        if cls._cached_config_path is not None:
            return cls._cached_config_path
        cls._cached_config_path = Path(cls.config_dir()) / "config.json"
        return cls._cached_config_path

    def _ensure_config(self):
        with ConfigManager._lock:
            if not self.config_path().exists():
                self.write(self.DEFAULT_CONFIG)

    @classmethod
    def read(cls):
        try:
            with open(cls.config_path(), "r") as f:
                return json.load(f)
        except Exception as error_reading_config_file:
            print(f"error reading config file: {error_reading_config_file}")
            traceback.print_exc()
            try:
                cls.write(cls.DEFAULT_CONFIG)
                return cls.DEFAULT_CONFIG
            except PermissionError:
                _toast("PD: Cannot access config file")
            except Exception as e:
                _toast(str(e))
                traceback.print_exc()
    @classmethod
    def write(cls, data):
        try:
            path = cls.config_path()
            path.parent.mkdir(parents=True, exist_ok=True)
            fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
            try:
                with os.fdopen(fd, "w") as f:
                    json.dump(data, f, indent=4)
                    f.flush()
                    os.fsync(f.fileno())
                os.replace(tmp, path)
            except BaseException:
                try:
                    os.unlink(tmp)
                except OSError:
                    pass
                raise
        except PermissionError:
            _toast("PD: Cannot access config file")
        except Exception as e:
            _toast(str(e))
            traceback.print_exc()

    # ---------- INTERVAL ----------
    def get_interval(self):
        return self.read().get("interval_mins", 2)

    def set_interval(self, mins: float):
        with ConfigManager._lock:
            data = self.read()
            data["interval_mins"] = mins
            self.write(data)

    # ---------- WALLPAPERS ----------
    def get_wallpapers(self):
        return self.read().get("wallpapers", [])

    def set_wallpapers(self, lst):
        with ConfigManager._lock:
            data = self.read()
            data["wallpapers"] = lst
            self.write(data)

    def add_wallpaper(self, path):
        with ConfigManager._lock:
            data = self.read()
            if path not in data["wallpapers"]:
                data["wallpapers"].append(path)
                self.write(data)

    def remove_wallpaper(self, path):
        with ConfigManager._lock:
            data = self.read()
            if path in data["wallpapers"]:
                data["wallpapers"].remove(path)
                self.write(data)

    def get_noon_wallpapers(self):
        return self.read().get("noon_wallpapers", [])

    def set_noon_wallpapers(self, lst):
        with ConfigManager._lock:
            data = self.read()
            data["noon_wallpapers"] = lst
            self.write(data)

    def get_day_wallpapers(self):
        return self.read().get("day_wallpapers", [])

    def set_day_wallpapers(self, lst):
        with ConfigManager._lock:
            data = self.read()
            data["day_wallpapers"] = lst
            self.write(data)

    def add_wallpaper_to_day_wallpapers(self, path):
        with ConfigManager._lock:
            data = self.read()
            if path not in data["day_wallpapers"]:
                data["day_wallpapers"].append(path)
                self.write(data)

    def add_wallpaper_to_noon_wallpapers(self, path):
        with ConfigManager._lock:
            data = self.read()
            if path not in data["noon_wallpapers"]:
                data["noon_wallpapers"].append(path)
                self.write(data)

    def remove_wallpaper_to_from(self, wallpaper_key_name, path):
        with ConfigManager._lock:
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
        with cls._lock:
            data = cls.read()
            data["use_on_wake"] = state
            cls.write(data)

    @classmethod
    def get_cols(cls):
        s=cls.read().get("cols", cls.DEFAULT_CONFIG["cols"])
        return s

    @classmethod
    def set_cols(cls, cols: int):
        with cls._lock:
            data = cls.read()
            data["cols"] = cols
            cls.write(data)

    @property
    def get_use_group_by_date(self):
        with ConfigManager._lock:
            data = self.read() or {}
            if "use_group_by_date" in data:
                return data["use_group_by_date"]
            self.set_use_group_by_date(True)
            return True

    def set_use_group_by_date(self, state: bool):
        with ConfigManager._lock:
            data = self.read()
            data["use_group_by_date"] = state
            self.write(data)

    # ---------- THEME PREFERENCE ----------
    @classmethod
    def get_theme_preference(cls):
        return cls.read().get("theme_preference", "adaptive")

    @classmethod
    def set_theme_preference(cls, preference: str):
        with cls._lock:
            data = cls.read()
            data["theme_preference"] = preference
            cls.write(data)

    # ---------- START PREFERENCES ----------
    @classmethod
    def get_start_on_app_launch(cls):
        return cls.read().get("start_on_app_launch", True)

    @classmethod
    def set_start_on_app_launch(cls, state: bool):
        with cls._lock:
            data = cls.read()
            data["start_on_app_launch"] = state
            cls.write(data)

    @classmethod
    def get_start_on_boot(cls):
        return cls.read().get("start_on_boot", True)

    @classmethod
    def set_start_on_boot(cls, state: bool):
        with cls._lock:
            data = cls.read()
            data["start_on_boot"] = state
            cls.write(data)
            boot_flag = Path(cls.config_dir()) / "start_on_boot.txt"
            with open(boot_flag, "w") as f:
                f.write("true" if state else "false")
