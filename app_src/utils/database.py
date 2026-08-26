import sqlite3
import threading
import traceback
from pathlib import Path

from utils.helper import appFolder
from utils.platform_compat import on_android_platform as _on_android_platform

_SCHEMA = """CREATE TABLE IF NOT EXISTS images (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    image_path TEXT UNIQUE NOT NULL,
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_set_at TIMESTAMP,
    set_count INTEGER DEFAULT 0,
    tab TEXT DEFAULT 'both',
    last_skipped_at TIMESTAMP,
    skip_count INTEGER DEFAULT 0
)"""


class ImageDatabase:
    _instance = None
    _class_lock = threading.Lock()

    def __new__(cls):
        with cls._class_lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._lock = threading.RLock()
        db_path = Path(appFolder()) / "image_history.db"
        print(f"ImageDatabase initialized at {db_path}")
        self._conn = sqlite3.connect(str(db_path), check_same_thread=False)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute(_SCHEMA)
        self._conn.commit()

    def _execute(self, sql, params=()):
        with self._lock:
            try:
                self._conn.execute(sql, params)
                self._conn.commit()
            except Exception as e:
                print(f"ImageDatabase error: {e}")
                traceback.print_exc()

    def _fetchone(self, sql, params=()):
        with self._lock:
            try:
                return self._conn.execute(sql, params).fetchone()
            except Exception as e:
                print(f"ImageDatabase fetch error: {e}")
                traceback.print_exc()
                return None

    def _fetchall(self, sql, params=()):
        with self._lock:
            try:
                return self._conn.execute(sql, params).fetchall()
            except Exception as e:
                print(f"ImageDatabase fetch error: {e}")
                traceback.print_exc()
                return []

    def insert_image(self, path):
        self._execute(
            "INSERT OR IGNORE INTO images (image_path) VALUES (?)",
            (path,),
        )

    def insert_images(self, paths):
        with self._lock:
            try:
                self._conn.executemany(
                    "INSERT OR IGNORE INTO images (image_path) VALUES (?)",
                    [(p,) for p in paths],
                )
                self._conn.commit()
            except Exception as e:
                print(f"ImageDatabase batch insert error: {e}")
                traceback.print_exc()

    def record_wallpaper_set(self, path):
        self._execute(
            "UPDATE images SET last_set_at = CURRENT_TIMESTAMP, set_count = set_count + 1 "
            "WHERE image_path = ?",
            (path,),
        )

    def record_skip(self, path):
        self._execute(
            "UPDATE images SET last_skipped_at = CURRENT_TIMESTAMP, skip_count = skip_count + 1 "
            "WHERE image_path = ?",
            (path,),
        )

    def update_tab(self, path, tab):
        self._execute(
            "UPDATE images SET tab = ? WHERE image_path = ?",
            (tab, path),
        )

    def remove_image(self, path):
        self._execute(
            "DELETE FROM images WHERE image_path = ?",
            (path,),
        )

    def remove_images(self, paths):
        with self._lock:
            try:
                self._conn.executemany(
                    "DELETE FROM images WHERE image_path = ?",
                    [(p,) for p in paths],
                )
                self._conn.commit()
            except Exception as e:
                print(f"ImageDatabase batch delete error: {e}")
                traceback.print_exc()

    def get_image_stats(self, path):
        return self._fetchone(
            "SELECT set_count, skip_count, last_set_at, last_skipped_at, tab "
            "FROM images WHERE image_path = ?",
            (path,),
        )

    def get_overall_stats(self):
        row = self._fetchone(
            "SELECT COUNT(*), SUM(set_count), SUM(skip_count) FROM images"
        )
        if row:
            return {
                "total_images": row[0] or 0,
                "total_sets": row[1] or 0,
                "total_skips": row[2] or 0,
            }
        return {"total_images": 0, "total_sets": 0, "total_skips": 0}

    def get_most_set(self, limit=5):
        return self._fetchall(
            "SELECT image_path, set_count FROM images "
            "WHERE set_count > 0 ORDER BY set_count DESC LIMIT ?",
            (limit,),
        )

    def get_most_skipped(self, limit=5):
        return self._fetchall(
            "SELECT image_path, skip_count FROM images "
            "WHERE skip_count > 0 ORDER BY skip_count DESC LIMIT ?",
            (limit,),
        )

    def close(self):
        with self._lock:
            try:
                self._conn.close()
            except Exception:
                pass
