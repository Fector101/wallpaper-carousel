import os

from PIL import Image
import pytest

from utils import image_operations as io
from utils.config_manager import ConfigManager
from utils import helper


def _make_image(path, color):
    Image.new("RGB", (1000, 700), color).save(path)


def test_create_scaled_down_img_rejects_nonpositive_dims(tmp_path):
    src = tmp_path / "a.png"
    src.write_bytes(b"x")
    dest = tmp_path / "out.jpg"
    with pytest.raises(ValueError):
        io.create_scaled_down_img(str(src), str(dest), 0, 100)
    with pytest.raises(ValueError):
        io.create_scaled_down_img(str(src), str(dest), 100, 0)
    with pytest.raises(ValueError):
        io.create_scaled_down_img(str(src), str(dest), 100, -5)


def test_create_scaled_down_img_rgba_png_converts_to_rgb(tmp_path):
    src = tmp_path / "rgba.png"
    Image.new("RGBA", (1000, 700), (255, 0, 0, 128)).save(src)
    dest = tmp_path / "out.jpg"

    result = io.create_scaled_down_img(str(src), str(dest), 400, 300)

    assert result == str(dest)
    assert dest.exists()
    with Image.open(dest) as img:
        assert img.mode == "RGB"


def test_create_scaled_down_img_android_failure_returns_source(tmp_path, monkeypatch):
    import builtins
    from pathlib import Path

    src = tmp_path / "a.png"
    _make_image(src, "red")
    dest = tmp_path / "part.jpg"
    dest.write_bytes(b"partial")

    real_import = builtins.__import__

    def _no_pil(name, *a, **k):
        if name == "PIL" or name.startswith("PIL."):
            raise ImportError("disabled for test")
        return real_import(name, *a, **k)

    monkeypatch.setattr(builtins, "__import__", _no_pil)
    monkeypatch.setattr(io, "_on_android_platform", lambda: True)
    # Bypass the "dest already exists" early return so the Android path runs,
    # then make the Android decode raise partway through.
    monkeypatch.setattr(io.os.path, "exists", lambda p: False)
    monkeypatch.setattr(
        io,
        "_compute_in_sample_size",
        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("decode failed")),
    )

    result = io.create_scaled_down_img(str(src), str(dest), 800, 600)

    assert result == str(src)
    assert not Path(dest).exists()


def test_get_or_create_scaled_down_image_zero_size_falls_back_to_source(tmp_path, monkeypatch):
    src = tmp_path / "a.png"
    _make_image(src, "red")
    monkeypatch.setattr(io, "scaled_down_path_for", lambda s: tmp_path / "out.jpg")

    result = io.get_or_create_scaled_down_image(str(src), (0, 100))
    assert result == str(src)


def test_get_or_create_scaled_down_image_positive_size_creates_dest(tmp_path):
    src = tmp_path / "a.png"
    _make_image(src, "red")

    result = io.get_or_create_scaled_down_image(str(src), (400, 400))
    assert os.path.exists(result)
    assert result != str(src)


def test_backfill_scaled_down_images_creates_missing_only(tmp_path, monkeypatch):
    monkeypatch.setattr(ConfigManager, "_cached_config_path", tmp_path / "config.json")
    ConfigManager.write(ConfigManager.DEFAULT_CONFIG)

    wp = tmp_path / "wallpapers"
    wp.mkdir()
    a = wp / "a.png"
    _make_image(a, "red")
    b = wp / "b.jpg"
    _make_image(b, "red")
    cache_ok = io.scaled_down_path_for(b)
    cache_ok.write_bytes(b"existing")
    missing_src = str(tmp_path / "nope.jpg")

    ConfigManager.write(
        {
            **ConfigManager.DEFAULT_CONFIG,
            "wallpapers": [str(a), str(b), missing_src],
            "day_wallpapers": [str(a)],
        }
    )

    io.backfill_scaled_down_images(size=(400, 400))

    assert io.scaled_down_path_for(a).exists()
    assert io.scaled_down_path_for(b).read_bytes() == b"existing"
    assert not io.scaled_down_path_for(missing_src).exists()


def test_backfill_scaled_down_images_empty_config_is_noop(tmp_path, monkeypatch):
    monkeypatch.setattr(ConfigManager, "_cached_config_path", tmp_path / "config.json")
    ConfigManager.write(ConfigManager.DEFAULT_CONFIG)

    io.backfill_scaled_down_images(size=(400, 400))

    assert not (tmp_path / "wallpapers" / "scaled_down_images").exists()


class _FakeImageDB:
    def __init__(self):
        self.removed = []

    def remove_images(self, paths):
        self.removed.append(list(paths))


def _setup_wallpapers(tmp_path, names, with_source=True, with_derived=True):
    wp = tmp_path / "wallpapers"
    wp.mkdir()
    for name in names:
        p = wp / name
        if with_source:
            _make_image(p, "red")
        if with_derived:
            (wp / "thumbs").mkdir(exist_ok=True)
            (wp / "scaled_down_images").mkdir(exist_ok=True)
            (wp / "thumbs" / f"{p.stem}_thumb.jpg").write_bytes(b"t")
            io.scaled_down_path_for(p).write_bytes(b"s")
    return [str(wp / name) for name in names]


def test_scaled_down_path_for_is_collision_safe(tmp_path):
    a = tmp_path / "foo.jpg"
    b = tmp_path / "foo.png"
    c = tmp_path / "foo.jpeg"
    assert io.scaled_down_path_for(a).name == "foo_jpg.jpg"
    assert io.scaled_down_path_for(b).name == "foo_png.jpg"
    assert io.scaled_down_path_for(c).name == "foo_jpeg.jpg"
    assert len({io.scaled_down_path_for(p) for p in (a, b, c)}) == 3


def test_remove_images_from_app_cleans_derived_files(tmp_path, monkeypatch):
    monkeypatch.setattr(ConfigManager, "_cached_config_path", tmp_path / "config.json")
    ConfigManager.write(ConfigManager.DEFAULT_CONFIG)

    paths = _setup_wallpapers(tmp_path, ["a.png", "b.jpg"])
    a_path, b_path = paths
    data = ConfigManager.DEFAULT_CONFIG.copy()
    data.update({"wallpapers": [a_path, b_path], "day_wallpapers": [a_path]})
    ConfigManager.write(data)

    fake_db = _FakeImageDB()
    monkeypatch.setattr("utils.database.ImageDatabase", lambda: fake_db)

    helper.remove_images_from_app([a_path])

    wp = tmp_path / "wallpapers"
    assert not (wp / "a.png").exists()
    assert not (wp / "thumbs" / "a_thumb.jpg").exists()
    assert not (wp / "scaled_down_images" / "a_png.jpg").exists()
    assert (wp / "b.jpg").exists()

    cfg = ConfigManager.read()
    assert a_path not in cfg["wallpapers"]
    assert a_path not in cfg["day_wallpapers"]
    assert b_path in cfg["wallpapers"]
    assert fake_db.removed == [[a_path]]


def test_remove_images_from_app_missing_source_still_cleans_up(tmp_path, monkeypatch):
    monkeypatch.setattr(ConfigManager, "_cached_config_path", tmp_path / "config.json")
    ConfigManager.write(ConfigManager.DEFAULT_CONFIG)

    paths = _setup_wallpapers(tmp_path, ["gone.png"], with_source=False, with_derived=True)
    gone_path = paths[0]
    ConfigManager.write(
        {**ConfigManager.DEFAULT_CONFIG, "wallpapers": [gone_path], "noon_wallpapers": [gone_path]}
    )

    fake_db = _FakeImageDB()
    monkeypatch.setattr("utils.database.ImageDatabase", lambda: fake_db)

    helper.remove_images_from_app([gone_path])

    wp = tmp_path / "wallpapers"
    assert not (wp / "thumbs" / "gone_thumb.jpg").exists()
    assert not (wp / "scaled_down_images" / "gone_png.jpg").exists()
    assert not ConfigManager.read()["wallpapers"]
    assert fake_db.removed == [[gone_path]]


def test_remove_images_from_app_oserror_skips_failed_path(tmp_path, monkeypatch):
    monkeypatch.setattr(ConfigManager, "_cached_config_path", tmp_path / "config.json")
    ConfigManager.write(ConfigManager.DEFAULT_CONFIG)

    paths = _setup_wallpapers(tmp_path, ["locked.png", "ok.jpg"])
    locked_path, ok_path = paths
    ConfigManager.write({**ConfigManager.DEFAULT_CONFIG, "wallpapers": [locked_path, ok_path]})

    fake_db = _FakeImageDB()
    monkeypatch.setattr("utils.database.ImageDatabase", lambda: fake_db)

    real_remove = os.remove
    calls = {"n": 0}

    def flaky_remove(path):
        calls["n"] += 1
        if calls["n"] == 1:
            raise PermissionError("denied")
        return real_remove(path)

    monkeypatch.setattr(os, "remove", flaky_remove)

    helper.remove_images_from_app([locked_path, ok_path])

    wp = tmp_path / "wallpapers"
    assert (wp / "locked.png").exists()
    assert not (wp / "ok.jpg").exists()
    assert not (wp / "thumbs" / "ok_thumb.jpg").exists()
    assert fake_db.removed == [[ok_path]]