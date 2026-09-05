import sqlite3
import threading
import time
import traceback
from pathlib import Path

from utils.helper import appFolder
from utils.logger import app_logger


_SCHEMA = """CREATE TABLE IF NOT EXISTS images (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    image_path TEXT UNIQUE NOT NULL,
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_set_at TIMESTAMP,
    set_count INTEGER DEFAULT 0,
    tab TEXT DEFAULT 'both',
    last_skipped_at TIMESTAMP,
    skip_count INTEGER DEFAULT 0
);
CREATE TABLE IF NOT EXISTS widget_images (
    app_widget_id INTEGER PRIMARY KEY,
    image_path TEXT NOT NULL
)"""


class ImageDatabase:
    _cached_config_dir = None
    _cached_config_path = None
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
        db_path = self.config_path()
        app_logger.info(f"[ImageDatabase] initialized at {db_path}")
        self._conn = sqlite3.connect(str(db_path), check_same_thread=False, timeout=10)
        self._conn.execute("PRAGMA busy_timeout=10000")
        try:
            self._conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        except sqlite3.Error as e:
            print(f"ImageDatabase wal_checkpoint skipped: {e}")
        self._conn.execute("PRAGMA journal_mode=DELETE")
        journal_mode = self._conn.execute("PRAGMA journal_mode").fetchone()[0]
        app_logger.info(f"[ImageDatabase] journal_mode={journal_mode}")
        self._conn.executescript(_SCHEMA)
        self._conn.commit()

    @classmethod
    def config_dir(cls):
        if cls._cached_config_dir is not None:
            return cls._cached_config_dir
        cls._cached_config_dir = appFolder()
        return cls._cached_config_dir

    @classmethod
    def config_path(cls):
        if cls._cached_config_path is not None:
            return cls._cached_config_path
        cls._cached_config_path = Path(cls.config_dir()) / "image_history.db"
        return cls._cached_config_path

    def _retry_busy(self, fn):
        """Run fn, retrying transient SQLITE_BUSY/SQLITE_LOCKED failures.
        Rollback is issued after each failure so the next attempt starts clean."""
        with self._lock:
            for attempt in range(1, 4):
                try:
                    return fn()
                except sqlite3.OperationalError as e:
                    try:
                        self._conn.rollback()
                    except sqlite3.Error:
                        pass
                    if "locked" in str(e).lower() or "busy" in str(e).lower():
                        if attempt < 3:
                            app_logger.error(
                                f"[ImageDatabase] busy/locked (attempt {attempt}/3): {e} - retrying"
                            )
                            time.sleep(0.2 * attempt)
                            continue
                    raise

    def _execute(self, sql, params=()):
        try:
            self._retry_busy(
                lambda: (self._conn.execute(sql, params), self._conn.commit())
            )
        except Exception as e:
            app_logger.error(f"[ImageDatabase] _execute error: {e}")
            traceback.print_exc()

    def _fetchone(self, sql, params=()):
        try:
            return self._retry_busy(
                lambda: self._conn.execute(sql, params).fetchone()
            )
        except Exception as e:
            print(f"ImageDatabase fetch error: {e}")
            traceback.print_exc()
            return None

    def _fetchall(self, sql, params=()):
        try:
            return self._retry_busy(
                lambda: self._conn.execute(sql, params).fetchall()
            )
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
            "INSERT INTO images (image_path, last_set_at, set_count) "
            "VALUES (?, CURRENT_TIMESTAMP, 1) "
            "ON CONFLICT(image_path) DO UPDATE SET "
            "last_set_at = CURRENT_TIMESTAMP, set_count = set_count + 1",
            (path,),
        )

    def record_skip(self, path):
        self._execute(
            "INSERT INTO images (image_path, last_skipped_at, skip_count) "
            "VALUES (?, CURRENT_TIMESTAMP, 1) "
            "ON CONFLICT(image_path) DO UPDATE SET "
            "last_skipped_at = CURRENT_TIMESTAMP, skip_count = skip_count + 1",
            (path,),
        )

    def update_tab(self, path, tab):
        self._execute(
            "INSERT INTO images (image_path, tab) VALUES (?, ?) "
            "ON CONFLICT(image_path) DO UPDATE SET tab = ?",
            (path, tab, tab),
        )

    def remove_image(self, path):
        self._execute(
            "DELETE FROM widget_images WHERE image_path = ?",
            (path,),
        )
        self._execute(
            "DELETE FROM images WHERE image_path = ?",
            (path,),
        )
        app_logger.info(f"[widget_images] remove_image cleaned rows referencing {path}")

    def set_widget_image(self, app_widget_id, image_path):
        self._execute(
            "INSERT INTO widget_images (app_widget_id, image_path) VALUES (?, ?) "
            "ON CONFLICT(app_widget_id) DO UPDATE SET image_path = excluded.image_path",
            (app_widget_id, image_path),
        )
        app_logger.info(f"[widget_images] set app_widget_id={app_widget_id} -> {image_path}")
        stored = self.get_widget_image(app_widget_id)
        if stored != image_path:
            app_logger.error(
                f"[widget_images] VERIFY_FAILED widget {app_widget_id} "
                f"stored={stored!r} expected={image_path!r}"
            )

    def get_widget_image(self, app_widget_id):
        row = self._fetchone(
            "SELECT image_path FROM widget_images WHERE app_widget_id = ?",
            (app_widget_id,),
        )
        result = row[0] if row else None
        app_logger.info(f"[widget_images] get app_widget_id={app_widget_id} -> {result}")
        return result

    def remove_widget(self, app_widget_id):
        self._execute(
            "DELETE FROM widget_images WHERE app_widget_id = ?",
            (app_widget_id,),
        )
        app_logger.warning(f"[widget_images] remove_widget app_widget_id={app_widget_id}")

    def remove_widgets(self, app_widget_ids):
        with self._lock:
            try:
                self._conn.executemany(
                    "DELETE FROM widget_images WHERE app_widget_id = ?",
                    [(w,) for w in app_widget_ids],
                )
                self._conn.commit()
                app_logger.warning(f"[widget_images] remove_widgets ids={app_widget_ids}")
            except Exception as e:
                print(f"ImageDatabase batch widget delete error: {e}")
                traceback.print_exc()

    def get_all_widget_images(self):
        rows = self._fetchall(
            "SELECT app_widget_id, image_path FROM widget_images"
        )
        app_logger.info(f"[widget_images] get_all -> {len(rows)} row(s)")
        return {int(widget_id): image_path for widget_id, image_path in rows}

    def clear_all(self):
        self._execute("DELETE FROM widget_images")
        self._execute("DELETE FROM images")
        app_logger.warning("[widget_images] clear_all called - widget_images emptied")

    def remove_images(self, paths):
        paths = list(paths)
        with self._lock:
            try:
                self._conn.executemany(
                    "DELETE FROM widget_images WHERE image_path = ?",
                    [(p,) for p in paths],
                )
                self._conn.executemany(
                    "DELETE FROM images WHERE image_path = ?",
                    [(p,) for p in paths],
                )
                self._conn.commit()
                app_logger.warning(f"[widget_images] remove_images cleaned rows for {len(paths)} path(s)")
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
