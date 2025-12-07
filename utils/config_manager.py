import json
import os
from pathlib import Path
try:
    from kivymd.toast import toast
except:
    def toast(txt):
        print("Fallback toast:", txt)

class ConfigManager:
    DEFAULT_CONFIG = {
        "interval_mins": 2,
        "wallpapers": []
    }

    def __init__(self, config_dir: Path):
        self.config_path = Path(config_dir) / "config.json"
        self._ensure_config()

    def _ensure_config(self):
        if not self.config_path.exists():
            self._write(self.DEFAULT_CONFIG)

    def _read(self):
        try:
            with open(self.config_path, "r") as f:
                return json.load(f)
        except:
            try:
                self._write(self.DEFAULT_CONFIG)
                return self.DEFAULT_CONFIG
            except Exception as e:
                toast(str(e))

    def _write(self, data):
        try:
            with open(self.config_path, "w") as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            toast(str(e))

    # ---------- INTERVAL ----------
    def get_interval(self):
        return self._read().get("interval_mins", 2)

    def set_interval(self, mins: int):
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
