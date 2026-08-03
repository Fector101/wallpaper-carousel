from pathlib import Path
from unittest import mock

from kivy.clock import Clock
from PIL import Image

from utils import image_operations as io
from utils.config_manager import ConfigManager


def _make_image(path, color):
    Image.new("RGB", (1000, 700), color).save(path)


def _new_op():
    op = io.ImageOperation(load_saved=lambda **kw: None)
    op.app = mock.MagicMock()
    return op


def test_import_images_from_plyer_copies_and_creates_thumbnails(tmp_path, monkeypatch):
    monkeypatch.setattr(ConfigManager, "config_path", tmp_path / "config.json")
    ConfigManager.write(ConfigManager.DEFAULT_CONFIG)

    src = tmp_path / "src"
    src.mkdir()
    _make_image(src / "a.png", "red")
    _make_image(src / "b.jpg", "blue")
    _make_image(src / "c.png", "green")

    op = _new_op()
    op.import_images_from_plyer([str(src / "a.png"), str(src / "b.jpg"), str(src / "c.png")])

    wp = io.wallpapers_dir
    assert {p.name for p in wp.glob("*.png")} | {p.name for p in wp.glob("*.jpg")} == {"a.png", "b.jpg", "c.png"}
    assert {p.name for p in (wp / "thumbs").glob("*")} == {"a_thumb.jpg", "b_thumb.jpg", "c_thumb.jpg"}
    assert {Path(p).name for p in io.my_config.read()["wallpapers"]} == {"a.png", "b.jpg", "c.png"}

    Clock.tick()
    assert op._processing_start is None


def test_import_images_from_plyer_no_files(tmp_path, monkeypatch):
    monkeypatch.setattr(ConfigManager, "config_path", tmp_path / "config.json")
    saved = {}
    op = io.ImageOperation(load_saved=lambda **kw: saved.update(kw))
    op.app = mock.MagicMock()

    op.import_images_from_plyer([])

    Clock.tick()
    assert saved.get("has_files") is False


class _FakeUri:
    def __init__(self, scheme, path):
        self._scheme = scheme
        self._path = path

    def getScheme(self):
        return self._scheme

    def getPath(self):
        return self._path

    def __repr__(self):
        return f"_FakeUri({self._scheme!r}, {self._path!r})"


class _FakeIntent:
    def __init__(self, clip=None, data=None, stream_list=None, stream=None, stream_array=None):
        self._clip = clip
        self._data = data
        self._stream_list = stream_list
        self._stream = stream
        self._stream_array = stream_array

    def getClipData(self):
        return self._clip

    def getData(self):
        return self._data

    def getParcelableArrayListExtra(self, key):
        return self._stream_list

    def getParcelableExtra(self, key):
        return self._stream

    def getParcelableArrayExtra(self, key):
        return self._stream_array


def test_get_uri_name_and_path_returns_readable_file_path(tmp_path):
    readable = tmp_path / "a.png"
    readable.write_bytes(b"data")
    name, path = io.get_uri_name_and_path(_FakeUri("file", str(readable)))
    assert path == str(readable)
    assert name == "a.png"


def test_get_uri_name_and_path_skips_unreadable_file(tmp_path):
    missing = tmp_path / "missing.png"
    name, path = io.get_uri_name_and_path(_FakeUri("file", str(missing)))
    assert path is None
    assert name is None


def test_copy_image_to_internal_file_scheme(tmp_path, monkeypatch):
    monkeypatch.setattr(ConfigManager, "config_path", tmp_path / "config.json")
    src = tmp_path / "a.png"
    _make_image(src, "red")
    dst = io.wallpapers_dir / "a.png"
    result = io.copy_image_to_internal(destination_path=dst, uri=_FakeUri("file", str(src)))
    assert result == str(dst)
    assert dst.exists()


def test_get_selected_uris_from_intent_prefers_clip_data(tmp_path):
    a = tmp_path / "a.png"
    a.write_bytes(b"x")

    class _Clip:
        def getItemCount(self):
            return 1

        def getItemAt(self, i):
            return _FakeClipItem(_FakeUri("file", str(a)))

    class _FakeClipItem:
        def __init__(self, uri):
            self._uri = uri

        def getUri(self):
            return self._uri

    intent = _FakeIntent(clip=_Clip(), data=_FakeUri("file", "/other.png"))
    uris = io.get_selected_uris_from_intent(intent)
    assert [u.getPath() for u in uris] == [str(a)]


def test_get_selected_uris_from_intent_reads_extra_stream_list(tmp_path, monkeypatch):
    monkeypatch.setattr(io, "cast", lambda *args: args[-1])
    a = tmp_path / "a.png"
    b = tmp_path / "b.png"
    a.write_bytes(b"x")
    b.write_bytes(b"y")
    intent = _FakeIntent(stream_list=[_FakeUri("file", str(a)), _FakeUri("file", str(b))])
    uris = io.get_selected_uris_from_intent(intent)
    assert [u.getPath() for u in uris] == [str(a), str(b)]


def test_get_selected_uris_from_intent_reads_single_extra_stream(tmp_path, monkeypatch):
    monkeypatch.setattr(io, "cast", lambda *args: args[-1])
    a = tmp_path / "a.png"
    a.write_bytes(b"x")
    intent = _FakeIntent(stream=_FakeUri("file", str(a)))
    uris = io.get_selected_uris_from_intent(intent)
    assert [u.getPath() for u in uris] == [str(a)]


def test_get_selected_uris_from_intent_reads_extra_stream_array(tmp_path, monkeypatch):
    monkeypatch.setattr(io, "cast", lambda *args: args[-1])
    a = tmp_path / "a.png"
    b = tmp_path / "b.png"
    a.write_bytes(b"x")
    b.write_bytes(b"y")
    intent = _FakeIntent(stream_array=[_FakeUri("file", str(a)), _FakeUri("file", str(b))])
    uris = io.get_selected_uris_from_intent(intent)
    assert [u.getPath() for u in uris] == [str(a), str(b)]


def test_get_selected_uris_from_intent_returns_empty_without_carriers():
    assert io.get_selected_uris_from_intent(_FakeIntent()) == []
    assert io.get_selected_uris_from_intent(None) == []


