import json
from pathlib import Path

class ConfigManager:
    def __init__(self, app_dir: Path):
        self.config_path = app_dir / "config.json"
        self.default_data = {
            "interval_minutes": 2,  # Default rotation time
            "wallpapers": []        # Optional: Store paths here later if needed
        }
        self._load()

    # Load or create default config
    def _load(self):
        if not self.config_path.exists():
            self._write(self.default_data)
        try:
            with self.config_path.open("r", encoding="utf-8") as f:
                self.data = json.load(f)
        except:
            self.data = self.default_data.copy()
            self._write(self.data)

    # Write data to file
    def _write(self, data):
        with self.config_path.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)

    # ===== Interval Management ===== #
    def get_interval(self) -> int:
        return self.data.get("interval_minutes", 2)

    def set_interval(self, minutes: int):
        self.data["interval_minutes"] = max(1, int(minutes))  # min 1 min
        self._write(self.data)

    # ===== Wallpapers List (optional future use) ===== #
    def get_wallpapers(self):
        return self.data.get("wallpapers", [])

    def set_wallpapers(self, wallpapers: list):
        self.data["wallpapers"] = wallpapers
        self._write(self.data)
