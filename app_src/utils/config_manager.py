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
        "wallpapers": []
    }

    def __init__(self):

        self.config_path = Path(self.config_dir) / "config.json"
        self._ensure_config()
    @property
    def config_dir(self):

        if is_platform_android():
            from android.storage import app_storage_path  # type: ignore
            app_path = app_storage_path()
        else:
            app_path = os.getcwd()

        return app_path

    def _ensure_config(self):
        if not self.config_path.exists():
            self._write(self.DEFAULT_CONFIG)

    def _read(self):
        try:
            with open(self.config_path, "r") as f:
                return json.load(f)
        except Exception as error_reading_config_file:
            print(f"error reading config file: {error_reading_config_file}")
            try:
                self._write(self.DEFAULT_CONFIG)
                return self.DEFAULT_CONFIG
            except PermissionError:
                toast("PD: Cannot access config file")
            except Exception as e:
                toast(str(e))

    def _write(self, data):
        try:
            with open(self.config_path, "w") as f:
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
