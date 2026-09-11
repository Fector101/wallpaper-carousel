import os
import sqlite3

import pytest
from PIL import Image

from utils import image_operations as io
from utils.config_manager import ConfigManager
from utils import helper


def _make_image(path, color, size=(1000, 700)):
    Image.new("RGB", size, color).save(path)


def _fresh_db(tmp_path):
    """Reset the ImageDatabase singleton against an isolated temp DB file."""
    from utils import database as db
    db.ImageDatabase._instance = None
    db.ImageDatabase._initialized = False
    db.ImageDatabase._cached_config_dir = str(tmp_path)
    db.ImageDatabase._cached_config_path = str(tmp_path / "image_history.db")
    return db.ImageDatabase()


class _FakeImageDB:
    def remove_images(self, paths):
        pass


# --- compute_preview_crop -------------------------------------------------

def test_compute_preview_crop_full_view():
    result = io.compute_preview_crop((800, 800), (800, 800), (1000, 1000), 1.0, (0, 0))
    box, viewport = result
    assert box == (0, 0, 1000, 1000)
    assert viewport == {"scale": 1.0, "cx": 0.5, "cy": 0.5}


def test_compute_preview_crop_zoomed_offset():
    result = io.compute_preview_crop((800, 800), (800, 800), (1000, 1000), 2.0, (-400, -200))
    assert result is not None
    box, viewport = result
    assert box == (250, 375, 750, 875)
    assert viewport["scale"] == 2.0
    assert abs(viewport["cx"] - 0.5) < 1e-9
    assert abs(viewport["cy"] - 0.375) < 1e-9


def test_compute_preview_crop_restores_same_view():
    result = io.compute_preview_crop((800, 800), (800, 800), (1000, 1000), 2.0, (-400, -200))
    _, viewport = result
    restored_pos = (
        800 / 2 - viewport["scale"] * (viewport["cx"] * 800),
        800 / 2 - viewport["scale"] * (viewport["cy"] * 800),
    )
    assert restored_pos == (-400, -200)


def test_compute_preview_crop_degenerate():
    assert io.compute_preview_crop((800, 800), (800, 800), (1000, 1000), 1.0, (100000, 100000)) is None


# --- crop files ------------------------------------------------------------

def test_crop_path_for_collision_safe(tmp_path, monkeypatch):
    monkeypatch.setattr(helper, "appFolder", lambda: str(tmp_path))
    a = tmp_path / "foo.jpg"
    b = tmp_path / "foo.png"
    assert helper.crop_path_for(a).name == "foo_jpg_crop.jpg"
    assert helper.crop_path_for(b).name == "foo_png_crop.jpg"
    assert len({helper.crop_path_for(p) for p in (a, b)}) == 2
    assert (tmp_path / "wallpaper_crops").is_dir()


def test_resolve_user_selected_crop_falls_back_to_source(tmp_path, monkeypatch):
    monkeypatch.setattr(helper, "appFolder", lambda: str(tmp_path))
    src = str(tmp_path / "src.jpg")
    assert helper.resolve_user_selected_crop(src) == src


def test_resolve_user_selected_crop_returns_crop_when_present(tmp_path, monkeypatch):
    monkeypatch.setattr(helper, "appFolder", lambda: str(tmp_path))
    src = str(tmp_path / "src.jpg")
    crop = helper.crop_path_for(src)
    crop.write_bytes(b"x")
    assert helper.resolve_user_selected_crop(src) == str(crop)


def test_crop_and_save_region_creates_cropped_file(tmp_path, monkeypatch):
    monkeypatch.setattr(helper, "appFolder", lambda: str(tmp_path))
    src = tmp_path / "big.png"
    _make_image(src, "red")
    dest = io.crop_and_save_region(str(src), (100, 200, 500, 600))
    assert dest == str(helper.crop_path_for(src))
    with Image.open(dest) as img:
        assert img.size == (400, 400)


def test_crop_and_save_region_rejects_empty_box(tmp_path, monkeypatch):
    monkeypatch.setattr(helper, "appFolder", lambda: str(tmp_path))
    src = tmp_path / "big.png"
    _make_image(src, "red")
    with pytest.raises(ValueError):
        io.crop_and_save_region(str(src), (100, 200, 100, 600))


def test_crop_and_save_region_rgba_png_converts_to_rgb(tmp_path, monkeypatch):
    monkeypatch.setattr(helper, "appFolder", lambda: str(tmp_path))
    src = tmp_path / "rgba.png"
    Image.new("RGBA", (1000, 700), (255, 0, 0, 128)).save(src)
    dest = io.crop_and_save_region(str(src), (100, 200, 500, 600))
    assert dest == str(helper.crop_path_for(src))
    with Image.open(dest) as img:
        assert img.mode == "RGB"
        assert img.size == (400, 400)


def test_save_crop_and_props_failed_persistence_restores_previous_crop(tmp_path, monkeypatch):
    monkeypatch.setattr(helper, "appFolder", lambda: str(tmp_path))
    src = str(tmp_path / "wallpapers" / "a.jpg")
    (tmp_path / "wallpapers").mkdir()
    crop = helper.crop_path_for(src)
    crop.write_bytes(b"previous")

    class FakeDB:
        def set_preview_props(self, *args):
            return False

    def fake_save(s, box):
        crop.write_bytes(b"newcrop")
        return str(crop)

    from ui.screens.preview_screen import _save_crop_and_props
    monkeypatch.setattr("utils.image_operations.crop_and_save_region", fake_save)
    monkeypatch.setattr("utils.database.ImageDatabase", lambda: FakeDB())

    with pytest.raises(Exception, match=r"^Failed to persist preview viewport$"):
        _save_crop_and_props(src, (0, 0, 10, 10), 2.0, 0.5, 0.5)
    assert crop.read_bytes() == b"previous"


def test_save_crop_and_props_failed_persistence_removes_new_crop(tmp_path, monkeypatch):
    monkeypatch.setattr(helper, "appFolder", lambda: str(tmp_path))
    src = str(tmp_path / "wallpapers" / "b.jpg")
    (tmp_path / "wallpapers").mkdir()
    crop = helper.crop_path_for(src)

    class FakeDB:
        def set_preview_props(self, *args):
            return False

    def fake_save(s, box):
        crop.write_bytes(b"newcrop")
        return str(crop)

    from ui.screens.preview_screen import _save_crop_and_props
    monkeypatch.setattr("utils.image_operations.crop_and_save_region", fake_save)
    monkeypatch.setattr("utils.database.ImageDatabase", lambda: FakeDB())

    with pytest.raises(Exception, match=r"^Failed to persist preview viewport$"):
        _save_crop_and_props(src, (0, 0, 10, 10), 2.0, 0.5, 0.5)
    assert not crop.exists()


def test_save_crop_and_props_success_writes_crop_and_props(tmp_path, monkeypatch):
    monkeypatch.setattr(helper, "appFolder", lambda: str(tmp_path))
    src = str(tmp_path / "wallpapers" / "c.jpg")
    (tmp_path / "wallpapers").mkdir()
    crop = helper.crop_path_for(src)

    persisted = []

    class FakeDB:
        def set_preview_props(self, path, scale, cx, cy):
            persisted.append((path, scale, cx, cy))
            return True

    def fake_save(s, box):
        crop.write_bytes(b"newcrop")
        return str(crop)

    from ui.screens.preview_screen import _save_crop_and_props
    monkeypatch.setattr("utils.image_operations.crop_and_save_region", fake_save)
    monkeypatch.setattr("utils.database.ImageDatabase", lambda: FakeDB())

    _save_crop_and_props(src, (0, 0, 10, 10), 2.0, 0.5, 0.5)
    assert crop.read_bytes() == b"newcrop"
    assert persisted == [(src, 2.0, 0.5, 0.5)]


# --- DB preview props ------------------------------------------------------

def test_db_migration_adds_preview_columns(tmp_path):
    db_path = tmp_path / "image_history.db"
    conn = sqlite3.connect(str(db_path))
    conn.executescript(
        """CREATE TABLE images (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            image_path TEXT UNIQUE NOT NULL,
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_set_at TIMESTAMP,
            set_count INTEGER DEFAULT 0,
            tab TEXT DEFAULT 'both',
            last_skipped_at TIMESTAMP,
            skip_count INTEGER DEFAULT 0
        );
        CREATE TABLE widget_images (
            app_widget_id INTEGER PRIMARY KEY,
            image_path TEXT NOT NULL
        );"""
    )
    conn.commit()
    conn.close()

    from utils import database as db
    db.ImageDatabase._instance = None
    db.ImageDatabase._initialized = False
    db.ImageDatabase._cached_config_dir = str(tmp_path)
    db.ImageDatabase._cached_config_path = str(db_path)
    inst = db.ImageDatabase()
    cols = {r[1] for r in inst._conn.execute("PRAGMA table_info(images)").fetchall()}
    assert {"preview_scale", "preview_cx", "preview_cy"} <= cols

    db.ImageDatabase._instance = None
    db.ImageDatabase._initialized = False
    inst2 = db.ImageDatabase()
    cols2 = {r[1] for r in inst2._conn.execute("PRAGMA table_info(images)").fetchall()}
    assert {"preview_scale", "preview_cx", "preview_cy"} <= cols2


def test_preview_props_roundtrip(tmp_path):
    inst = _fresh_db(tmp_path)
    path = "/some/place/img.jpg"
    assert inst.get_preview_props(path) is None
    assert inst.set_preview_props(path, 2.5, 0.4, 0.6) is True
    assert inst.get_preview_props(path) == {"scale": 2.5, "cx": 0.4, "cy": 0.6}
    assert inst.set_preview_props(path, 1.0, 0.5, 0.5) is True
    assert inst.get_preview_props(path) == {"scale": 1.0, "cx": 0.5, "cy": 0.5}


def test_set_preview_props_reports_failure(tmp_path):
    inst = _fresh_db(tmp_path)
    path = "/some/place/img.jpg"
    inst._conn.close()
    assert inst.set_preview_props(path, 2.5, 0.4, 0.6) is False


# --- wallpaper setting uses the crop --------------------------------------

def _stub_java_classes(monkeypatch, sdk_int, decode_file):
    """Make change_wallpaper's internal imports resolve to a deterministic fake."""
    import sys
    import types
    fake = types.ModuleType("android_notify.internal.java_classes")
    fake.BuildVersion = type("BuildVersion", (), {"SDK_INT": sdk_int})
    fake.BitmapFactory = type("BitmapFactory", (), {"decodeFile": staticmethod(decode_file)})
    fake.__path__ = []
    monkeypatch.setitem(sys.modules, "android_notify.internal.java_classes", fake)
    for parent in ("android_notify", "android_notify.internal"):
        mod = sys.modules.get(parent)
        if mod is not None:
            monkeypatch.setattr(mod, "__path__", [], raising=False)
    return fake


def _run_change_wallpaper(monkeypatch, tmp_path, src, decoded, recorded):
    monkeypatch.setattr(helper, "appFolder", lambda: str(tmp_path))

    class FakeWallpaperManager:
        FLAG_LOCK = 2

        @staticmethod
        def getInstance(*_):
            return FakeWallpaperManager()

        def setBitmap(self, bitmap, *_, **__):
            pass

    monkeypatch.setattr(helper, "WallpaperManager", FakeWallpaperManager)
    monkeypatch.setattr(helper, "_toast", lambda *_: None)
    _stub_java_classes(
        monkeypatch,
        sdk_int=26,
        decode_file=lambda p: decoded.append(str(p)) and f"bitmap({p})",
    )

    class FakeDB:
        def record_wallpaper_set(self, path):
            recorded.append(path)

    monkeypatch.setattr("utils.database.ImageDatabase", lambda: FakeDB())
    return helper.change_wallpaper(src)


def test_change_wallpaper_uses_saved_crop(tmp_path, monkeypatch):
    monkeypatch.setattr(helper, "appFolder", lambda: str(tmp_path))
    src = str(tmp_path / "wallpapers" / "a.jpg")
    (tmp_path / "wallpapers").mkdir()
    crop = helper.crop_path_for(src)
    crop.write_bytes(b"crop")

    decoded = []
    recorded = []
    real_exists = os.path.exists
    monkeypatch.setattr(
        os.path,
        "exists",
        lambda p: real_exists(p) or str(p) == src or str(p) == str(crop),
    )

    result = _run_change_wallpaper(monkeypatch, tmp_path, src, decoded, recorded)

    assert result is True
    assert decoded == [str(crop)]
    assert recorded == [src]


def test_change_wallpaper_uses_source_without_crop(tmp_path, monkeypatch):
    monkeypatch.setattr(helper, "appFolder", lambda: str(tmp_path))
    src = str(tmp_path / "wallpapers" / "b.jpg")
    (tmp_path / "wallpapers").mkdir()
    (tmp_path / "wallpapers" / "b.jpg").write_bytes(b"b")

    decoded = []
    recorded = []
    real_exists = os.path.exists
    monkeypatch.setattr(
        os.path,
        "exists",
        lambda p: real_exists(p) or str(p) == src,
    )

    result = _run_change_wallpaper(monkeypatch, tmp_path, src, decoded, recorded)

    assert result is True
    assert decoded == [src]
    assert recorded == [src]


# --- removal cleanup -------------------------------------------------------

def test_remove_images_from_app_unlinks_crop(tmp_path, monkeypatch):
    monkeypatch.setattr(ConfigManager, "_cached_config_path", tmp_path / "config.json")
    ConfigManager.write(ConfigManager.DEFAULT_CONFIG)
    monkeypatch.setattr(helper, "appFolder", lambda: str(tmp_path))

    wp = tmp_path / "wallpapers"
    wp.mkdir()
    src = wp / "a.jpg"
    src.write_bytes(b"src")
    crop = helper.crop_path_for(str(src))
    crop.write_bytes(b"crop")

    ConfigManager.write({**ConfigManager.DEFAULT_CONFIG, "wallpapers": [str(src)]})
    monkeypatch.setattr("utils.database.ImageDatabase", lambda: _FakeImageDB())

    helper.remove_images_from_app([str(src)])

    assert not src.exists()
    assert not crop.exists()